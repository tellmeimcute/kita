from logging import getLogger
from typing import Any, Tuple

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.media_group import MediaGroupBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao import SuggestionDAO
from database.models import Suggestion
from database.roles import UserRole
from handlers.keyboards import get_main_kb_by_role
from helpers.utils import get_media_group
from services.notifier import Notifier

logger = getLogger("admin_suggestions")


async def get_suggestion_by_id(
    session: AsyncSession,
    suggestion_id: int,
) -> Tuple[Suggestion, MediaGroupBuilder] | None:
    suggestion = await SuggestionDAO.get_one_or_none_by_id(session, suggestion_id)

    if not suggestion:
        return None

    media_group = get_media_group(suggestion.media, suggestion.caption)
    return suggestion, media_group


async def get_active_suggestion(
    session: AsyncSession,
) -> Tuple[Suggestion, MediaGroupBuilder] | None:
    suggestion = await SuggestionDAO.get_active(session)

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

    #suggestions_left -= 1
    media_group.caption = (
        f"Постов в очереди: {suggestions_left}.\n\n"
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
            "suggestions_left": suggestions_left - 1,
        }
    )


async def go_next_suggestion(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    role: UserRole,
    data: dict,
    notifier: Notifier,
):
    raw_suggestion = await get_active_suggestion(session)
    if not raw_suggestion:
        await state.clear()
        return await notifier.notify_admin_no_active_suggestions(message.from_user.id, role)

    chat_id = message.chat.id
    suggestions_left = await SuggestionDAO.get_active_count(session)
    await update_review_state(
        *raw_suggestion, chat_id, bot, state, suggestions_left=suggestions_left, data=data
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
