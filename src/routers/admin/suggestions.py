
from logging import getLogger

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from aiogram_dialog import DialogManager, StartMode, ShowMode

from sqlalchemy.ext.asyncio import AsyncSession
from dishka import FromDishka

from core.filters import I18nTextFilter, TextArgsFilter
from core.schemas.message_payload import MessagePayload
from core.schemas import IDCommand
from core.schemas.data import SuggestionViewerData

from database.dto import UserDTO
from database.enums import UserRole

from services import NotifierService, SuggestionService
from services.suggestion_queue import SuggestionQueueManager
from usecases.moderate_suggestion import ModerateSuggestionUseCase, ModerationResult
from usecases.change_role import ChangeRoleUseCase

from routers.state import SuggestionViewerState

from ui.suggestion_renderer import SuggestionRenderer
from ui.state_groups import UserMenuSG


router = Router(name="admin_suggestions")
logger = getLogger("kita.admin_suggestions")


@router.message(TextArgsFilter("command_open_solo_view", IDCommand))
async def solo_suggestion(
    message: Message,
    user_dto: UserDTO,
    session: FromDishka[AsyncSession],
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
    state: FSMContext,
    session: FromDishka[AsyncSession],
    queue_manager: FromDishka[SuggestionQueueManager],
    moderation_usecase: FromDishka[ModerateSuggestionUseCase],
    renderer: FromDishka[SuggestionRenderer],
    verdict: bool,
):
    suggestion_dto = queue_manager.data.suggestion_dto
    async with session.begin():
        await moderation_usecase.execute(suggestion_dto, verdict, force_update=True)

    await renderer.verdict_rewrite(user_dto)
    await state.clear()


@router.message(I18nTextFilter("command_enter_viewer"))
async def enter_suggestion_viewer(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    queue_manager: FromDishka[SuggestionQueueManager],
    renderer: FromDishka[SuggestionRenderer],
):
    await state.set_state(SuggestionViewerState.in_viewer)

    if new_suggestion := await queue_manager.pop_next():
        await renderer.start_review(user_dto)
        return await renderer.suggestion(user_dto, new_suggestion)

    await state.clear()
    await renderer.empty_queue(user_dto)

@router.message(SuggestionViewerState.in_viewer, I18nTextFilter("viewer_accept", verdict=True))
@router.message(SuggestionViewerState.in_viewer, I18nTextFilter("viewer_decline", verdict=False))
async def viewer_apply_verdict(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    session: FromDishka[AsyncSession],
    renderer: FromDishka[SuggestionRenderer],
    queue_manager: FromDishka[SuggestionQueueManager],
    moderation_usecase: FromDishka[ModerateSuggestionUseCase],
    dialog_manager: DialogManager,
    verdict: bool,
):
    async with session.begin():
        updated_dto = await queue_manager.get_updated_dto()
        result: ModerationResult = await moderation_usecase.execute(updated_dto, verdict)

    if result.verdict_exists:
        await renderer.verdict_exists(user_dto, result.suggestion_dto)

    # ПОЛУЧАЕМ НОВУЮ ПРЕДЛОЖКУ
    if new_suggestion := await queue_manager.pop_next():
        await renderer.suggestion(user_dto, new_suggestion)
    else:
        await state.clear()
        await renderer.empty_queue(user_dto)

        await dialog_manager.start(
            UserMenuSG.main,
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.DELETE_AND_SEND,
        )


VIEWER_BAN_FILTER = I18nTextFilter("ban_btn")
@router.message(SuggestionViewerState.in_solo_view, VIEWER_BAN_FILTER)
@router.message(SuggestionViewerState.in_viewer, VIEWER_BAN_FILTER)
async def ban_suggestion_author(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    session: FromDishka[AsyncSession],
    notifier: FromDishka[NotifierService],
    renderer: FromDishka[SuggestionRenderer],
    queue_manager: FromDishka[SuggestionQueueManager],
    change_role_usecase: FromDishka[ChangeRoleUseCase],
):

    target_id = queue_manager.data.suggestion_dto.author_id
    target_role = UserRole.BANNED

    async with session.begin():
        target_dto = await change_role_usecase.execute(
            target_id,
            target_role,
            caller=user_dto,
        )

    payload = MessagePayload(
        i18n_key="answer_admin_role_changed",
        i18n_kwargs=target_dto.model_dump(),
    )
    await notifier.notify_user(user_dto, payload)

    #
    current_state = await state.get_state()
    if current_state != SuggestionViewerState.in_solo_view.state:
        queue_manager.data.suggestion_dtos = None
        if new_suggestion := await queue_manager.pop_next():
            return await renderer.suggestion(user_dto, new_suggestion)
        await renderer.empty_queue(user_dto)
            
    await state.clear()
    