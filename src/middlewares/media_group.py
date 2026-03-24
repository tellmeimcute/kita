import json
import asyncio

from logging import getLogger
from aiogram import BaseMiddleware
from aiogram.types import Message
from redis.asyncio import Redis


logger = getLogger(name="kita.media_group_middleware")

class MediaGroupMiddleware(BaseMiddleware):
    """
    Помещает в album все обьекты media group
    Дополнительно шлет media_group_id
    """
    
    # event fields to be cached in redis
    message_fields = {
        "message_id",
        "from_user",
        "caption",
        "forward_origin",
        "video",
        "photo",
        "animation",
        "document",
        "media_group_id",
        "chat",
        "date",
    }

    def __init__(self, redis_client: Redis, latency: float = 0.3) -> None:
        self.redis = redis_client
        self.latency = latency
        self.prefix = "media_group:"

    async def __call__(self, handler, event: Message, data: dict):
        if not isinstance(event, Message) or not event.media_group_id:
            return await handler(event, data)

        group_id = event.media_group_id
        key = f"{self.prefix}{group_id}"

        message_data = event.model_dump_json(include=self.message_fields)

        await self.redis.rpush(key, message_data)
        await self.redis.expire(key, int(self.latency * 4) + 10)

        lock_key = f"{key}:processing"
        if await self.redis.set(lock_key, "1", nx=True, ex=5):
            asyncio.create_task(self._process_album(key, handler, event, data))

        return None

    async def _process_album(self, key: str, handler, original_event: Message, data: dict):
        await asyncio.sleep(self.latency + 0.05)

        raw_list = await self.redis.lrange(key, 0, -1)
        if not raw_list:
            await self._cleanup(key)
            return

        album: list[Message] = []
        for raw in raw_list:
            try:
                msg_dict = json.loads(raw)
                msg = Message.model_validate(msg_dict)
                album.append(msg)
            except Exception as e:
                logger.error("error when proccesing mediagroup event: %s", e, exc_info=True)
                continue

        album.sort(key=lambda m: m.message_id)

        data["album"] = album
        data["media_group_id"] = original_event.media_group_id

        try:
            await handler(original_event, data)
        finally:
            await self._cleanup(key)

    async def _cleanup(self, key: str):
        await self.redis.delete(key)
        await self.redis.delete(f"{key}:processing")