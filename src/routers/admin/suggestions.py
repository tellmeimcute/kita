
from logging import getLogger

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from dishka import FromDishka

from database.dto import SuggestionFullDTO, UserDTO
from database.roles import UserRole
from routers.state import SuggestionViewerState
from helpers.filters import I18nTextFilter, TextArgsFilter
from helpers.schemas.message_payload import MessagePayload

from helpers.schemas import IDCommand
from helpers.schemas.data import SuggestionViewerData

from services import NotifierService, SuggestionService, UserService

from services.suggestion_moderation import SuggestionModerationService
from helpers.suggestion_queue import SuggestionQueueManager
from ui.keyboards import ReplyKeyboard
from ui.suggestion_renderer import SuggestionRenderer


router = Router(name="admin_suggestions")
logger = getLogger("kita.admin_suggestions")


@router.message(TextArgsFilter("command_open_solo_view", IDCommand))
async def solo_suggestion(
    message: Message,
    session: AsyncSession,
    user_dto: UserDTO,
    suggestion_service: FromDishka[SuggestionService],
    renderer: FromDishka[SuggestionRenderer],
    state: FSMContext,
    command: IDCommand,
):
    suggestion_dto = await suggestion_service.get(command.target_id)

    await state.set_state(SuggestionViewerState.in_solo_view)

    viewer_data = SuggestionViewerData(user_dto=user_dto, suggestion_dto=suggestion_dto)
    queue_manager = SuggestionQueueManager(session, suggestion_service, state, viewer_data)

    await renderer.suggestion(user_dto, suggestion_dto)
    await queue_manager.dump_into_state()
    await renderer.wait_verdict(user_dto)


@router.message(SuggestionViewerState.in_solo_view, I18nTextFilter("viewer_accept", verdict=True))
@router.message(SuggestionViewerState.in_solo_view, I18nTextFilter("viewer_decline", verdict=False))
async def solo_suggestion_verdict(
    message: Message,
    user_dto: UserDTO,
    session: AsyncSession,
    state: FSMContext,
    suggestion_service: FromDishka[SuggestionService],
    renderer: FromDishka[SuggestionRenderer],
    queue_manager: FromDishka[SuggestionQueueManager],
    moderation: FromDishka[SuggestionModerationService],
    verdict: bool,
):
    suggestion_dto: SuggestionFullDTO = queue_manager.data.suggestion_dto

    suggestion_dto.accepted = verdict
    async with session.begin():
        await suggestion_service.update(suggestion_dto)

    await renderer.verdict_rewrite(user_dto)
    await state.clear()

    if suggestion_dto.accepted:
        await moderation.process_accepted(suggestion_dto)


@router.message(I18nTextFilter("command_enter_viewer"))
async def enter_suggestion_viewer(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_dto: UserDTO,
    suggestion_service: FromDishka[SuggestionService],
    renderer: FromDishka[SuggestionRenderer],
):
    await state.set_state(SuggestionViewerState.in_viewer)

    viewer_data = SuggestionViewerData(user_dto=user_dto)
    queue_manager = SuggestionQueueManager(session, suggestion_service, state, viewer_data)
    
    if new_suggestion := await queue_manager.pop_next():
        await renderer.start_review(user_dto)
        return await renderer.suggestion(user_dto, new_suggestion)

    await state.clear()
    await renderer.empty_queue(user_dto)

@router.message(SuggestionViewerState.in_viewer, I18nTextFilter("viewer_accept", verdict=True))
@router.message(SuggestionViewerState.in_viewer, I18nTextFilter("viewer_decline", verdict=False))
async def viewer_apply_verdict(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_dto: UserDTO,
    suggestion_service: FromDishka[SuggestionService],
    renderer: FromDishka[SuggestionRenderer],
    queue_manager: FromDishka[SuggestionQueueManager],
    moderation: FromDishka[SuggestionModerationService],
    verdict: bool,
):
    suggestion_dto = await queue_manager.get_updated_dto()
    
    if suggestion_dto.accepted is None:
        suggestion_dto.accepted = verdict
        async with session.begin():
            await suggestion_service.update(suggestion_dto)

        if suggestion_dto.accepted:
            await moderation.process_accepted(suggestion_dto)
    else:
        await renderer.verdict_exists(user_dto, suggestion_dto)

    if new_suggestion := await queue_manager.pop_next():
        await renderer.suggestion(user_dto, new_suggestion)
    else:
        await state.clear()
        await renderer.empty_queue(user_dto)


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
    renderer: FromDishka[SuggestionRenderer],
    queue_manager: FromDishka[SuggestionQueueManager],
):

    target_id = queue_manager.data.suggestion_dto.author_id
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

    #
    current_state = await state.get_state()
    if current_state != "SuggestionViewerState:in_solo_view":
        queue_manager.data.suggestion_dtos = None
        if new_suggestion := await queue_manager.pop_next():
            return await renderer.suggestion(user_dto, new_suggestion)
        await renderer.empty_queue(user_dto)
            
    await state.clear()