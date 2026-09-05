from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.exceptions import UserImmuneError
from core.filters import I18nTextFilter
from core.i18n_translator import Translator
from database.dto import UserDTO
from database.enums import SuggestionStatus as status
from database.enums import UserRole
from interfaces import (
    MessageNotifierProtocol,
    SuggestionQueueProtocol,
    SuggestionServiceProtocol,
    SuggestionViewerProtocol,
    UnitOfWorkProtocol,
)
from ui.keyboards import ReplyKeyboard
from ui.state_groups import SuggestionViewerSG
from usecases import ChangeRoleUseCase, MessageUserUseCase
from usecases.moderate_suggestion import ModerateSuggestionUseCase

router = Router(name="admin_suggestions")


@inject
async def enter_suggestion_viewer(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    suggestion_service: FromDishka[SuggestionServiceProtocol],
    suggestion_queue: FromDishka[SuggestionQueueProtocol],
    suggestion_viewer: FromDishka[SuggestionViewerProtocol],
    tl: FromDishka[Translator],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    state: FSMContext = manager.middleware_data.get("state")

    async with uow.transaction():
        new_suggestions = await suggestion_service.get_active()

    if not new_suggestions:
        return await callback.answer(tl.translate("suggestion_no_active"))

    await manager.reset_stack()
    await state.set_state(SuggestionViewerSG.in_viewer)

    await suggestion_queue.seed_queue(new_suggestions)
    await suggestion_viewer.advance(user_dto)


@router.message(
    SuggestionViewerSG.in_viewer,
    I18nTextFilter("viewer_accept", verdict=status.ACCEPTED),
)
@router.message(
    SuggestionViewerSG.in_viewer,
    I18nTextFilter("viewer_decline", verdict=status.DECLINED),
)
async def viewer_verdict(
    message: Message,
    dialog_manager: DialogManager,
    user_dto: UserDTO,
    uow: FromDishka[UnitOfWorkProtocol],
    suggestion_service: FromDishka[SuggestionServiceProtocol],
    notifier: FromDishka[MessageNotifierProtocol],
    moderate: FromDishka[ModerateSuggestionUseCase],
    suggestion_viewer: FromDishka[SuggestionViewerProtocol],
    verdict: status,
):
    current_suggestion = await suggestion_viewer.get_current()
    if not current_suggestion:
        return await suggestion_viewer.return_to_menu(dialog_manager, user_dto)

    async with uow.transaction():
        updated_dto = await suggestion_service.get(current_suggestion.id)

    result = await moderate.execute(updated_dto, verdict)

    if result.verdict_exists:
        return await notifier.send_text(
            user_dto,
            "suggestion_verdict_exists",
            i18n_kwargs=dict(
                id=result.suggestion_dto.id,
                verdict=result.suggestion_dto.status,
            ),
        )

    advanced = await suggestion_viewer.advance(user_dto)
    if not advanced:
        return await suggestion_viewer.return_to_menu(dialog_manager, user_dto)


@router.message(SuggestionViewerSG.in_viewer, I18nTextFilter("ban_btn"))
async def viewer_ban_author(
    message: Message,
    dialog_manager: DialogManager,
    user_dto: UserDTO,
    uow: FromDishka[UnitOfWorkProtocol],
    notifier: FromDishka[MessageNotifierProtocol],
    change_role_usecase: FromDishka[ChangeRoleUseCase],
    suggestion_viewer: FromDishka[SuggestionViewerProtocol],
):
    current_suggestion = await suggestion_viewer.get_current()
    target_id = current_suggestion.author_id

    try:
        async with uow.transaction():
            await change_role_usecase.execute(target_id, UserRole.BANNED, caller=user_dto)
    except UserImmuneError:
        return await notifier.send_text(user_dto, "error_user_immune")

    advanced = await suggestion_viewer.advance(user_dto)
    if not advanced:
        return await suggestion_viewer.return_to_menu(dialog_manager, user_dto)


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


@router.message(SuggestionViewerSG.message_user, ~I18nTextFilter("viewer_back_btn"))
async def message_to_user(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    notifier: FromDishka[MessageNotifierProtocol],
    message_user_usecase: FromDishka[MessageUserUseCase],
    suggestion_viewer: FromDishka[SuggestionViewerProtocol],
    album: list[Message] | None = None,
):
    current_suggestion = await suggestion_viewer.get_current()
    target_dto = current_suggestion.author

    if not album:
        album = (message,)

    album_ids = [m.message_id for m in album]

    await message_user_usecase.execute(target_dto, user_dto, album_ids, message.chat.id)

    await state.set_state(SuggestionViewerSG.in_viewer)
    await notifier.send_text(
        user_dto,
        "wait_verdict_text",
        kb=ReplyKeyboard.viewer_actions(),
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
        kb=ReplyKeyboard.viewer_actions(),
    )
