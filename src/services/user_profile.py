from typing import Any

from loguru import logger

from database.dto import UserProfileDTO
from database.redis import UserProfileRedis
from interfaces import BotRegistryProtocol, UserProfileRepositoryProtocol

from .base import BaseService


class UserProfileService(BaseService):
    REDIS_KEY_PART = "user_profile"

    __slots__ = ("user_profile_redis", "repo")

    def __init__(
        self,
        user_profile_redis: UserProfileRedis,
        repo: UserProfileRepositoryProtocol,
        bot_registry: BotRegistryProtocol,
    ):
        super().__init__(bot_registry)
        self.user_profile_redis = user_profile_redis
        self.repo = repo

    async def get_or_create(self, user_id: int) -> UserProfileDTO:
        cached = await self.user_profile_redis.get(self._get_key(user_id))
        if cached:
            return cached

        profile_dto = await self.repo.get_or_create(user_id)

        await self.user_profile_redis.set_cache(
            key=self._get_key(user_id),
            data=profile_dto,
        )
        return profile_dto

    async def get(self, user_id: int) -> UserProfileDTO | None:
        cached = await self.user_profile_redis.get(self._get_key(user_id))
        if cached:
            return cached

        profile_dto = await self.repo.get(user_id)
        if not profile_dto:
            return None

        await self.user_profile_redis.set_cache(
            key=self._get_key(user_id),
            data=profile_dto,
        )
        return profile_dto

    async def get_many(self, limit: int = 10, offset: int = 0):
        return await self.repo.get_many(limit, offset)

    async def create(self, user_id: int) -> UserProfileDTO:
        profile_dto = await self.repo.create(user_id)
        await self.user_profile_redis.set_cache(
            key=self._get_key(user_id),
            data=profile_dto,
        )
        return profile_dto

    async def update(self, user_id: int, **data: Any):
        await self.repo.update(user_id, **data)
        await self.user_profile_redis.delete(self._get_key(user_id))
        logger.info("Update user profile {} for bot {}", user_id, self.bot.id)

    async def save(self, profile_dto: UserProfileDTO):
        changed = profile_dto.prepare_changed_data()
        if not changed:
            return

        await self.repo.update(profile_dto.user_id, **changed)
        await self.user_profile_redis.delete(self._get_key(profile_dto.user_id))
        logger.info("Update user profile {} for bot {}", profile_dto.user_id, self.bot.id)

    async def get_active(self):
        return await self.repo.get_active()

    async def get_admins(self):
        return await self.repo.get_admins()

    async def decline_suggestion(self, profile_dto: UserProfileDTO):
        await self.repo.decline_all_suggestions(profile_dto.user_id)
