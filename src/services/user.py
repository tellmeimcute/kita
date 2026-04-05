
from logging import getLogger
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import UserAlchemyDAO
from database.dto import UserDTO
from database.models import UserAlchemy
from database.roles import UserRole
from helpers.schemas.objects import UserData
from helpers.exceptions import UserImmuneError, SQLModelNotFoundError

logger = getLogger("kita.user_service")


class UserService:
    dao = UserAlchemyDAO

    __slots__ = (
        "session",
        'config',
    )

    def __init__(self, session: AsyncSession, config: Config):
        self.session = session
        self.config = config

    def is_immune(self, user_id: int):
        return user_id == self.config.ADMIN_ID

    async def cache_user(self, user_dto: UserDTO):
        key = f"user:{user_dto.user_id}"
        data = user_dto.model_dump_json()
        await self.config.redis.set(
            name=key,
            value=data,
            ex=60,
        )

    async def get_cache_user(self, user_id: int):
        key = f"user:{user_id}"
        raw = await self.config.redis.get(key)
        if not raw:
            return None
        try:
            return UserDTO.model_validate_json(raw)
        except Exception as e:
            logger.error("Fail to get user from cache: %s", e, exc_info=True)
            await self.config.redis.delete(key)
            return None
        
    async def cache_user_exists(self, user_id: int) -> bool:
        return bool(await self.config.redis.exists(f"user:{user_id}"))
    
    async def cache_user_delete(self, user_id: int):
        return await self.config.redis.delete(f"user:{user_id}")

    async def create(self, user_data: UserData):
        role = UserRole.ADMIN if user_data.id == self.config.ADMIN_ID else UserRole.USER

        prep_user_dto = UserDTO(
            user_id=user_data.id,
            username=user_data.username,
            name=user_data.full_name,
            role=role,
            is_bot_blocked=False,
        )

        prep_user_alchemy = UserAlchemy(**prep_user_dto.model_dump())

        user_alchemy = await self.dao.create(self.session, prep_user_alchemy)

        logger.info("Created new user %s", user_data.id)
        user_dto = UserDTO.model_validate(user_alchemy)
        await self.cache_user(user_dto)

        return user_dto

    async def get(self, user_id: int) -> UserDTO:
        cached_user = await self.get_cache_user(user_id)
        if cached_user:
            return cached_user

        user_alchemy = await self.dao.get_one_or_none_by_id(self.session, user_id)

        if not user_alchemy:
            raise SQLModelNotFoundError()

        user_dto = UserDTO.model_validate(user_alchemy)
        await self.cache_user(user_dto)
        return user_dto

    async def update_from_data(self, user_dto: UserDTO, user_data: UserData):
        user_dto.update_from_data(user_data)
        changed_data = user_dto.prepare_changed_data()
        if not changed_data:
            return

        await self.dao.update_by_id(self.session, user_dto.user_id, changed_data)
        await self.cache_user_delete(user_dto.user_id)

        logger.info(
            "Update database info for user %s. New data: %s", user_dto.user_id, changed_data
        )

    async def get_active(self):
        active = await self.dao.get_active(self.session)
        return UserDTO.from_model_list(active)

    async def get_admins(self):
        active = await self.dao.get_admins(self.session)
        return UserDTO.from_model_list(active)

    async def set_role(self, user_dto: UserDTO, role: UserRole):
        if self.is_immune(user_dto.user_id):
            raise UserImmuneError()

        user_dto.role = role
        result = await self.dao.update_by_id(
            self.session, user_dto.user_id, user_dto.prepare_changed_data()
        )

        await self.cache_user_delete(user_dto.user_id)
        return result

    async def decline_suggestion(self, user_dto: UserDTO):
        await self.dao.decline_all_suggestions(self.session, user_dto.user_id)

        