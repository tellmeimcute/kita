from aiogram.types import Message, MessageOriginChannel

from core.schemas.broadcast import BroadcastData


class BroadcastUseCase:
    async def prepare(self, message: Message, album: tuple[Message]) -> BroadcastData:
        is_forwarded = isinstance(message.forward_origin, MessageOriginChannel)
        return BroadcastData(
            is_forwarded=is_forwarded,
            source_chat_id=message.chat.id,
            source_message_ids=[m.message_id for m in album],
        )
