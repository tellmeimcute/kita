
from typing import Any
from logging import getLogger

from redis.asyncio import Redis
from database.dto import UserDTO
from database.redis import UserRedis, KitaKeyBuilder, RedisKey
from interfaces import UserRepositoryProtocol

logger = getLogger("kita.user_service")

class UserService:

    __slots__ = (
        "redis",
        "repo",
        "key_builder",
    )

    def __init__(
        self,
        redis: Redis,
        repo: UserRepositoryProtocol,
    ):
        self.redis = redis
        self.repo = repo
        self.key_builder = KitaKeyBuilder(with_bot_id=False)

    def _get_key(self, user_id: int):
        redis_key = RedisKey(user_id=user_id)
        return self.key_builder.build(key=redis_key, part="user")

    async def create(self, prep_user_dto: UserDTO):
        user_dto = await self.repo.create(prep_user_dto)

        await UserRedis.set(
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

        await UserRedis.set(
            redis=self.redis,
            key=self._get_key(user_dto.user_id),
            data=user_dto,
        )

        return user_dto

    async def update(self, user_id: int, **data: Any):
        await self.repo.update(user_id, **data)
        await UserRedis.delete(redis=self.redis, key=self._get_key(user_id))
        logger.info("Update database info for user %s", user_id)

    async def save(self, user_dto: UserDTO):
        await self.repo.save(user_dto)
        await UserRedis.delete(redis=self.redis, key=self._get_key(user_dto.user_id))
        logger.info("Update database info for user %s", user_dto.user_id)
