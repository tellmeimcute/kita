
from logging import getLogger

from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from core.config import Config
from database.dao import UserAlchemyDAO
from database.dto import UserDTO
from database.models import UserAlchemy
from database.roles import UserRole
from database.redis.user import UserRedis

from helpers.schemas.objects import UserData
from core.exceptions import UserImmuneError, SQLUserNotFoundError

logger = getLogger("kita.user_service")


class UserService:
    dao = UserAlchemyDAO

    __slots__ = (
        "session",
        "admin_id",
        "redis",
        "redis_key",
    )

    def __init__(self, session: AsyncSession, config: Config, redis: Redis):
        self.session = session
        self.admin_id = config.ADMIN_ID
        self.redis = redis

        self.redis_key = lambda x: f"user:{x}"

    def is_immune(self, user_id: int):
        return user_id == self.admin_id

    async def create(self, user_data: UserData):
        role = UserRole.ADMIN if user_data.id == self.admin_id else UserRole.USER

        prep_user_dto = UserDTO(
            user_id=user_data.id,
            username=user_data.username,
            name=user_data.full_name,
            role=role,
            is_bot_blocked=False,
        )

        prep_user_alchemy = UserAlchemy(**prep_user_dto.model_dump())

        user_alchemy = await self.dao.create(self.session, prep_user_alchemy)
        user_dto = UserDTO.model_validate(user_alchemy)

        await UserRedis.set(
            redis=self.redis,
            key=self.redis_key(user_dto.user_id),
            data=user_dto,
        )

        logger.info("Created new user %s", user_data.id)
        return user_dto

    async def get(self, user_id: int) -> UserDTO:
        cached_user = await UserRedis.get(self.redis, self.redis_key(user_id))
        if cached_user:
            return cached_user

        user_alchemy = await self.dao.get_one_or_none_by_id(self.session, user_id)
        if not user_alchemy:
            raise SQLUserNotFoundError(target_id=user_id)

        user_dto = UserDTO.model_validate(user_alchemy)

        await UserRedis.set(
            redis=self.redis,
            key=self.redis_key(user_dto.user_id),
            data=user_dto,
        )

        return user_dto

    async def update_from_data(self, user_dto: UserDTO, user_data: UserData):
        user_dto.update_from_data(user_data)
        changed_data = user_dto.prepare_changed_data()
        if not changed_data:
            return

        await self.dao.update_by_id(self.session, user_dto.user_id, changed_data)
        await UserRedis.delete(
            redis=self.redis,
            key=self.redis_key(user_dto.user_id)
        )

        logger.info(
            "Update database info for user %s. New data: %s", user_dto.user_id, changed_data
        )

    async def get_active(self):
        active = await self.dao.get_active(self.session)
        return UserDTO.from_model_list(active)

    async def get_admins(self):
        active = await self.dao.get_admins(self.session)
        return UserDTO.from_model_list(active)

    async def set_role(self, user_dto: UserDTO, target_role: UserRole):
        user_dto.role = target_role
        result = await self.dao.update_by_id(
            self.session, user_dto.user_id, user_dto.prepare_changed_data()
        )

        await UserRedis.delete(self.redis, self.redis_key(user_dto.user_id))
        return result

    async def decline_suggestion(self, user_dto: UserDTO):
        await self.dao.decline_all_suggestions(self.session, user_dto.user_id)

    async def moderate_user(self, target_id: int, target_role: UserRole, caller: UserDTO):
        if self.is_immune(target_id) or caller.user_id == target_id:
            raise UserImmuneError()
        
        target_dto = await self.get(target_id)
        await self.set_role(target_dto, target_role)

        if target_role == UserRole.BANNED:
            await self.decline_suggestion(target_dto)

        return target_dto