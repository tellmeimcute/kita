import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

from aiogram.types import Message, MessageOriginChannel

from core.schemas.broadcast import BroadcastData
from interfaces import NotifierServiceProtocol, UserProfileServiceProtocol


@dataclass(frozen=True)
class BatchResult:
    total: int
    delivered: int


class BroadcastUseCase:
    def __init__(
        self, notifier: NotifierServiceProtocol, profile_service: UserProfileServiceProtocol
    ):
        self.notifier = notifier
        self.profile_service = profile_service

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
        send_func = self.notifier.forward_messages if is_forwarded else self.notifier.copy_messages

        total = 0
        delivered = 0

        tasks = []
        for user_id in user_ids:
            user_profile = await self.profile_service.get(user_id)
            tasks.append(send_func(user_profile, source_message_ids, source_chat_id))
            total += 1

        for res in await asyncio.gather(*tasks, return_exceptions=True):
            if isinstance(res, (list, tuple)):
                delivered += 1

        return BatchResult(total, delivered)
