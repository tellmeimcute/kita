from logging import getLogger

from aiogram import Router, html
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dto import SuggestionFullDTO, UserDTO
from handlers.state import SuggestionViewerState
from helpers.filters import I18nTextFilter, TextArgsFilter
from helpers.message_payload import MessagePayload
from helpers.schemas import ChangeRoleData, IDCommand, SuggestionViewerData
from helpers.suggestion_viewer import SuggestionViewer
from services import NotifierService, SuggestionService, UserService

router = Router(name="admin_suggestions")
logger = getLogger("kita.admin_suggestions")


@router.message(TextArgsFilter("command_open_solo_view", IDCommand))
async def solo_suggestion(
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
        suggestion_dto = await suggestion_service.get(command.target_id)
    except (ValueError, ValidationError):
        i18n_kwargs = {"suggestion_id": command.target_id}
        payload = MessagePayload(i18n_key="error_suggestion_not_found", i18n_kwargs=i18n_kwargs)
        return await notifier.notify_user(user_dto, payload=payload)

    await state.set_state(SuggestionViewerState.in_solo_view)

    viewer_data = SuggestionViewerData(user_dto=user_dto, suggestion_dto=suggestion_dto)
    viewer = SuggestionViewer(viewer_data, suggestion_service, notifier, config)

    await viewer.render_suggestion()
    await viewer.dump_into_state(state, viewer.data)
    await viewer.render_wait_verdict()


@router.message(SuggestionViewerState.in_solo_view, I18nTextFilter("viewer_accept", verdict=True))
@router.message(
    SuggestionViewerState.in_solo_view, I18nTextFilter("viewer_decline", verdict=False)
)
async def solo_suggestion_verdict(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    notifier: NotifierService,
    config: Config,
    verdict: bool,
):
    suggestion_service = SuggestionService(session, config)

    data = await state.get_data()
    viewer_data = SuggestionViewerData.model_validate(data.get("viewer_data"))
    suggestion_dto: SuggestionFullDTO = viewer_data.suggestion_dto

    viewer = SuggestionViewer(viewer_data, suggestion_service, notifier, config)

    viewer.utils.update_status(suggestion_dto, verdict)
    await suggestion_service.update(suggestion_dto)

    if suggestion_dto.accepted:
        await viewer.post_channel()
        await viewer.notify_author()

    await viewer.render_verdict_rewrite()
    await state.clear()


@router.message(I18nTextFilter("command_enter_viewer"))
async def enter_suggestion_viewer(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_dto: UserDTO,
    notifier: NotifierService,
    config: Config,
):
    suggestion_service = SuggestionService(session, config)
    await state.set_state(SuggestionViewerState.in_viewer)

    viewer_data = SuggestionViewerData(user_dto=user_dto)
    viewer = SuggestionViewer(viewer_data, suggestion_service, notifier, config)

    await viewer.render_start_review()
    await viewer.go_next_suggestion(state)


@router.message(SuggestionViewerState.in_viewer, I18nTextFilter("viewer_accept", verdict=True))
@router.message(SuggestionViewerState.in_viewer, I18nTextFilter("viewer_decline", verdict=False))
async def viewer_apply_verdict(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    notifier: NotifierService,
    config: Config,
    verdict: bool,
):
    suggestion_service = SuggestionService(session, config)

    viewer = await SuggestionViewer.from_state(state, suggestion_service, notifier, config)
    suggestion_dto = await viewer.get_updated_dto()

    if suggestion_dto.accepted is not None:
        await viewer.render_verdict_exists()
        return await viewer.go_next_suggestion(state)

    viewer.utils.update_status(suggestion_dto, verdict)
    await suggestion_service.update(suggestion_dto)

    if suggestion_dto.accepted:
        await viewer.post_channel()
        await viewer.notify_author()

    await viewer.go_next_suggestion(state)


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
    suggestion_service = SuggestionService(session, config)
    viewer = await SuggestionViewer.from_state(state, suggestion_service, notifier, config)

    try:
        cmd_data = ChangeRoleData(
            target_id=viewer.data.suggestion_dto.author_id,
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

    current_state = await state.get_state()
    if current_state != "SuggestionViewerState:in_solo_view":
        await viewer.render_suggestion()
