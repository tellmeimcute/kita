
from logging import getLogger

from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from database.dao import UserAlchemyDAO
from database.dto import UserDTO
from database.models import UserAlchemy
from database.roles import UserRole
from database.redis.user import UserRedis

from core.exceptions import SQLUserNotFoundError

logger = getLogger("kita.user_service")


class UserService:
    dao = UserAlchemyDAO

    __slots__ = (
        "session",
        "redis",
        "redis_key",
    )

    def __init__(self, session: AsyncSession, redis: Redis):
        self.session = session
        self.redis = redis

        self.redis_key = lambda x: f"user:{x}"

    async def create(self, prep_user_dto: UserDTO):
        prep_user_alchemy = UserAlchemy(**prep_user_dto.model_dump())

        user_alchemy = await self.dao.create(self.session, prep_user_alchemy)
        user_dto = UserDTO.model_validate(user_alchemy)

        await UserRedis.set(
            redis=self.redis,
            key=self.redis_key(user_dto.user_id),
            data=user_dto,
        )

        logger.info("Created new user %s", user_dto.user_id)
        logger.debug("New user data: %s", user_dto)
        return user_dto

    async def get(self, user_id: int) -> UserDTO:
        cached_user = await UserRedis.get(self.redis, self.redis_key(user_id))
        if cached_user:
            return cached_user

        user_alchemy = await self.dao.get_one_or_none_by_user_id(self.session, user_id)
        if not user_alchemy:
            raise SQLUserNotFoundError(target_id=user_id)

        user_dto = UserDTO.model_validate(user_alchemy)

        await UserRedis.set(
            redis=self.redis,
            key=self.redis_key(user_dto.user_id),
            data=user_dto,
        )

        return user_dto

    async def update_from_data(self, user_dto: UserDTO, changed_data: dict):
        if not changed_data:
            return

        await self.dao.update_by_user_id(self.session, user_dto.user_id, changed_data)
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
        changed_data = user_dto.prepare_changed_data()
        await self.update_from_data(user_dto, changed_data)

    async def decline_suggestion(self, user_dto: UserDTO):
        await self.dao.decline_all_suggestions(self.session, user_dto.user_id)