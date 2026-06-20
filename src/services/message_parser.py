
from dataclasses import dataclass
from aiogram.types import Message, MessageOriginChannel

@dataclass
class MediaInfo:
    filetype: str
    telegram_file_id: str

class MessageParser:
    @staticmethod
    def parse_media(message: Message) -> MediaInfo | None:
        if message.video:
            return MediaInfo("video", message.video.file_id)
        if message.photo:
            return MediaInfo("photo", message.photo[-1].file_id)
        if message.animation:
            return MediaInfo("document", message.animation.file_id)
        if message.document:
            return MediaInfo("document", message.document.file_id)
        return None

    @staticmethod
    def parse_forward_origin(message: Message) -> str | None:
        origin = message.forward_origin
        if isinstance(origin, MessageOriginChannel):
            return origin.chat.full_name
        return None
    