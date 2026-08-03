import asyncio
from logging import getLogger
from typing import ClassVar

from aiogram.types import Message
from redis.asyncio import Redis

from database.redis import MediaGroupKey, MediaGroupKeyBuilder, TgMessageRedis

from .base import KitaMiddleware

logger = getLogger(name="kita.media_group_middleware")


class MediaGroupMiddleware(KitaMiddleware):
    __event__types__: ClassVar[set[str]] = {"message"}

    __slots__ = (
        "redis",
        "tg_message_redis",
        "latency",
        "key_builder",
    )

    def __init__(
        self, redis: Redis, tg_message_redis: TgMessageRedis, latency: float = 0.3
    ) -> None:
        self.redis = redis
        self.tg_message_redis = tg_message_redis
        self.latency = latency

        self.key_builder = MediaGroupKeyBuilder()

    async def __call__(self, handler, event: Message, data: dict):
        if not isinstance(event, Message) or not event.media_group_id:
            return await handler(event, data)

        redis_key = MediaGroupKey(
            bot_id=event.bot.id, user_id=event.from_user.id, media_group_id=event.media_group_id
        )

        key = self.key_builder.build(key=redis_key, part="media_group")
        lock_key = self.key_builder.build(key=redis_key, part="lock")

        await self.tg_message_redis.rpush(key, event)

        if await self.redis.set(lock_key, "1", nx=True, ex=5):
            logger.debug("Start mediagroup processing")
            try:
                await self._process_album(key, handler, event, data)
            finally:
                await self.tg_message_redis.delete(key)
                await self.tg_message_redis.delete(lock_key)

    async def _process_album(self, key: str, handler, original_event: Message, data: dict):
        await asyncio.sleep(self.latency + 0.05)

        album = await self.tg_message_redis.lrange(key)

        album.sort(key=lambda m: m.message_id)
        data.update(album=album, media_group_id=original_event.media_group_id)

        await handler(original_event, data)
