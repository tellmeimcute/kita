
from logging import getLogger
from typing import Any

from redis.asyncio import Redis

from database.dto import UserProfileDTO
from database.redis import UserProfileRedis
from interfaces import BotRegistryProtocol, UserProfileRepositoryProtocol
from .base import BaseService

logger = getLogger("kita.user_profile_service")

class UserProfileService(BaseService):
    
    REDIS_KEY_PART = "user_profile"

    __slots__ = ("redis", "repo")

    def __init__(
        self,
        redis: Redis,
        repo: UserProfileRepositoryProtocol,
        bot_registry: BotRegistryProtocol,
    ):
        super().__init__(bot_registry)
        self.redis = redis
        self.repo = repo

    async def get_or_create(self, user_id: int) -> UserProfileDTO:
        cached = await UserProfileRedis.get(self.redis, self._get_key(user_id))
        if cached:
            return cached

        profile_dto = await self.repo.get_or_create(user_id)

        await UserProfileRedis.set_cache(
            redis=self.redis,
            key=self._get_key(user_id),
            data=profile_dto,
        )
        return profile_dto

    async def get(self, user_id: int) -> UserProfileDTO | None:
        cached = await UserProfileRedis.get(self.redis, self._get_key(user_id))
        if cached:
            return cached

        profile_dto = await self.repo.get(user_id)
        if not profile_dto:
            return None

        await UserProfileRedis.set_cache(
            redis=self.redis,
            key=self._get_key(user_id),
            data=profile_dto,
        )
        return profile_dto

    async def create(self, user_id: int) -> UserProfileDTO:
        profile_dto = await self.repo.create(user_id)
        await UserProfileRedis.set_cache(
            redis=self.redis,
            key=self._get_key(user_id),
            data=profile_dto,
        )
        return profile_dto

    async def update(self, user_id: int, **data: Any):
        await self.repo.update(user_id, **data)
        await UserProfileRedis.delete(redis=self.redis, key=self._get_key(user_id))
        logger.info("Update user profile %s for bot %s", user_id, self.bot.id)

    async def save(self, profile_dto: UserProfileDTO):
        changed = profile_dto.prepare_changed_data()
        if not changed:
            return
        
        await self.repo.update(profile_dto.user_id, **changed)
        await UserProfileRedis.delete(redis=self.redis, key=self._get_key(profile_dto.user_id))
        logger.info("Update user profile %s for bot %s", profile_dto.user_id, self.bot.id)

    async def get_active(self):
        return await self.repo.get_active()

    async def get_admins(self):
        return await self.repo.get_admins()

    async def decline_suggestion(self, profile_dto: UserProfileDTO):
        await self.repo.decline_all_suggestions(profile_dto.user_id)
