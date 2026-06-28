
from typing import Any
from logging import getLogger

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from database.dto import UserDTO
from database.redis.user import UserRedis

from interfaces.repository import UserRepositoryProtocol

logger = getLogger("kita.user_service")

class UserService:

    __slots__ = (
        "session",
        "redis",
        "redis_key",
        "repo",
    )

    def __init__(self, session: AsyncSession, redis: Redis, repo: UserRepositoryProtocol):
        self.session = session
        self.redis = redis

        self.redis_key = lambda x: f"user:{x}"
        self.repo = repo

    async def create(self, prep_user_dto: UserDTO):
        user_dto = await self.repo.create(prep_user_dto)

        await UserRedis.set(
            redis=self.redis,
            key=self.redis_key(user_dto.user_id),
            data=user_dto,
        )

        logger.info("Created new user %s", user_dto.user_id)
        logger.debug("New user data: %s", user_dto)

        return user_dto

    async def get(self, user_id: int) -> UserDTO | None:
        cached_user = await UserRedis.get(self.redis, self.redis_key(user_id))
        if cached_user:
            return cached_user

        user_dto = await self.repo.get_by_id(user_id)
        if not user_dto:
            return None
            
        await UserRedis.set(
            redis=self.redis,
            key=self.redis_key(user_dto.user_id),
            data=user_dto,
        )

        return user_dto

    async def update(self, user_id: int, **data: Any):
        await self.repo.update(user_id, **data)
        await UserRedis.delete(redis=self.redis, key=self.redis_key(user_id))
        logger.info("Update database info for user %s", user_id)

    async def save(self, user_dto: UserDTO):
        await self.repo.save(user_dto)
        await UserRedis.delete(redis=self.redis, key=self.redis_key(user_dto.user_id))
        logger.info("Update database info for user %s", user_dto.user_id)

    async def get_active(self):
        return await self.repo.get_active()

    async def get_admins(self):
        return await self.repo.get_admins()

    async def decline_suggestion(self, user_dto: UserDTO):
        await self.repo.decline_all_suggestions(user_dto.user_id)
