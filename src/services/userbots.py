from logging import getLogger
from typing import Any

from redis.asyncio import Redis

from database.dto import UserBotDTO
from database.redis import KitaKeyBuilder, RedisKey, UserBotRedis
from interfaces import BotRegistryProtocol, UserBotRepositoryProtocol
from .base import BaseService

logger = getLogger("kita.userbot_service")


class UserBotService(BaseService):
    REDIS_KEY_PART = "userbot"

    __slots__ = (
        "redis",
        "repo",
    )

    def __init__(
        self,
        redis: Redis,
        repo: UserBotRepositoryProtocol,
        bot_registry: BotRegistryProtocol,
    ):
        super().__init__(bot_registry, KitaKeyBuilder(with_user_id=False))
        self.redis = redis
        self.repo = repo

    def _get_key(self, bot_id: int):
        redis_key = RedisKey(bot_id=bot_id)
        return self._key_builder.build(redis_key, self.REDIS_KEY_PART)

    async def get(self, bot_id: int) -> UserBotDTO | None:
        cached_bot = await UserBotRedis.get(self.redis, self._get_key(bot_id))
        if cached_bot:
            return cached_bot

        userbot_dto = await self.repo.get(bot_id)
        if not userbot_dto:
            return None

        await UserBotRedis.set(
            redis=self.redis,
            key=self._get_key(bot_id),
            data=userbot_dto,
        )

        return userbot_dto

    async def create(
        self,
        token: str,
        bot_id: int,
        username: str,
        owner_id: int,
        channel_id: int,
        channel_name: str,
    ):
        await UserBotRedis.delete(redis=self.redis, key=self._get_key(bot_id))
        return await self.repo.create(
            token, bot_id, username, owner_id, channel_id, channel_name
        )

    async def update(self, bot_id: int, **data: Any):
        await self.repo.update(bot_id, **data)
        await UserBotRedis.delete(redis=self.redis, key=self._get_key(bot_id))
        logger.info("Update userbot %s", bot_id)

    async def save(self, userbot_dto: UserBotDTO):
        await self.repo.save(userbot_dto)
        await UserBotRedis.delete(redis=self.redis, key=self._get_key(userbot_dto.bot_id))
        logger.info("Update userbot %s", userbot_dto.bot_id)
