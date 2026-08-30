from collections.abc import Sequence
from typing import Any

from database.dto import UserProfileDTO
from database.redis import UserProfileRedis
from interfaces import BotRegistryProtocol

from ..user_profile import UserProfileRepository
from .base import CachedRepository


class CachedUserProfileRepository(CachedRepository):
    REDIS_KEY_PART = "user_profile"

    __slots__ = ("repo",)

    def __init__(
        self,
        bot_registry: BotRegistryProtocol,
        redis: UserProfileRedis,
        repo: UserProfileRepository,
    ):
        super().__init__(bot_registry, redis)
        self.repo = repo

    async def get_by_id(self, user_id: int) -> UserProfileDTO | None:
        return await self._cache_or_load(
            self._get_key(user_id),
            lambda: self.repo.get_by_id(user_id),
        )

    async def get_or_create(self, user_id: int) -> UserProfileDTO:
        return await self._cache_or_load(
            self._get_key(user_id),
            lambda: self.repo.get_or_create(user_id),
        )

    async def update(self, user_id: int, **data: Any):
        result = await self.repo.update(user_id, **data)
        await self._redis.delete(self._get_key(user_id))
        return result

    async def create(self, user_id: int) -> UserProfileDTO:
        result = await self.repo.create(user_id)
        await self._redis.set_cache(self._get_key(user_id), result)
        return result

    async def get_many(
        self, limit: int = 10, offset: int = 0, order_desc: bool = False
    ) -> Sequence[UserProfileDTO]:
        return await self.repo.get_many(limit, offset, order_desc)

    async def get_active(self) -> Sequence[UserProfileDTO]:
        return await self.repo.get_active()

    async def get_admins(self) -> Sequence[UserProfileDTO]:
        return await self.repo.get_admins()

    async def get_banned(self) -> Sequence[UserProfileDTO]:
        return await self.repo.get_banned()

    async def count(self) -> int:
        return await self.repo.count()

    async def admins_count(self) -> int:
        return await self.repo.admins_count()

    async def banned_count(self) -> int:
        return await self.repo.banned_count()

    async def active_count(self) -> int:
        return await self.repo.active_count()

    async def get_active_ids(self, after_id: int | None, limit: int) -> Sequence[int]:
        return await self.repo.get_active_ids(after_id, limit)

    async def bot_user_stats(self) -> int:
        return await self.repo.bot_user_stats()

    async def decline_all_suggestions(self, user_id: int):
        return await self.repo.decline_all_suggestions(user_id)
