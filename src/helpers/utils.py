from typing import List, Sequence, Tuple

from aiogram.types import Message
from aiogram.utils.media_group import MediaGroupBuilder

from database.models import Media, Suggestion


def message_get_media_and_id(msg: Message) -> Tuple[str, str]:
    if msg.video:
        return "video", msg.video.file_id
    elif msg.photo:
        return "photo", msg.photo[-1].file_id
    elif msg.animation:
        return "document", msg.animation.file_id
    elif msg.document:
        return "document", msg.document.file_id
    return None, None


def get_media_group(medias: List[Media], caption: str | None = None) -> MediaGroupBuilder:
    media_group = MediaGroupBuilder(caption=caption)
    for media in medias:
        media_group.add(type=media.filetype, media=media.telegram_file_id)
    return media_group


def build_album_suggestions(
    album: Sequence[Message],
    author_id: int,
    media_group_id: str | None,
) -> Tuple[Suggestion, List[Media], MediaGroupBuilder]:
    suggestion: Suggestion = Suggestion(author_id=author_id, media_group_id=media_group_id)
    medias: List[Media] = []

    media_group = MediaGroupBuilder()

    for s_msg in album:
        media_type, media_id = message_get_media_and_id(s_msg)
        if not media_id:
            continue

        media_group.add(type=media_type, media=media_id)

        if s_msg.caption:
            media_group.caption = s_msg.caption
            suggestion.caption = s_msg.caption

        medias.append(Media(filetype=media_type, telegram_file_id=media_id, suggestion=suggestion))

    return suggestion, medias, media_group
