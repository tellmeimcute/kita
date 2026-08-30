from collections.abc import Sequence
from typing import Any

from database.dto import UserBotDTO
from database.redis import KitaKeyBuilder, RedisKey, UserBotRedis
from interfaces import BotRegistryProtocol

from ..userbots import UserBotRepository
from .base import CachedRepository


class CachedUserBotRepository(CachedRepository):
    REDIS_KEY_PART = "userbot"

    __slots__ = ("repo",)

    def __init__(
        self,
        bot_registry: BotRegistryProtocol,
        redis: UserBotRedis,
        repo: UserBotRepository,
    ):
        key_builder = KitaKeyBuilder(with_user_id=False)
        super().__init__(bot_registry, redis, key_builder)
        self.repo = repo

    def _get_key(self, bot_id: int):
        redis_key = RedisKey(bot_id=bot_id)
        return self._key_builder.build(redis_key, self.REDIS_KEY_PART)

    async def get(self, bot_id: int) -> UserBotDTO | None:
        return await self._cache_or_load(
            self._get_key(bot_id),
            lambda: self.repo.get(bot_id),
        )

    async def get_active(self) -> Sequence[UserBotDTO]:
        return await self.repo.get_active()

    async def get_by_owner_id(self, owner_id: int) -> Sequence[UserBotDTO]:
        return await self.repo.get_by_owner_id(owner_id)

    async def create(
        self,
        token: str,
        bot_id: int,
        username: str,
        owner_id: int,
        channel_id: int,
        channel_name: str,
    ):
        result = await self.repo.create(
            token,
            bot_id,
            username,
            owner_id,
            channel_id,
            channel_name,
        )
        await self._redis.delete(self._get_key(bot_id))
        return result

    async def update(self, bot_id: int, **data: Any):
        result = await self.repo.update(bot_id, **data)
        await self._redis.delete(self._get_key(bot_id))
        return result

    async def save(self, dto: UserBotDTO):
        result = await self.repo.save(dto)
        await self._redis.delete(self._get_key(dto.bot_id))
        return result
