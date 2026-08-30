from collections.abc import Sequence
from typing import Any

from core.schemas import UserStats
from database.dto import SuggestionBaseDTO, SuggestionFullDTO
from database.redis import RedisKey, UserStatsRedis
from interfaces import BotRegistryProtocol

from ..suggestions import SuggestionRepository
from .base import CachedRepository


class CachedSuggestionRepository(CachedRepository):
    __slots__ = ("repo",)

    def __init__(
        self,
        bot_registry: BotRegistryProtocol,
        user_stats_redis: UserStatsRedis,
        repo: SuggestionRepository,
    ):
        super().__init__(bot_registry, user_stats_redis)
        self.repo = repo

    def _get_user_stats_key(self, user_id: int):
        redis_key = RedisKey(bot_id=self.bot.id, user_id=user_id)
        return self._key_builder.build(redis_key, "user_stats")

    async def get_by_id(self, suggestion_id: int) -> SuggestionFullDTO | None:
        return await self.repo.get_by_id(suggestion_id)

    async def update(self, suggestion_id: int, **data: Any):
        return await self.repo.update(suggestion_id, **data)

    async def save(self, dto: SuggestionBaseDTO):
        result = await self.repo.save(dto)
        await self._redis.delete(self._get_user_stats_key(dto.author_id))
        return result

    async def create(
        self,
        author_id: int,
        anonymous: bool,
        mediainfo: list[Any],
        caption: str | None,
        media_group_id: str | None,
        forwarded_from: str | None,
    ):
        result = await self.repo.create(
            author_id,
            anonymous,
            mediainfo,
            caption,
            media_group_id,
            forwarded_from,
        )
        await self._redis.delete(self._get_user_stats_key(author_id))
        return result

    async def get_active(
        self,
        limit: int = 10,
        offset: int = 0,
    ) -> Sequence[SuggestionFullDTO]:
        return await self.repo.get_active(limit, offset)

    async def user_stats(self, user_id: int) -> UserStats | None:
        key = self._get_user_stats_key(user_id)

        if stats := await self._redis.get(key):
            return stats

        stats = await self.repo.user_stats(user_id)
        if stats is not None:
            await self._redis.set_cache(key, stats)
        return stats

    async def count(self) -> int:
        return await self.repo.count()
