
from typing import Any
from logging import getLogger

from redis.asyncio import Redis
from database.dto import UserProfileDTO
from database.redis import UserProfileRedis, KitaKeyBuilder, RedisKey
from interfaces import UserProfileRepositoryProtocol, BotRegistryProtocol

logger = getLogger("kita.user_profile_service")

class UserProfileService:

    __slots__ = (
        "redis",
        "repo",
        "bot_registry",
        "key_builder",
    )

    def __init__(
        self,
        redis: Redis,
        repo: UserProfileRepositoryProtocol,
        bot_registry: BotRegistryProtocol,
    ):
        self.redis = redis
        self.repo = repo
        self.bot_registry = bot_registry
        self.key_builder = KitaKeyBuilder()

    def _get_key(self, user_id: int):
        redis_key = RedisKey(
            bot_id=self.bot_registry.get_current().id,
            user_id=user_id,
        )
        return self.key_builder.build(key=redis_key, part="user_profile")

    async def get_or_create(self, user_id: int) -> UserProfileDTO:
        cached = await UserProfileRedis.get(self.redis, self._get_key(user_id))
        if cached:
            return cached

        profile_dto = await self.repo.get_or_create(user_id)

        await UserProfileRedis.set(
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

        await UserProfileRedis.set(
            redis=self.redis,
            key=self._get_key(user_id),
            data=profile_dto,
        )
        return profile_dto

    async def create(self, user_id: int) -> UserProfileDTO:
        profile_dto = await self.repo.create(user_id)
        await UserProfileRedis.set(
            redis=self.redis,
            key=self._get_key(user_id),
            data=profile_dto,
        )
        return profile_dto

    async def update(self, user_id: int, **data: Any):
        await self.repo.update(user_id, **data)
        await UserProfileRedis.delete(redis=self.redis, key=self._get_key(user_id))
        logger.info("Update user profile %s for bot %s", user_id, self.bot_registry.get_current().id)

    async def save(self, profile_dto: UserProfileDTO):
        changed = profile_dto.prepare_changed_data()
        if not changed:
            return
        
        await self.repo.update(profile_dto.user_id, **changed)
        await UserProfileRedis.delete(redis=self.redis, key=self._get_key(profile_dto.user_id))
        logger.info("Update user profile %s for bot %s", profile_dto.user_id, self.bot_registry.get_current().id)

    async def get_active(self):
        return await self.repo.get_active()

    async def get_admins(self):
        return await self.repo.get_admins()

    async def decline_suggestion(self, profile_dto: UserProfileDTO):
        await self.repo.decline_all_suggestions(profile_dto.user_id)
