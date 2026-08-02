
from logging import getLogger
from typing import Any

from redis.asyncio import Redis

from database.dto import UserDTO
from database.redis import KitaKeyBuilder, UserRedis
from interfaces import UserRepositoryProtocol, BotRegistryProtocol
from .base import BaseService

logger = getLogger("kita.user_service")

class UserService(BaseService):

    REDIS_KEY_PART = "user"

    __slots__ = (
        "redis",
        "repo",
    )

    def __init__(
        self,
        redis: Redis,
        repo: UserRepositoryProtocol,
        bot_registry: BotRegistryProtocol,
    ):
        super().__init__(bot_registry, KitaKeyBuilder(with_bot_id=False))

        self.redis = redis
        self.repo = repo

    async def create(self, prep_user_dto: UserDTO):
        user_dto = await self.repo.create(prep_user_dto)

        await UserRedis.set_cache(
            redis=self.redis,
            key=self._get_key(user_dto.user_id),
            data=user_dto,
        )

        logger.info("Created new user %s", user_dto.user_id)
        logger.debug("New user data: %s", user_dto)

        return user_dto

    async def get(self, user_id: int) -> UserDTO | None:
        cached_user = await UserRedis.get(self.redis, self._get_key(user_id))
        if cached_user:
            return cached_user

        user_dto = await self.repo.get_by_id(user_id)
        if not user_dto:
            return None

        await UserRedis.set_cache(
            redis=self.redis,
            key=self._get_key(user_dto.user_id),
            data=user_dto,
        )

        return user_dto

    async def get_or_create(self, prep_user_dto: UserDTO) -> UserDTO:
        cached = await UserRedis.get(
            self.redis, self._get_key(prep_user_dto.user_id)
        )
        if cached:
            return cached

        user_dto = await self.repo.get_or_create(prep_user_dto)

        await UserRedis.set_cache(
            redis=self.redis,
            key=self._get_key(prep_user_dto.user_id),
            data=user_dto,
        )

        return user_dto

    async def update(self, user_id: int, **data: Any):
        await self.repo.update(user_id, **data)
        await UserRedis.delete(redis=self.redis, key=self._get_key(user_id))
        logger.info("Update database info for user %s", user_id)

    async def save(self, user_dto: UserDTO):
        changed = user_dto.prepare_changed_data()
        if not changed:
            return
        
        await self.repo.update(user_dto.user_id, **changed)
        await UserRedis.delete(redis=self.redis, key=self._get_key(user_dto.user_id))
        logger.info("Update database info for user %s", user_dto.user_id)
