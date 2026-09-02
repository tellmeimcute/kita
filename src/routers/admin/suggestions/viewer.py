from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram_dialog import DialogManager, ShowMode, StartMode
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.exceptions import UserImmuneError
from core.filters import I18nTextFilter
from core.i18n_translator import Translator
from core.schemas import SuggestionViewerData
from database.dto import UserDTO
from database.dto.suggestion import SuggestionFullDTO
from database.enums import SuggestionStatus, UserRole
from interfaces import (
    MessageNotifierProtocol,
    SuggestionNotifierProtocol,
    SuggestionServiceProtocol,
    UnitOfWorkProtocol,
)
from ui.keyboards import ReplyKeyboard
from ui.state_groups import SuggestionViewerSG, UserMenuSG
from usecases import ChangeRoleUseCase, MessageUserUseCase
from usecases.moderate_suggestion import ModerateSuggestionUseCase, ModerationResult

router = Router(name="admin_suggestions")


async def _load_next_suggestion(
    viewer_data: SuggestionViewerData,
    suggestion_service: SuggestionServiceProtocol,
    uow: UnitOfWorkProtocol,
) -> SuggestionFullDTO | None:
    if viewer_data.suggestion_dtos:
        next_suggestion = viewer_data.suggestion_dtos.pop(0)
        viewer_data.suggestion_dto = next_suggestion
        return next_suggestion

    async with uow.transaction():
        new_suggestions = await suggestion_service.get_active()

    if not new_suggestions:
        return None

    viewer_data.suggestion_dtos = list(new_suggestions)
    next_suggestion = viewer_data.suggestion_dtos.pop(0)
    viewer_data.suggestion_dto = next_suggestion
    return next_suggestion


async def _return_to_menu(
    user_dto: UserDTO,
    state: FSMContext,
    dialog_manager: DialogManager,
    notifier: MessageNotifierProtocol,
):
    await state.clear()
    await notifier.send_text(user_dto, "suggestion_no_active", kb=ReplyKeyboardRemove())
    return await dialog_manager.start(
        UserMenuSG.main,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.DELETE_AND_SEND,
    )


@inject
async def enter_suggestion_viewer(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    suggestion_service: FromDishka[SuggestionServiceProtocol],
    viewer_data: FromDishka[SuggestionViewerData],
    suggestion_notifier: FromDishka[SuggestionNotifierProtocol],
    tl: FromDishka[Translator],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    state: FSMContext = manager.middleware_data.get("state")

    async with uow.transaction():
        new_suggestions = await suggestion_service.get_active()

    if not new_suggestions:
        warning = tl.translate("suggestion_no_active")
        return await callback.answer(warning)

    viewer_data.suggestion_dtos = list(new_suggestions)
    first_suggestion = viewer_data.suggestion_dtos.pop(0)
    viewer_data.suggestion_dto = first_suggestion

    await manager.reset_stack()
    await state.set_state(SuggestionViewerSG.in_viewer)
    await state.set_data({"viewer_data": viewer_data.model_dump(mode="json")})

    await suggestion_notifier.send_to_admin(user_dto, first_suggestion)


@router.message(
    SuggestionViewerSG.in_viewer,
    I18nTextFilter("viewer_accept", verdict=SuggestionStatus.ACCEPTED),
)
@router.message(
    SuggestionViewerSG.in_viewer,
    I18nTextFilter("viewer_decline", verdict=SuggestionStatus.DECLINED),
)
async def viewer_verdict(
    message: Message,
    state: FSMContext,
    dialog_manager: DialogManager,
    user_dto: UserDTO,
    viewer_data: FromDishka[SuggestionViewerData],
    uow: FromDishka[UnitOfWorkProtocol],
    suggestion_service: FromDishka[SuggestionServiceProtocol],
    notifier: FromDishka[MessageNotifierProtocol],
    suggestion_notifier: FromDishka[SuggestionNotifierProtocol],
    moderation_usecase: FromDishka[ModerateSuggestionUseCase],
    verdict: SuggestionStatus,
):
    async with uow.transaction():
        updated_dto = await suggestion_service.get(viewer_data.suggestion_dto.id)
        result: ModerationResult = await moderation_usecase.execute(
            updated_dto, verdict, bot_id=message.bot.id
        )

    if result.verdict_exists:
        await notifier.send_text(
            user_dto,
            "suggestion_verdict_exists",
            i18n_kwargs=dict(id=result.suggestion_dto.id, verdict=result.suggestion_dto.status),
        )
        return None

    new_suggestion = await _load_next_suggestion(viewer_data, suggestion_service, uow)

    if not new_suggestion:
        return await _return_to_menu(user_dto, state, dialog_manager, notifier)

    await state.set_data({"viewer_data": viewer_data.model_dump(mode="json")})
    return await suggestion_notifier.send_to_admin(user_dto, new_suggestion)


@router.message(SuggestionViewerSG.in_viewer, I18nTextFilter("ban_btn"))
async def viewer_ban_author(
    message: Message,
    state: FSMContext,
    dialog_manager: DialogManager,
    user_dto: UserDTO,
    viewer_data: FromDishka[SuggestionViewerData],
    uow: FromDishka[UnitOfWorkProtocol],
    suggestion_service: FromDishka[SuggestionServiceProtocol],
    notifier: FromDishka[MessageNotifierProtocol],
    suggestion_notifier: FromDishka[SuggestionNotifierProtocol],
    change_role_usecase: FromDishka[ChangeRoleUseCase],
):
    target_id = viewer_data.suggestion_dto.author_id
    target_role = UserRole.BANNED

    try:
        async with uow.transaction():
            await change_role_usecase.execute(target_id, target_role, caller=user_dto)
    except UserImmuneError:
        return await notifier.send_text(user_dto, "error_user_immune")

    new_suggestion = await _load_next_suggestion(viewer_data, suggestion_service, uow)

    if not new_suggestion:
        return await _return_to_menu(user_dto, state, dialog_manager, notifier)

    await state.set_data({"viewer_data": viewer_data.model_dump(mode="json")})
    return await suggestion_notifier.send_to_admin(user_dto, new_suggestion)


@router.message(SuggestionViewerSG.in_viewer, I18nTextFilter("viewer_message_to_user_btn"))
async def enter_message_to_user(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    notifier: FromDishka[MessageNotifierProtocol],
):
    await state.set_state(SuggestionViewerSG.message_user)
    await notifier.send_text(
        user_dto,
        "wait_message_text",
        kb=ReplyKeyboard.viewer_back(),
    )


@router.message(SuggestionViewerSG.message_user, I18nTextFilter("viewer_back_btn"))
async def viewer_back(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    notifier: FromDishka[MessageNotifierProtocol],
):
    await state.set_state(SuggestionViewerSG.in_viewer)
    await notifier.send_text(
        user_dto,
        "wait_verdict_text",
        kb=ReplyKeyboard.viewer_admin_action(),
    )


@router.message(SuggestionViewerSG.message_user, ~I18nTextFilter("viewer_back_btn"))
async def message_to_user(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    viewer_data: FromDishka[SuggestionViewerData],
    notifier: FromDishka[MessageNotifierProtocol],
    message_user_usecase: FromDishka[MessageUserUseCase],
    album: list[Message] | None = None,
):
    target_dto = viewer_data.suggestion_dto.author
    if not album:
        album = (message,)

    album_ids = [m.message_id for m in album]

    await message_user_usecase.execute(target_dto, user_dto, album_ids, message.chat.id)

    await state.set_state(SuggestionViewerSG.in_viewer)
    await notifier.send_text(
        user_dto,
        "wait_verdict_text",
        kb=ReplyKeyboard.viewer_admin_action(),
    )
