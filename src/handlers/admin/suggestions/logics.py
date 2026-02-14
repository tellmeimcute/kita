from logging import getLogger
from typing import Tuple

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.utils.media_group import MediaGroupBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao import SuggestionDAO
from database.models import Suggestion
from database.dto import UserDTO
from handlers.keyboards import get_main_kb_by_role
from helpers.utils import get_media_group
from helpers.message_payload import MessagePayload
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
    user_dto: UserDTO,
    notifier: Notifier,
    state: FSMContext,
    suggestions_left: int | None = None,
    data: dict | None = None,
):
    if not suggestions_left:
        data = data or await state.get_data()
        suggestions_left = data["suggestions_left"]

    left_caption = notifier.get_i18n_text("suggestion_left", {"left": suggestions_left})

    i18n_kwargs = {
        "author_username": suggestion.author.username,
        "author_id": suggestion.author_id,
        "suggestion_id": suggestion.id,
        "original_caption": suggestion.caption,
    }

    suggestion_caption = notifier.get_i18n_text("admin_get_suggestion_caption", i18n_kwargs)
    media_group.caption = f"{left_caption}\n{suggestion_caption}"

    payload = MessagePayload(content=media_group.build())
    await notifier.notify_user(user_dto, payload=payload)

    await state.set_data(
        {
            "last": suggestion.id,
            "media_group": media_group,
            "suggestion": suggestion,
            "suggestions_left": suggestions_left - 1,
        }
    )


async def go_next_suggestion(
    session: AsyncSession,
    state: FSMContext,
    user_dto: UserDTO,
    data: dict,
    notifier: Notifier,
):
    raw_suggestion = await get_active_suggestion(session)
    if not raw_suggestion:
        await state.clear()
        kb = get_main_kb_by_role(user_dto.role)
        payload =  MessagePayload(i18n_key="no_active_suggestions", reply_markup=kb)
        return await notifier.notify_user(user_dto, payload=payload)

    suggestions_left = await SuggestionDAO.get_active_count(session)
    await update_review_state(
        *raw_suggestion, user_dto, notifier, state, suggestions_left=suggestions_left, data=data
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
