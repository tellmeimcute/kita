


from logging import getLogger

from aiogram import Router, html
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import SuggestionDAO
from database.dto import SuggestionFullDTO, UserDTO
from handlers.keyboards import ReplyKeyboard
from helpers.filters import I18nTextFilter, TextArgsFilter
from helpers.message_payload import MessagePayload
from helpers.schemas import ChangeRoleData, IDCommand, SuggestionViewerData

from services.user import UserService
from services.notifier import NotifierService
from services.suggestion import SuggestionService

from .filters import viewer_action
from .logics import SuggestionViewerRenderer
from .state import SuggestionViewerState

router = Router(name="admin_suggestions")
logger = getLogger("kita.admin_suggestions")


@router.message(TextArgsFilter("command_open_solo_view", IDCommand))
async def get_suggestion_solo_view(
    message: Message,
    session: AsyncSession,
    user_dto: UserDTO,
    notifier: NotifierService,
    state: FSMContext,
    config: Config,
    command: IDCommand,
):
    suggestion_service = SuggestionService(session, config)

    try:
        suggestion_dto = await suggestion_service.get(command.target_id, solo=False)
    except (ValueError, ValidationError):
        i18n_kwargs = {"suggestion_id": command.target_id}
        payload = MessagePayload(i18n_key="error_suggestion_not_found", i18n_kwargs=i18n_kwargs)
        return await notifier.notify_user(user_dto, payload=payload)

    await state.set_state(SuggestionViewerState.in_solo_view)

    viewer_data = SuggestionViewerData(
        suggestion_dto=suggestion_dto, 
        user_dto=user_dto,
    )
    viewer = SuggestionViewerRenderer(notifier, viewer_data, config)

    await viewer.render_suggestion()
    await viewer.update_state_data(state, viewer.data)
    await viewer.render_send_verdict()


@router.message(SuggestionViewerState.in_solo_view, viewer_action("viewer_accept"))
@router.message(SuggestionViewerState.in_solo_view, viewer_action("viewer_accept_no_caption"))
@router.message(SuggestionViewerState.in_solo_view, viewer_action("viewer_decline"))
async def verdict_solo_view(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    notifier: NotifierService,
    config: Config,
    viewer_action: str,
    verdict: bool,
):
    suggestion_service = SuggestionService(session, config)

    data = await state.get_data()
    viewer_data: SuggestionViewerData = data.get("viewer_data")
    suggestion_dto: SuggestionFullDTO = viewer_data.suggestion_dto

    viewer = SuggestionViewerRenderer.from_data(notifier, viewer_data, config)

    if verdict:
        status = await viewer.post_in_channel(viewer_action)
        if not status:
            return
        await viewer.notify_author(status)
    
    suggestion_dto.accepted = verdict
    await suggestion_service.update(suggestion_dto)

    await viewer.render_verdict_rewrite()
    await state.clear()


@router.message(I18nTextFilter("command_enter_viewer"))
async def show_suggestions_admin_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_dto: UserDTO,
    notifier: NotifierService,
    config: Config,
):
    suggestion_orm = await SuggestionDAO.get_active(session)

    if not suggestion_orm:
        payload = MessagePayload(i18n_key="no_active_suggestions", reply_markup=ReplyKeyboard.main(user_dto))
        return await notifier.notify_user(user_dto, payload=payload)

    await state.set_state(SuggestionViewerState.in_viewer)

    suggestion_dto = SuggestionFullDTO.model_validate(suggestion_orm)
    viewer_data = SuggestionViewerData(
        suggestion_dto=suggestion_dto,
        user_dto=user_dto,
    )
    viewer = SuggestionViewerRenderer(notifier, viewer_data, config)

    await viewer.render_send_verdict(i18n_key="start_review_suggestions")
    await viewer.render_suggestion()
    await viewer.update_state_data(state, viewer.data)


@router.message(SuggestionViewerState.in_viewer, viewer_action("viewer_accept"))
@router.message(SuggestionViewerState.in_viewer, viewer_action("viewer_accept_no_caption"))
@router.message(SuggestionViewerState.in_viewer, viewer_action("viewer_decline"))
async def accept_deny_suggestion(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    notifier: NotifierService,
    config: Config,
    viewer_action: str,
    verdict: bool,
):
    suggestion_service = SuggestionService(session, config)

    data = await state.get_data()
    viewer_data: SuggestionViewerData = data.get("viewer_data")
    suggestion_dto: SuggestionFullDTO = viewer_data.suggestion_dto

    viewer: SuggestionViewerRenderer = SuggestionViewerRenderer.from_data(notifier, viewer_data, config)

    updated_dto = await suggestion_service.get(suggestion_dto.id, solo=True)
    suggestion_dto = suggestion_dto.model_copy(update={"accepted": updated_dto.accepted})
    viewer.data = viewer.data.model_copy(update={"suggestion_dto": suggestion_dto})

    if suggestion_dto.accepted is not None:
        await viewer.render_verdict_exists()
        return await viewer.go_next(session, state)

    if verdict:
        status = await viewer.post_in_channel(viewer_action)
        if not status:
            return
        await viewer.notify_author(status)

    suggestion_dto.accepted = verdict
    await suggestion_service.update(suggestion_dto)

    return await viewer.go_next(session, state)


VIEWER_BAN_FILTER = I18nTextFilter("command_ban_filter")
@router.message(SuggestionViewerState.in_solo_view, VIEWER_BAN_FILTER)
@router.message(SuggestionViewerState.in_viewer, VIEWER_BAN_FILTER)
async def ban_suggestion_author(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_dto: UserDTO,
    notifier: NotifierService,
    user_service: UserService,
    config: Config,
):
    data = await state.get_data()

    viewer_data: SuggestionViewerData = data.get("viewer_data")
    suggestion_dto: SuggestionFullDTO = viewer_data.suggestion_dto

    viewer: SuggestionViewerRenderer = SuggestionViewerRenderer.from_data(notifier, viewer_data, config)

    try:
        cmd_data = ChangeRoleData(
            target_id=suggestion_dto.author_id,
            target_role="BANNED",
            caller_dto=user_dto,
            notifier=notifier,
        )
        await user_service.change_role(cmd_data, notify_user=False)
    except (ValueError, ValidationError):
        payload = MessagePayload(
            i18n_key="command_syntax_error",
            i18n_kwargs={"hint": html.code("Validation Error.")},
        )
        return await notifier.notify_user(user_dto, payload)

    # Получаем новый (следующий) suggestion
    current_state = await state.get_state()
    if current_state != "SuggestionViewerState:in_solo_view":
        await viewer.go_next(session, state)
