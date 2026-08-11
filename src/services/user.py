from typing import Any

from loguru import logger

from database.dto import UserDTO
from database.redis import KitaKeyBuilder, UserRedis
from interfaces import BotRegistryProtocol, UserRepositoryProtocol

from .base import BaseService


class UserService(BaseService):
    REDIS_KEY_PART = "user"

    __slots__ = (
        "user_redis",
        "repo",
    )

    def __init__(
        self,
        user_redis: UserRedis,
        repo: UserRepositoryProtocol,
        bot_registry: BotRegistryProtocol,
    ):
        super().__init__(bot_registry, KitaKeyBuilder(with_bot_id=False))

        self.user_redis = user_redis
        self.repo = repo

    async def create(self, prep_user_dto: UserDTO):
        user_dto = await self.repo.create(prep_user_dto)

        await self.user_redis.set_cache(
            key=self._get_key(user_dto.user_id),
            data=user_dto,
        )

        logger.info("Created new user {}", user_dto.user_id)
        logger.debug("New user data: {}", user_dto)

        return user_dto

    async def get(self, user_id: int) -> UserDTO | None:
        cached_user = await self.user_redis.get(self._get_key(user_id))
        if cached_user:
            return cached_user

        user_dto = await self.repo.get_by_id(user_id)
        if not user_dto:
            return None

        await self.user_redis.set_cache(
            key=self._get_key(user_dto.user_id),
            data=user_dto,
        )

        return user_dto

    async def get_or_create(self, prep_user_dto: UserDTO) -> UserDTO:
        cached = await self.user_redis.get(self._get_key(prep_user_dto.user_id))
        if cached:
            return cached

        user_dto = await self.repo.get_or_create(prep_user_dto)

        await self.user_redis.set_cache(
            key=self._get_key(prep_user_dto.user_id),
            data=user_dto,
        )

        return user_dto

    async def update(self, user_id: int, **data: Any):
        await self.repo.update(user_id, **data)
        await self.user_redis.delete(self._get_key(user_id))
        logger.info("Update database info for user {}", user_id)

    async def save(self, user_dto: UserDTO):
        changed = user_dto.prepare_changed_data()
        if not changed:
            return

        await self.repo.update(user_dto.user_id, **changed)
        await self.user_redis.delete(self._get_key(user_dto.user_id))
        logger.info("Update database info for user {}", user_dto.user_id)
