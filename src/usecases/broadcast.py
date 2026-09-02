import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

from aiogram.types import Message, MessageOriginChannel
from redis.asyncio import Redis

from core.schemas.broadcast import BroadcastData
from database.redis import KitaKeyBuilder, RedisKey
from interfaces import BotRegistryProtocol, MessageNotifierProtocol, UserProfileServiceProtocol


@dataclass(frozen=True)
class BatchResult:
    total: int
    delivered: int


class BroadcastUseCase:
    def __init__(
        self,
        redis: Redis,
        bot_registry: BotRegistryProtocol,
        notifier: MessageNotifierProtocol,
        profile_service: UserProfileServiceProtocol,
    ):
        self.redis = redis
        self.bot_registry = bot_registry
        self.notifier = notifier
        self.profile_service = profile_service

        self.bot = bot_registry.get_current()
        self.key_builder = KitaKeyBuilder(with_user_id=False)

    def lock_key(self):
        redis_key = RedisKey(bot_id=self.bot.id)
        return self.key_builder.build(redis_key, "broadcast")

    async def lock(self):
        return await self.redis.set(self.lock_key(), "1", nx=True, ex=3600)

    async def unlock(self):
        return await self.redis.delete(self.lock_key())

    async def prepare(self, message: Message, album: tuple[Message]) -> BroadcastData:
        is_forwarded = isinstance(message.forward_origin, MessageOriginChannel)
        return BroadcastData(
            is_forwarded=is_forwarded,
            source_chat_id=message.chat.id,
            source_message_ids=[m.message_id for m in album],
        )

    async def execute_batch(
        self,
        user_ids: Sequence[int],
        source_chat_id: int,
        source_message_ids: Sequence[int],
        is_forwarded: bool,
    ):
        send_func = (
            self.notifier.forward if is_forwarded else self.notifier.copy
        )

        total = 0
        delivered = 0

        tasks = []
        for user_id in user_ids:
            user_profile = await self.profile_service.get(user_id)
            tasks.append(send_func(user_profile, source_chat_id, source_message_ids))
            total += 1

        for res in await asyncio.gather(*tasks, return_exceptions=True):
            if isinstance(res, (list, tuple)):
                delivered += 1

        return BatchResult(total, delivered)
