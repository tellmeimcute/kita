
import asyncio
from logging import getLogger

from aiogram import Router, html
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from dishka import FromDishka

from config import Config, RuntimeConfig
from database.dto import SuggestionFullDTO, UserDTO
from database.roles import UserRole
from routers.state import SuggestionViewerState
from helpers.filters import I18nTextFilter, TextArgsFilter
from helpers.schemas.message_payload import MessagePayload

from helpers.schemas import IDCommand
from helpers.schemas.data import SuggestionViewerData

from helpers.suggestion_viewer import SuggestionViewer
from helpers.exceptions import UserImmuneError, SQLModelNotFoundError
from services import NotifierService, SuggestionService, UserService

router = Router(name="admin_suggestions")
logger = getLogger("kita.admin_suggestions")


@router.message(TextArgsFilter("command_open_solo_view", IDCommand))
async def solo_suggestion(
    message: Message,
    session: AsyncSession,
    user_dto: UserDTO,
    notifier: FromDishka[NotifierService],
    suggestion_service: FromDishka[SuggestionService],
    state: FSMContext,
    config: FromDishka[Config],
    runtime_config: FromDishka[RuntimeConfig],
    command: IDCommand,
):
    try:
        async with session.begin():
            suggestion_dto = await suggestion_service.get(command.target_id)
    except (SQLModelNotFoundError, ValidationError):
        i18n_kwargs = {"suggestion_id": command.target_id}
        payload = MessagePayload(i18n_key="error_suggestion_not_found", i18n_kwargs=i18n_kwargs)
        return await notifier.notify_user(user_dto, payload=payload)

    await state.set_state(SuggestionViewerState.in_solo_view)

    viewer_data = SuggestionViewerData(user_dto=user_dto, suggestion_dto=suggestion_dto)
    viewer = SuggestionViewer(
        viewer_data,
        session,
        suggestion_service,
        notifier,
        config,
        runtime_config,
    )

    await viewer.render_suggestion()
    await viewer.dump_into_state(state, viewer.data)
    await viewer.render_wait_verdict()


@router.message(SuggestionViewerState.in_solo_view, I18nTextFilter("viewer_accept", verdict=True))
@router.message(SuggestionViewerState.in_solo_view, I18nTextFilter("viewer_decline", verdict=False))
async def solo_suggestion_verdict(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    notifier: FromDishka[NotifierService],
    suggestion_service: FromDishka[SuggestionService],
    config: FromDishka[Config],
    runtime_config: FromDishka[RuntimeConfig],
    verdict: bool,
):

    data = await state.get_data()
    viewer_data = SuggestionViewerData.model_validate(data.get("viewer_data"))
    suggestion_dto: SuggestionFullDTO = viewer_data.suggestion_dto

    viewer = SuggestionViewer(
        viewer_data,
        session,
        suggestion_service,
        notifier,
        config,
        runtime_config,
    )

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
    session: AsyncSession,
    state: FSMContext,
    user_dto: UserDTO,
    notifier: FromDishka[NotifierService],
    suggestion_service: FromDishka[SuggestionService],
    config: FromDishka[Config],
    runtime_config: FromDishka[RuntimeConfig],
):
    await state.set_state(SuggestionViewerState.in_viewer)

    viewer_data = SuggestionViewerData(user_dto=user_dto)
    viewer = SuggestionViewer(viewer_data, session, suggestion_service, notifier, config, runtime_config)

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
    notifier: FromDishka[NotifierService],
    suggestion_service: FromDishka[SuggestionService],
    config: FromDishka[Config],
    runtime_config: FromDishka[RuntimeConfig],
    verdict: bool,
):
    viewer = await SuggestionViewer.from_state(state, session, suggestion_service, notifier, config, runtime_config)
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
    suggestion_service: FromDishka[SuggestionService],
    config: FromDishka[Config],
    runtime_config: FromDishka[RuntimeConfig],
):
    viewer = await SuggestionViewer.from_state(state, session, suggestion_service, notifier, config, runtime_config)

    try:
        if viewer.data.suggestion_dto.author_id == user_dto.user_id:
            raise UserImmuneError()
        async with session.begin():
            target_dto = await user_service.get(viewer.data.suggestion_dto.author_id)
            await user_service.set_role(target_dto, UserRole.BANNED)
            await user_service.decline_suggestion(target_dto)
    except (ValueError, ValidationError):
        payload = MessagePayload(
            i18n_key="command_syntax_error",
            i18n_kwargs={"hint": html.code("Validation Error.")},
        )
        return await notifier.notify_user(user_dto, payload)
    except UserImmuneError:
        payload = MessagePayload(i18n_key="error_user_immune")
        return await notifier.notify_user(user_dto, payload)
    except SQLModelNotFoundError:
        i18n_kwargs = {"user_id": viewer.data.suggestion_dto.author_id}
        payload = MessagePayload(i18n_key="user_not_found", i18n_kwargs=i18n_kwargs)
        return await notifier.notify_user(user_dto, payload)

    payload = MessagePayload(
        i18n_key="answer_admin_role_changed",
        i18n_kwargs=target_dto.model_dump(),
    )
    await notifier.notify_user(user_dto, payload)

    current_state = await state.get_state()
    if current_state != "SuggestionViewerState:in_solo_view":
        await viewer.go_next_suggestion(state)
