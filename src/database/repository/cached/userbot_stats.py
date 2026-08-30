from database.dto import UserBotStats
from database.redis import UserBotStatsRedis
from interfaces import (
    BotRegistryProtocol,
    MediaRepositoryProtocol,
    SuggestionRepositoryProtocol,
    UserProfileRepositoryProtocol,
)

from .base import CachedRepository


class CachedUserBotStatsRepository(CachedRepository):
    __slots__ = (
        "profile_stats",
        "suggestions_count",
        "media_count",
    )

    def __init__(
        self,
        bot_registry: BotRegistryProtocol,
        redis: UserBotStatsRedis,
        user_profile_repo: UserProfileRepositoryProtocol,
        suggestion_repo: SuggestionRepositoryProtocol,
        media_repo: MediaRepositoryProtocol,
    ):
        super().__init__(bot_registry, redis)
        self.profile_stats = user_profile_repo.bot_user_stats
        self.suggestions_count = suggestion_repo.count
        self.media_count = media_repo.count

    async def get(self) -> UserBotStats:
        key = f"kita:{self.bot.id}:bot_stats"

        if stats := await self._redis.get(key):
            return stats

        stats = await self._load()
        await self._redis.set_cache(key, stats)
        return stats

    async def _load(self) -> UserBotStats:
        profile_stats = await self.profile_stats()
        suggestions_count = await self.suggestions_count()
        media_count = await self.media_count()
        profile_stats = profile_stats._asdict()

        return UserBotStats(
            users_total=profile_stats["users_total"],
            users=profile_stats["users"],
            banned=profile_stats["banned"],
            admins=profile_stats["admins"],
            suggestions=suggestions_count,
            medias=media_count,
        )
