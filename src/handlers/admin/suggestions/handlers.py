


from logging import getLogger

from aiogram import Router, html
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import SuggestionDAO
from database.dto import SuggestionBaseDTO, SuggestionFullDTO, UserDTO
from handlers.keyboards import get_main_kb_by_role
from helpers.filters import I18nTextFilter, TextArgsFilter
from helpers.message_payload import MessagePayload
from helpers.schemas import ChangeRoleData, IDCommand, SuggestionViewerData
from helpers.utils import ban_user
from services.notifier import Notifier

from .filters import viewer_action
from .logics import SuggestionViewerRenderer
from .state import SuggestionViewerState

router = Router(name="admin_suggestions")
logger = getLogger()


@router.message(TextArgsFilter("command_open_solo_view", IDCommand))
async def get_suggestion_solo_view(
    message: Message,
    session: AsyncSession,
    user_dto: UserDTO,
    notifier: Notifier,
    state: FSMContext,
    config: Config,
    command: IDCommand,
):
    try:
        async with session.begin():
            suggestion = await SuggestionDAO.get_one_or_none_by_id(session, command.target_id)
            suggestion_dto = SuggestionFullDTO.model_validate(suggestion)
    except (ValueError, ValidationError) as e:
        i18n_kwargs = {"suggestion_id": command.target_id}
        payload = MessagePayload(i18n_key="error_suggestion_not_found", i18n_kwargs=i18n_kwargs)
        return await notifier.notify_user(user_dto, payload=payload)

    await state.set_state(SuggestionViewerState.in_solo_view)

    viewer_data = SuggestionViewerData(
        suggestion_dto=suggestion_dto, 
        user_dto=user_dto,
        channel_id=config.CHANNEL_ID
    )
    viewer = SuggestionViewerRenderer(notifier, viewer_data)

    await viewer.render_suggestion()
    await viewer.update_state_data(state)
    await viewer.render_send_verdict()


@router.message(SuggestionViewerState.in_solo_view, viewer_action("viewer_accept"))
@router.message(SuggestionViewerState.in_solo_view, viewer_action("viewer_accept_no_caption"))
@router.message(SuggestionViewerState.in_solo_view, viewer_action("viewer_decline"))
async def verdict_solo_view(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    notifier: Notifier,
    viewer_action: str,
    verdict: bool,
):
    data = await state.get_data()
    viewer_data: SuggestionViewerData = data.get("viewer_data")
    suggestion_dto: SuggestionFullDTO = viewer_data.suggestion_dto

    viewer: SuggestionViewerRenderer  = await SuggestionViewerRenderer.from_data(notifier, viewer_data)

    if verdict:
        status = await viewer.post_in_channel(viewer_action)
        if not status:
            return
        
        await viewer.notify_author(status)
        
    async with session.begin():
        data_orm = {"accepted": verdict}
        await SuggestionDAO.update_by_id(session, suggestion_dto.id, data_orm)

    await viewer.render_verdict_rewrite()
    await state.clear()


@router.message(I18nTextFilter("command_enter_viewer"))
async def show_suggestions_admin_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_dto: UserDTO,
    notifier: Notifier,
    config: Config,
):
    suggestion_orm = await SuggestionDAO.get_active(session)

    if not suggestion_orm:
        kb = get_main_kb_by_role(user_dto.role)
        payload = MessagePayload(i18n_key="no_active_suggestions", reply_markup=kb)
        return await notifier.notify_user(user_dto, payload=payload)

    await state.set_state(SuggestionViewerState.in_viewer)

    suggestion_dto = SuggestionFullDTO.model_validate(suggestion_orm)
    viewer_data = SuggestionViewerData(
        suggestion_dto=suggestion_dto, 
        user_dto=user_dto,
        channel_id=config.CHANNEL_ID
    )
    viewer = SuggestionViewerRenderer(notifier, viewer_data)

    await viewer.render_send_verdict(i18n_key="start_review_suggestions")
    await viewer.render_suggestion()
    await viewer.update_state_data(state)


@router.message(SuggestionViewerState.in_viewer, viewer_action("viewer_accept"))
@router.message(SuggestionViewerState.in_viewer, viewer_action("viewer_accept_no_caption"))
@router.message(SuggestionViewerState.in_viewer, viewer_action("viewer_decline"))
async def accept_deny_suggestion(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    notifier: Notifier,
    viewer_action: str,
    verdict: bool,
):
    data = await state.get_data()

    viewer_data: SuggestionViewerData = data.get("viewer_data")
    suggestion_dto: SuggestionFullDTO = viewer_data.suggestion_dto

    viewer: SuggestionViewerRenderer  = await SuggestionViewerRenderer.from_data(notifier, viewer_data)

    async with session.begin():
        suggestion = await SuggestionDAO.get_one_or_none_by_id(session, suggestion_dto.id, solo=True)
        updated_dto = SuggestionBaseDTO.model_validate(suggestion)
        
        suggestion_dto.accepted = updated_dto.accepted
        viewer.data.suggestion_dto = suggestion_dto

    if suggestion_dto.accepted is not None:
        await viewer.render_verdict_exists()
        return await viewer.go_next(session, state)

    if verdict:
        status = await viewer.post_in_channel(viewer_action)
        if not status:
            return
        await viewer.notify_author(status)

    async with session.begin():
        data_orm = {"accepted": verdict}
        await SuggestionDAO.update_by_id(session, suggestion_dto.id, data_orm)

    return await viewer.go_next(session, state)


VIEWER_BAN_FILTER = I18nTextFilter("command_ban_filter")
@router.message(SuggestionViewerState.in_solo_view, VIEWER_BAN_FILTER)
@router.message(SuggestionViewerState.in_viewer, VIEWER_BAN_FILTER)
async def ban_suggestion_author(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_dto: UserDTO,
    config: Config,
    notifier: Notifier,
):
    data = await state.get_data()

    viewer_data: SuggestionViewerData = data.get("viewer_data")
    suggestion_dto: SuggestionFullDTO = viewer_data.suggestion_dto

    viewer: SuggestionViewerRenderer  = await SuggestionViewerRenderer.from_data(notifier, viewer_data)

    try:
        cmd_data = ChangeRoleData(
            target_id=suggestion_dto.author_id,
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
        await viewer.go_next(session, state)
