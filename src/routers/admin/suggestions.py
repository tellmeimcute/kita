
import asyncio
from logging import getLogger

from aiogram import Router, html
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from dishka import FromDishka

from di.suggestion_viewer import viewer_factory_t

from database.dto import SuggestionFullDTO, UserDTO
from database.roles import UserRole
from routers.state import SuggestionViewerState
from helpers.filters import I18nTextFilter, TextArgsFilter
from helpers.schemas.message_payload import MessagePayload

from helpers.schemas import IDCommand
from helpers.schemas.data import SuggestionViewerData

from helpers.suggestion_viewer import SuggestionViewer
from services import NotifierService, SuggestionService, UserService

router = Router(name="admin_suggestions")
logger = getLogger("kita.admin_suggestions")


@router.message(TextArgsFilter("command_open_solo_view", IDCommand))
async def solo_suggestion(
    message: Message,
    user_dto: UserDTO,
    suggestion_service: FromDishka[SuggestionService],
    viewer_factory: FromDishka[viewer_factory_t],
    state: FSMContext,
    command: IDCommand,
):
    suggestion_dto = await suggestion_service.get(command.target_id)

    await state.set_state(SuggestionViewerState.in_solo_view)

    viewer_data = SuggestionViewerData(user_dto=user_dto, suggestion_dto=suggestion_dto)
    viewer = viewer_factory(viewer_data)

    await viewer.render_suggestion()
    await viewer.dump_into_state(state, viewer.data)
    await viewer.render_wait_verdict()


@router.message(SuggestionViewerState.in_solo_view, I18nTextFilter("viewer_accept", verdict=True))
@router.message(SuggestionViewerState.in_solo_view, I18nTextFilter("viewer_decline", verdict=False))
async def solo_suggestion_verdict(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    suggestion_service: FromDishka[SuggestionService],
    viewer: FromDishka[SuggestionViewer],
    verdict: bool,
):
    suggestion_dto: SuggestionFullDTO = viewer.data.suggestion_dto

    suggestion_dto.accepted = verdict
    async with session.begin():
        await suggestion_service.update(suggestion_dto)

    await viewer.render_verdict_rewrite()
    await state.clear()

    if suggestion_dto.accepted:
        tasks = [viewer.post_channel(suggestion_dto), viewer.notify_author(suggestion_dto)]
        asyncio.gather(*tasks)


@router.message(I18nTextFilter("command_enter_viewer"))
async def enter_suggestion_viewer(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    viewer_factory: FromDishka[viewer_factory_t],
):
    await state.set_state(SuggestionViewerState.in_viewer)

    viewer_data = SuggestionViewerData(user_dto=user_dto)
    viewer = viewer_factory(viewer_data)

    if await viewer.to_next_suggestion(state):
        await viewer.render_start_review()
        return await viewer.render_suggestion()

    await state.clear()
    await viewer.render_empty_queue()

@router.message(SuggestionViewerState.in_viewer, I18nTextFilter("viewer_accept", verdict=True))
@router.message(SuggestionViewerState.in_viewer, I18nTextFilter("viewer_decline", verdict=False))
async def viewer_apply_verdict(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    suggestion_service: FromDishka[SuggestionService],
    viewer: FromDishka[SuggestionViewer],
    verdict: bool,
):
    suggestion_dto = await viewer.get_updated_dto()
    
    if suggestion_dto.accepted is not None:
        await viewer.render_verdict_exists()
        return await viewer.go_next_suggestion(state)

    suggestion_dto.accepted = verdict
    async with session.begin():
        await suggestion_service.update(suggestion_dto)

    await viewer.go_next_suggestion(state)

    if suggestion_dto.accepted:
        tasks = [viewer.post_channel(suggestion_dto), viewer.notify_author(suggestion_dto)]
        asyncio.gather(*tasks)


VIEWER_BAN_FILTER = I18nTextFilter("command_ban_filter")


@router.message(SuggestionViewerState.in_solo_view, VIEWER_BAN_FILTER)
@router.message(SuggestionViewerState.in_viewer, VIEWER_BAN_FILTER)
async def ban_suggestion_author(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_dto: UserDTO,
    user_service: UserService,
    notifier: FromDishka[NotifierService],
    viewer: FromDishka[SuggestionViewer],
):
    try:
        target_id = viewer.data.suggestion_dto.author_id
        target_role = UserRole.BANNED

        async with session.begin():
            target_dto = await user_service.moderate_user(
                target_id, target_role, caller=user_dto
            )

        payload = MessagePayload(
            i18n_key="answer_admin_role_changed",
            i18n_kwargs=target_dto.model_dump(),
        )
        await notifier.notify_user(user_dto, payload)
    except (ValueError, ValidationError):
        payload = MessagePayload(
            i18n_key="command_syntax_error",
            i18n_kwargs={"hint": html.code("Validation Error.")},
        )
        return await notifier.notify_user(user_dto, payload)

    current_state = await state.get_state()
    if current_state != "SuggestionViewerState:in_solo_view":
        await viewer.go_next_suggestion(state)
