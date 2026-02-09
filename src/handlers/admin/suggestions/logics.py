from logging import getLogger
from typing import Any, Tuple

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.utils.media_group import MediaGroupBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao import SuggestionDAO
from database.models import Suggestion
from helpers.utils import get_media_group

logger = getLogger("admin_suggestions")


async def get_suggestion_by_id(
    session: AsyncSession,
    suggestion_id: int,
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
    session: AsyncSession,
    order_by: Any = None,
) -> Tuple[Suggestion, MediaGroupBuilder] | None:
    suggestion = await SuggestionDAO.get_one_or_none(
        session, Suggestion.accepted.is_(None), (Suggestion.media, Suggestion.author), order_by
    )

    if not suggestion:
        return None

    media_group = get_media_group(suggestion.media, suggestion.caption)
    return suggestion, media_group


async def update_review_state(
    suggestion: Suggestion,
    media_group: MediaGroupBuilder,
    chat_id: int,
    bot: Bot,
    state: FSMContext,
    suggestions_left: int | None = None,
    data: dict | None = None,
):
    if not suggestions_left:
        data = data or await state.get_data()
        suggestions_left = data["suggestions_left"]

    suggestions_left -= 1
    media_group.caption = (
        f"Постов в очереди: этот + {suggestions_left}шт.\n\n"
        f"Предложка от @{suggestion.author.username} ({suggestion.author_id}):\n\n"
        f"ID: {suggestion.id}\n"
        f"Оригинальная подпись:\n"
        f"{suggestion.caption}"
    )

    await bot.send_media_group(chat_id, media_group.build())
    await state.set_data(
        {
            "last": suggestion.id,
            "media_group": media_group,
            "suggestion": suggestion,
            "suggestions_left": suggestions_left,
        }
    )


async def post_in_channel(
    bot: Bot,
    media_group: MediaGroupBuilder,
    suggestion: Suggestion,
    channel_id: int,
    with_og_caption: bool = True,
):
    new_caption = "#предложка"
    if with_og_caption and suggestion.caption:
        new_caption = f"{suggestion.caption}\n\n{new_caption}"

    media_group.caption = new_caption
    try:
        await bot.send_media_group(channel_id, media=media_group.build())
    except Exception as e:
        logger.error("Ошибка при отправке предложки в канал: %s", e)
