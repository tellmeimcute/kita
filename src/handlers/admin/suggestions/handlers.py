from aiogram import Bot, F, Router, html
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.media_group import MediaGroupBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import SuggestionDAO
from database.dto import UserDTO
from database.models import Suggestion
from handlers.keyboards import accept_decline_kb, get_main_kb_by_role
from helpers.message_payload import MessagePayload
from helpers.utils import ban_user
from services.notifier import Notifier

from .logics import (
    get_active_suggestion,
    get_suggestion_by_id,
    go_next_suggestion,
    post_in_channel,
    update_review_state,
)
from .state import SuggestionViewer

router = Router(name="admin_suggestions")


@router.message(Command("get_suggestion", prefix="/!"))
async def get_suggestion(
    message: Message,
    session: AsyncSession,
    command: CommandObject,
    user_dto: UserDTO,
    notifier: Notifier,
):
    suggestion_id = command.args
    raw_suggestion = await get_suggestion_by_id(session, suggestion_id)
    if not raw_suggestion:
        i18n_kwargs = {"suggestion_id": suggestion_id}
        payload = MessagePayload(i18n_key="error_suggestion_not_found", i18n_kwargs=i18n_kwargs)
        return await notifier.notify_user(user_dto, payload=payload)

    suggestion, media_group = raw_suggestion

    i18n_kwargs = {
        "author_username": html.bold(suggestion.author.username),
        "author_id": suggestion.author_id,
        "suggestion_id": suggestion.id,
        "original_caption": suggestion.caption,
    }

    translated = notifier.get_translated_text("admin_get_suggestion_caption")
    media_group.caption = notifier.get_formatted_text(translated, i18n_kwargs)

    payload = MessagePayload(content=media_group.build())
    await notifier.notify_user(user_dto, payload=payload)


@router.message(F.text.lower() == "смотреть предложку")
async def show_suggestions_admin_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_dto: UserDTO,
    bot: Bot,
    notifier: Notifier,
):
    raw_suggestion = await get_active_suggestion(session)

    if not raw_suggestion:
        kb = get_main_kb_by_role(user_dto.role)
        payload = MessagePayload(i18n_key="no_active_suggestions", reply_markup=kb)
        return await notifier.notify_user(user_dto, payload=payload)

    payload = MessagePayload(i18n_key="start_review_suggestions", reply_markup=accept_decline_kb)
    await notifier.notify_user(user_dto, payload=payload)

    await state.set_state(SuggestionViewer.in_viewer)

    suggestion, media_group = raw_suggestion
    suggestions_left = await SuggestionDAO.get_active_count(session)

    await update_review_state(suggestion, media_group, user_dto, notifier, state, suggestions_left)


@router.message(
    SuggestionViewer.in_viewer, (F.text.lower() == "принять") | (F.text.lower() == "отклонить")
)
async def accept_deny_suggestion(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    user_dto: UserDTO,
    config: Config,
    notifier: Notifier,
    with_caption: bool = True,
    is_accepted: bool = False,
):
    text = message.text.lower()
    is_accepted = text == "принять" or is_accepted

    data = await state.get_data()
    cur_suggestion_id: int = data["last"]

    async with session.begin():
        cur_suggestion = await SuggestionDAO.get_one_or_none_by_id(
            session, cur_suggestion_id, solo=True
        )

        # Запостить (если принято) и обновить в базе.
        if cur_suggestion.accepted is None:
            if is_accepted:
                cur_media_group: MediaGroupBuilder = data["media_group"]
                await post_in_channel(
                    bot, cur_media_group, cur_suggestion, config.CHANNEL_ID, with_caption
                )

            cur_suggestion.accepted = is_accepted

    # Получаем новый (следующий) suggestion
    return await go_next_suggestion(session, state, user_dto, data, notifier)


@router.message(SuggestionViewer.in_viewer, F.text.lower() == "бан")
async def ban_suggestion_author(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_dto: UserDTO,
    config: Config,
    notifier: Notifier,
):
    data = await state.get_data()
    cur_suggestion: Suggestion = data["suggestion"]

    async with session.begin():
        target_id = cur_suggestion.author_id
        if not await ban_user(session, target_id, config):
            payload = MessagePayload(i18n_key="error_user_immune")
            return await notifier.notify_user(user_dto, payload=payload)

    # Получаем новый (следующий) suggestion
    return await go_next_suggestion(session, state, user_dto, data, notifier)


@router.message(SuggestionViewer.in_viewer, (F.text.lower() == "принять без подписи"))
async def accept_wo_caption(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    user_dto: UserDTO,
    config: Config,
    notifier: Notifier,
):
    await accept_deny_suggestion(
        message, session, state, bot, user_dto, config, notifier, False, True
    )
