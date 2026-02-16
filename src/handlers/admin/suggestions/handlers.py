from logging import getLogger

from aiogram import Bot, F, Router, html
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.media_group import MediaGroupBuilder
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import SuggestionDAO
from database.dto import SuggestionBaseDTO, SuggestionFullDTO, UserDTO
from handlers.keyboards import get_main_kb_by_role, get_accept_decline_kb
from helpers.message_payload import MessagePayload
from helpers.schemas import ChangeRoleCommand, IDCommand
from helpers.utils import ban_user
from services.notifier import Notifier

from aiogram.utils.i18n import lazy_gettext as __
from .filters import ViewerActionFilter

from .logics import (
    get_active_suggestion,
    get_media_group,
    go_next_suggestion,
    post_in_channel,
    update_review_state,
)
from .state import SuggestionViewer

VIEWER_ACTION_FILTER = ViewerActionFilter()
VIEWER_BAN_FILTER = F.text.lower() == __("command_ban_filter")

router = Router(name="admin_suggestions")
logger = getLogger()


@router.message(Command("get_suggestion", prefix="/!"))
async def get_suggestion_solo_view(
    message: Message,
    session: AsyncSession,
    command: CommandObject,
    user_dto: UserDTO,
    notifier: Notifier,
    state: FSMContext,
):
    try:
        cmd_data = IDCommand(target_id=command.args)
        async with session.begin():
            suggestion = await SuggestionDAO.get_one_or_none_by_id(session, cmd_data.target_id)
            suggestion_dto = SuggestionFullDTO.model_validate(suggestion)
    except (ValueError, ValidationError) as e:
        logger.error(e)
        i18n_kwargs = {"suggestion_id": command.args}
        payload = MessagePayload(i18n_key="error_suggestion_not_found", i18n_kwargs=i18n_kwargs)
        return await notifier.notify_user(user_dto, payload=payload)

    media_group = get_media_group(suggestion_dto.media, suggestion_dto.caption)

    i18n_kwargs = {
        "author_username": html.bold(suggestion_dto.author.username),
        "author_id": suggestion_dto.author_id,
        "suggestion_id": suggestion_dto.id,
        "original_caption": suggestion_dto.caption,
        "verdict": suggestion.accepted,
    }

    translated = notifier.get_translated_text("admin_get_suggestion_caption")
    media_group.caption = notifier.get_formatted_text(translated, i18n_kwargs)

    await state.set_state(SuggestionViewer.in_solo_view)
    await state.set_data(
        {
            "suggestion_dto": suggestion_dto,  # FULL DTO
            "media_group": media_group,
        }
    )

    payload = MessagePayload(content=media_group.build())
    await notifier.notify_user(user_dto, payload)

    payload = MessagePayload(i18n_key="send_verdict", reply_markup=get_accept_decline_kb())
    await notifier.notify_user(user_dto, payload)


@router.message(
    SuggestionViewer.in_solo_view,
    VIEWER_ACTION_FILTER,
)
async def verdict_solo_view(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_dto: UserDTO,
    notifier: Notifier,
    bot: Bot,
    config: Config,
    viewer_action: str,
):
    print(viewer_action)
    data = await state.get_data()
    suggestion_dto: SuggestionFullDTO = data.get("suggestion_dto")

    verdict = viewer_action == "accept" or viewer_action == "accept_no_caption"
    async with session.begin():
        data_orm = {"accepted": verdict}
        await SuggestionDAO.update_by_id(session, suggestion_dto.id, data_orm)

    if verdict:
        with_og_caption = viewer_action != "accept_no_caption"
        media_group = data.get("media_group")
        await post_in_channel(bot, media_group, suggestion_dto, config.CHANNEL_ID, with_og_caption)

    kb = get_main_kb_by_role(user_dto.role)
    payload = MessagePayload(i18n_key="verdict_rewrite", reply_markup=kb)
    await notifier.notify_user(user_dto, payload)
    await state.clear()


@router.message(F.text == __("enter_viewer_command"))
async def show_suggestions_admin_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_dto: UserDTO,
    notifier: Notifier,
):
    raw_suggestion = await get_active_suggestion(session)

    if not raw_suggestion:
        kb = get_main_kb_by_role(user_dto.role)
        payload = MessagePayload(i18n_key="no_active_suggestions", reply_markup=kb)
        return await notifier.notify_user(user_dto, payload=payload)

    payload = MessagePayload(i18n_key="start_review_suggestions", reply_markup=get_accept_decline_kb())
    await notifier.notify_user(user_dto, payload=payload)

    await state.set_state(SuggestionViewer.in_viewer)

    suggestion, media_group = raw_suggestion
    suggestions_left = await SuggestionDAO.get_active_count(session)

    await update_review_state(suggestion, media_group, user_dto, notifier, state, suggestions_left)


@router.message(
    SuggestionViewer.in_viewer,
    VIEWER_ACTION_FILTER,
)
async def accept_deny_suggestion(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    user_dto: UserDTO,
    config: Config,
    notifier: Notifier,
    viewer_action: str,
):
    verdict = viewer_action == "accept" or viewer_action == "accept_no_caption"

    data = await state.get_data()
    suggestion_id: int = data["last"]

    async with session.begin():
        suggestion = await SuggestionDAO.get_one_or_none_by_id(session, suggestion_id, solo=True)
        suggestion_dto = SuggestionBaseDTO.model_validate(suggestion)

    # go next если уже вердикт вынесен
    if suggestion_dto.accepted is not None:
        i18n_kwargs = {
            "id": html.bold(f"{suggestion_dto.id}"),
            "verdict": html.bold(f"{suggestion_dto.accepted}"),
        }
        payload = MessagePayload(i18n_key="suggestion_verdict_exists", i18n_kwargs=i18n_kwargs)
        await notifier.notify_user(user_dto, payload)
        return await go_next_suggestion(session, state, user_dto, data, notifier)

    # Запостить (если принято) и обновить в базе.
    if verdict:
        media_group: MediaGroupBuilder = data["media_group"]
        with_caption = viewer_action != "accept_no_caption"
        await post_in_channel(bot, media_group, suggestion_dto, config.CHANNEL_ID, with_caption)

    async with session.begin():
        data_orm = {"accepted": verdict}
        await SuggestionDAO.update_by_id(session, suggestion_dto.id, data_orm)

    # Получаем новый (следующий) suggestion
    return await go_next_suggestion(session, state, user_dto, data, notifier)


@router.message(SuggestionViewer.in_solo_view, VIEWER_BAN_FILTER)
@router.message(SuggestionViewer.in_viewer, VIEWER_BAN_FILTER)
async def ban_suggestion_author(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_dto: UserDTO,
    config: Config,
    notifier: Notifier,
):
    data = await state.get_data()
    cur_suggestion: SuggestionBaseDTO = data.get("suggestion") or data.get("suggestion_dto")

    target_id = cur_suggestion.author_id

    try:
        cmd_data = ChangeRoleCommand(
            target_id=target_id,
            target_role="BANNED",
            caller_dto=user_dto,
            notifier=notifier,
            bot_owner_id=config.ADMIN_ID,
        )
        if await ban_user(session, cmd_data, notify_user=False) is False:
            return

    except (ValueError, ValidationError):
        payload = MessagePayload(
            i18n_key="command_syntax_error",
            i18n_kwargs={"hint": html.code("Validation Error.")},
        )
        return await notifier.notify_user(user_dto, payload)

    # Получаем новый (следующий) suggestion
    current_state = await state.get_state()
    if current_state != "SuggestionViewer:in_solo_view":
        await go_next_suggestion(session, state, user_dto, data, notifier)
