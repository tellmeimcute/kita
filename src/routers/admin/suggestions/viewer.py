
import asyncio
from logging import getLogger

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.filters import I18nTextFilter
from core.exceptions import UserImmuneError
from core.i18n_translator import Translator
from core.schemas.message_payload import MessagePayload
from core.schemas.viewer import SuggestionViewerData
from core.schemas import SuggestionViewerData
from core.events import EventBus, CopyMessagesToUserEvent

from database.dto import UserDTO
from database.enums import UserRole, SuggestionStatus
from interfaces import (
    UnitOfWorkProtocol,
    SuggestionServiceProtocol,
    NotifierServiceProtocol,
)

from usecases.moderate_suggestion import ModerateSuggestionUseCase, ModerationResult
from usecases import ChangeRoleUseCase

from ui.state_groups import SuggestionViewerSG
from ui.suggestion_renderer import SuggestionRenderer
from ui.state_groups import UserMenuSG
from ui.keyboards import ReplyKeyboard


router = Router(name="admin_suggestions")
logger = getLogger("kita.admin_suggestions")

@inject
async def enter_suggestion_viewer(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    suggestion_service: FromDishka[SuggestionServiceProtocol],
    viewer_data: FromDishka[SuggestionViewerData],
    renderer: FromDishka[SuggestionRenderer],
    tl: FromDishka[Translator],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    state: FSMContext = manager.middleware_data.get("state")

    async with uow.transaction():
        new_suggestions: list | None = await suggestion_service.get_active()

    if not new_suggestions:
        warning = tl.translate("suggestion_no_active")
        return await callback.answer(warning)

    cur_suggestion = new_suggestions.pop(0)

    viewer_data.suggestion_dtos = new_suggestions
    viewer_data.suggestion_dto = cur_suggestion

    await manager.reset_stack()
    await state.set_state(SuggestionViewerSG.in_viewer)
    await state.set_data({"viewer_data": viewer_data.model_dump(mode="json")})
    await renderer.suggestion(user_dto, cur_suggestion)


@router.message(SuggestionViewerSG.in_viewer, I18nTextFilter("viewer_accept", verdict=SuggestionStatus.ACCEPTED))
@router.message(SuggestionViewerSG.in_viewer, I18nTextFilter("viewer_decline", verdict=SuggestionStatus.DECLINED))
async def viewer_verdict(
    message: Message,
    state: FSMContext,
    dialog_manager: DialogManager,
    user_dto: UserDTO,
    viewer_data: FromDishka[SuggestionViewerData],
    uow: FromDishka[UnitOfWorkProtocol],
    suggestion_service: FromDishka[SuggestionServiceProtocol],
    renderer: FromDishka[SuggestionRenderer],
    moderation_usecase: FromDishka[ModerateSuggestionUseCase],
    verdict: SuggestionStatus,
):
    async with uow.transaction():
        updated_dto = await suggestion_service.get(viewer_data.suggestion_dto.id)
        result: ModerationResult = await moderation_usecase.execute(updated_dto, verdict)

    if result.verdict_exists:
        await renderer.verdict_exists(user_dto, result.suggestion_dto)

    if not viewer_data.suggestion_dtos:
        async with uow.transaction():
            new_suggestions: list | None = await suggestion_service.get_active()
            
        if not new_suggestions:
            await state.clear()
            await renderer.empty_queue(user_dto)
            return await dialog_manager.start(
                UserMenuSG.main,
                mode=StartMode.RESET_STACK,
                show_mode=ShowMode.DELETE_AND_SEND,
            )
        
        viewer_data.suggestion_dtos = new_suggestions

    new_suggestion = viewer_data.suggestion_dtos.pop(0)
    viewer_data.suggestion_dto = new_suggestion
    await state.set_data({"viewer_data": viewer_data.model_dump(mode="json")})

    return await renderer.suggestion(user_dto, new_suggestion)


@router.message(SuggestionViewerSG.in_viewer, I18nTextFilter("ban_btn"))
async def viewer_ban_author(
    message: Message,
    state: FSMContext,
    dialog_manager: DialogManager,
    user_dto: UserDTO,
    viewer_data: FromDishka[SuggestionViewerData],
    uow: FromDishka[UnitOfWorkProtocol],
    suggestion_service: FromDishka[SuggestionServiceProtocol],
    notifier: FromDishka[NotifierServiceProtocol],
    renderer: FromDishka[SuggestionRenderer],
    change_role_usecase: FromDishka[ChangeRoleUseCase],
):
    target_id = viewer_data.suggestion_dto.author_id
    target_role = UserRole.BANNED

    try:
        async with uow.transaction():
            await change_role_usecase.execute(
                target_id, target_role, caller=user_dto
            )
    except UserImmuneError:
        payload = MessagePayload(i18n_key="error_user_immune")
        return await notifier.notify_user(user_dto, payload)
    
    viewer_data.suggestion_dtos = None
    async with uow.transaction():
        new_suggestions: list | None = await suggestion_service.get_active()

    if not new_suggestions:
        await state.clear()
        await renderer.empty_queue(user_dto)
        return await dialog_manager.start(
            UserMenuSG.main,
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.DELETE_AND_SEND,
        )

    cur_suggestion = new_suggestions.pop(0)
    viewer_data.suggestion_dtos = new_suggestions
    viewer_data.suggestion_dto = cur_suggestion

    await state.set_data({"viewer_data": viewer_data.model_dump(mode="json")})
    return await renderer.suggestion(user_dto, cur_suggestion)


@router.message(SuggestionViewerSG.in_viewer, I18nTextFilter("viewer_message_to_user_btn"))
async def enter_message_to_user(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    notifier: FromDishka[NotifierServiceProtocol],
):
    await state.set_state(SuggestionViewerSG.message_user)

    payload = MessagePayload(i18n_key="wait_message_text", reply_markup=ReplyKeyboard.viewer_back())
    await notifier.notify_user(user_dto, payload)


@router.message(SuggestionViewerSG.message_user, I18nTextFilter("viewer_back_btn"))
async def viewer_back(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    notifier: FromDishka[NotifierServiceProtocol],
):
    await state.set_state(SuggestionViewerSG.in_viewer)
    payload = MessagePayload(
        i18n_key="wait_verdict_text",
        reply_markup=ReplyKeyboard.viewer_admin_action(),
    )
    await notifier.notify_user(user_dto, payload)

@router.message(SuggestionViewerSG.message_user, ~I18nTextFilter("viewer_back_btn"))
async def message_to_user(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    viewer_data: FromDishka[SuggestionViewerData],
    notifier: FromDishka[NotifierServiceProtocol],
    event_bus: FromDishka[EventBus],
    album: list[Message] | None = None,
):
    target_dto = viewer_data.suggestion_dto.author
    if not album:
        album = (message,)
    
    album_ids = [m.message_id for m in album]
    
    event_bus.dispatch(
        CopyMessagesToUserEvent(
            user_dto=target_dto,
            caller_dto=user_dto,
            source_chat_id=message.chat.id,
            album_ids=album_ids,
        )
    )

    await state.set_state(SuggestionViewerSG.in_viewer)

    payload = MessagePayload(
        i18n_key="wait_verdict_text",
        reply_markup=ReplyKeyboard.viewer_admin_action(),
    )
    await notifier.notify_user(user_dto, payload)
