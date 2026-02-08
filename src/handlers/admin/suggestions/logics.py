
from typing import Tuple, Any

from aiogram import Bot
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao import SuggestionDAO
from database.models import Suggestion

from helpers.utils import get_media_group

async def get_suggestion_by_id(
    session: AsyncSession, 
    suggestion_id: int
) -> Tuple[Suggestion, MediaGroupBuilder] | None:
    async with session.begin():
        suggestion = await SuggestionDAO.get_one_or_none(
            session, Suggestion.id == suggestion_id, (Suggestion.media, Suggestion.author)
        )

    if not suggestion:
        return None
    
    media_group = get_media_group(suggestion.media, suggestion.caption)
    return suggestion, media_group


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

    media_group = get_media_group(suggestion.media, caption)
    return suggestion, media_group


async def update_review_state(
    suggestion: Suggestion, 
    media_group: MediaGroupBuilder,
    chat_id: int,
    bot: Bot,
    state: FSMContext
):
    await bot.send_media_group(chat_id, media_group.build())
    await state.set_data(
        {"last": suggestion.id, "media_group": media_group, "suggestion": suggestion}
    )


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