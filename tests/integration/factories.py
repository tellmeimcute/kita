from datetime import UTC, datetime
from typing import Any

from aiogram.types import (
    Animation,
    Chat,
    Document,
    Message,
    MessageOriginChannel,
    PhotoSize,
    Video,
)

from .scaffold import CHANNEL_ID


def make_tg_message(
    *,
    message_id: int,
    text: str | None = None,
    caption: str | None = None,
    photo: str | None = None,
    video: str | None = None,
    document: str | None = None,
    animation: str | None = None,
    media_group_id: str | None = None,
    forwarded_from: str | None = None,
) -> Message:
    kwargs: dict[str, Any] = {
        "message_id": message_id,
        "date": datetime.now(UTC),
        "chat": Chat(id=CHANNEL_ID, type="channel"),
    }

    if text is not None:
        kwargs["text"] = text
    if caption is not None:
        kwargs["caption"] = caption
    if photo is not None:
        kwargs["photo"] = [PhotoSize(file_id=photo, file_unique_id=photo, width=800, height=600)]
    if video is not None:
        kwargs["video"] = Video(
            file_id=video,
            file_unique_id=video,
            width=800,
            height=600,
            duration=5,
        )
    if document is not None:
        kwargs["document"] = Document(file_id=document, file_unique_id=document)
    if animation is not None:
        kwargs["animation"] = Animation(
            file_id=animation,
            file_unique_id=animation,
            width=800,
            height=600,
            duration=5,
        )
    if media_group_id is not None:
        kwargs["media_group_id"] = media_group_id
    if forwarded_from is not None:
        kwargs["forward_origin"] = MessageOriginChannel(
            date=datetime.now(UTC),
            chat=Chat(id=CHANNEL_ID, type="channel", title=forwarded_from),
            message_id=1,
        )

    return Message(**kwargs)
