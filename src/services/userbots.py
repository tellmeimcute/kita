from typing import Any

from loguru import logger

from database.dto import UserBotDTO
from database.redis import KitaKeyBuilder, RedisKey, UserBotRedis
from interfaces import BotRegistryProtocol, UserBotRepositoryProtocol

from .base import BaseService


class UserBotService(BaseService):
    REDIS_KEY_PART = "userbot"

    __slots__ = (
        "userbot_redis",
        "repo",
        "owner_userbots_key",
    )

    def __init__(
        self,
        userbot_redis: UserBotRedis,
        repo: UserBotRepositoryProtocol,
        bot_registry: BotRegistryProtocol,
    ):
        super().__init__(bot_registry, KitaKeyBuilder(with_user_id=False))

        self.userbot_redis = userbot_redis
        self.repo = repo

        self.owner_userbots_key = KitaKeyBuilder(with_bot_id=False)

    def _get_key(self, bot_id: int):
        redis_key = RedisKey(bot_id=bot_id)
        return self._key_builder.build(redis_key, self.REDIS_KEY_PART)

    def _get_owner_key(self, owner_id: int):
        redis_key = RedisKey(user_id=owner_id)
        return self.owner_userbots_key.build(redis_key, "owner_userbots")

    async def get(self, bot_id: int) -> UserBotDTO | None:
        cached_bot = await self.userbot_redis.get(self._get_key(bot_id))
        if cached_bot:
            return cached_bot

        userbot_dto = await self.repo.get(bot_id)
        if not userbot_dto:
            return None

        await self.userbot_redis.set_cache(
            key=self._get_key(bot_id),
            data=userbot_dto,
        )

        return userbot_dto

    async def get_by_owner_id(self, owner_id: int):
        key = self._get_owner_key(owner_id)

        owner_userbots = await self.userbot_redis.lrange(key)
        if owner_userbots:
            return owner_userbots

        userbots = await self.repo.get_by_owner_id(owner_id)
        if userbots:
            await self.userbot_redis.rpush(key, *userbots)
        return userbots

    async def create(
        self,
        token: str,
        bot_id: int,
        username: str,
        owner_id: int,
        channel_id: int,
        channel_name: str,
    ):
        await self.userbot_redis.delete(self._get_owner_key(owner_id))
        await self.userbot_redis.delete(self._get_key(bot_id))

        return await self.repo.create(token, bot_id, username, owner_id, channel_id, channel_name)

    async def update(self, bot_id: int, **data: Any):
        await self.repo.update(bot_id, **data)
        await self.userbot_redis.delete(self._get_key(bot_id))
        logger.info("Update userbot {}", bot_id)

    async def save(self, userbot_dto: UserBotDTO):
        await self.repo.save(userbot_dto)
        await self.userbot_redis.delete(self._get_key(userbot_dto.bot_id))
        logger.info("Update userbot {}", userbot_dto.bot_id)
