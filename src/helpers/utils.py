from typing import List, Sequence, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from aiogram.types import Message
from aiogram.utils.media_group import MediaGroupBuilder

from database.models import Media, Suggestion
from database.dao import SuggestionDAO, MediaDAO


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


async def create_medias(
    session: AsyncSession, 
    album: List[Message],
    suggestion: Suggestion,
):
    medias: List[Media] = []

    for message in album:
        media_type, media_id = message_get_media_and_id(message)
        if not media_id:
            continue

        media = await MediaDAO.create(
            session, filetype=media_type, telegram_file_id=media_id, suggestion=suggestion
        )

        medias.append(media)

    return medias

def get_media_group(medias: List[Media], caption: str | None = None) -> MediaGroupBuilder:
    media_group = MediaGroupBuilder(caption=caption)
    for media in medias:
        media_group.add(type=media.filetype, media=media.telegram_file_id)
    return media_group