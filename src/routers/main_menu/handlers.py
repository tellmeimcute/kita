import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from aiogram import Router
from aiogram.types import ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.i18n import I18n

from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.input import MessageInput

from core.exceptions import UnsupportedPayload
from helpers.suggestion_utils import SuggestionUtils

from database.dto import UserDTO
from services.user import UserService
from services.notifier import NotifierService
from services.suggestion import SuggestionService

from helpers.schemas.message_payload import MessagePayload
from helpers.filters import I18nTextFilter

from ui.state_groups import UserMenuSG

router = Router(name="main_menu")

@inject
async def on_language_selected(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    user_service: UserService = manager.middleware_data.get("user_service")
    session: AsyncSession = manager.middleware_data.get("session")

    i18n: I18n = manager.middleware_data.get("i18n")

    if user_dto.language_code == button.widget_id:
        return await callback.answer(f"Your locale already {button.widget_id}!")

    user_dto.language_code = button.widget_id
    async with session.begin():
        await user_service.update_from_data(user_dto, user_dto.prepare_changed_data())

    i18n.ctx_locale.set(user_dto.language_code)
    await callback.answer(text=button.widget_id)
    await manager.switch_to(UserMenuSG.settings)


@inject
async def on_album_received(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    suggestion_service: FromDishka[SuggestionService],
    notifier: FromDishka[NotifierService],
    user_service: FromDishka[UserService],
    suggestion_utils: FromDishka[SuggestionUtils],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    session: AsyncSession = manager.middleware_data.get("session")

    album = manager.middleware_data.get("album")

    if not album:
        album = (message,)

    try:
        async with session.begin():
            suggestion_dto = await suggestion_service.create(user_dto, album)
    except UnsupportedPayload:
        await session.rollback()
        return await manager.switch_to(UserMenuSG.suggestion_media_error, show_mode=ShowMode.DELETE_AND_SEND)
        
    await manager.switch_to(UserMenuSG.suggestion_on_moderation)

    admins = await user_service.get_admins()
    i18n_kwargs = suggestion_utils.get_i18n_kwargs(suggestion_dto)
    payload = MessagePayload(i18n_key="notify_admin_new_suggestion", i18n_kwargs=i18n_kwargs)
    asyncio.create_task(notifier.notify_many(admins, payload))


@router.message(CommandStart())
@router.message(I18nTextFilter("command_open_menu"))
async def start_main_menu(message: Message, state: FSMContext, dialog_manager: DialogManager):
    current_state = await state.get_state()
    if current_state:
        await state.clear()

    await dialog_manager.start(
        UserMenuSG.main,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.DELETE_AND_SEND,
    )

@router.message(I18nTextFilter("decline"))
@router.message(I18nTextFilter("command_cancel"))
@router.message(Command("cancel"))
async def cancel(
    message: Message,
    user_dto: UserDTO,
    state: FSMContext,
    dialog_manager: DialogManager,
    notifier: FromDishka[NotifierService],
):
    payload = MessagePayload(i18n_key="state_reset", reply_markup=ReplyKeyboardRemove())
    await notifier.notify_user(user_dto, payload=payload)
    await start_main_menu(message, state, dialog_manager)