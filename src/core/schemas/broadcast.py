from .base import BaseData


class BroadcastData(BaseData):
    is_forwarded: bool = False
    source_chat_id: int | None = None
    source_message_ids: list[int] | None = None
