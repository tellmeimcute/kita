
from typing import Tuple, Any

from aiogram import Bot
from aiogram.types import Message
from aiogram.utils.media_group import MediaGroupBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao import SuggestionDAO
from database.models import Suggestion


async def get_suggestions_logic(
    message: Message, 
    session: AsyncSession, 
    bot: Bot, 
    suggestion_id: int
):
    async with session.begin():
        suggestion = await SuggestionDAO.get_one_or_none(
            session, Suggestion.id == suggestion_id, (Suggestion.media, Suggestion.author)
        )

    if not suggestion:
        return
    
    medias = suggestion.media
    media_group = MediaGroupBuilder(
        caption=suggestion.caption
    )

    for media in medias:
        media_group.add(type=media.filetype, media=media.telegram_file_id)

    await bot.send_message(
        message.chat.id,
        f"Предложка от @{suggestion.author.username} ({suggestion.author_id}):"
    )

    await bot.send_media_group(
        message.chat.id,
        media=media_group.build()
    )


async def get_active_suggestion(
    session: AsyncSession, order_by: Any = None
) -> Tuple[Suggestion, MediaGroupBuilder] | None:
    
    async with session.begin():
        suggestion = await SuggestionDAO.get_one_or_none(
            session, Suggestion.accepted.is_(None), (Suggestion.media, Suggestion.author), order_by
        )

    if not suggestion:
        return None

    caption = (
        f"Предложка от @{suggestion.author.username} ({suggestion.author_id}):\n\n"
        f"ID: {suggestion.id}\n"
        f"Оригинальная подпись:\n"
        f"{suggestion.caption}"
    )

    media_group = MediaGroupBuilder(caption=caption)
    for media in suggestion.media:
        media_group.add(type=media.filetype, media=media.telegram_file_id)

    return suggestion, media_group

async def post_in_channel(
    bot: Bot,
    media_group: MediaGroupBuilder,
    suggestion: Suggestion,
    channel_id: int,
    with_og_caption: bool = True
):
    new_caption = "#предложка"
    if with_og_caption and suggestion.caption:
        new_caption = f"{suggestion.caption}\n\n{new_caption}"

    media_group.caption = new_caption
    await bot.send_media_group(channel_id, media=media_group.build())