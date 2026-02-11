from typing import List, Tuple

from aiogram.types import Message
from aiogram.utils.media_group import MediaGroupBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import MediaDAO, UserAlchemyDAO
from database.models import Media, Suggestion


async def ban_user(
    session: AsyncSession,
    target_id: int,
    config: Config,
) -> bool:
    if int(target_id) == config.ADMIN_ID:
        return False
    await UserAlchemyDAO.change_role(session, target_id, "banned")
    return True


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
