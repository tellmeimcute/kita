
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

from core.schemas.message_payload import MessagePayload
from core.filters import I18nTextFilter

from interfaces import UnitOfWorkProtocol, UserServiceProtocol
from database.dto import UserDTO
from services.notifier import NotifierService

from ui.state_groups import UserMenuSG

router = Router(name="main_menu")


@inject
async def on_language_selected(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    user_service: FromDishka[UserServiceProtocol],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    i18n: I18n = manager.middleware_data.get("i18n")

    if user_dto.language_code == button.widget_id:
        return await callback.answer(f"Your locale already {button.widget_id}!")

    user_dto.language_code = button.widget_id
    async with uow.transaction():
        await user_service.save(user_dto)

    i18n.ctx_locale.set(user_dto.language_code)
    await callback.answer(text=button.widget_id)
    await manager.switch_to(UserMenuSG.settings)


@inject
async def prefer_anon_toggle(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    user_service: FromDishka[UserServiceProtocol]
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")

    user_dto.prefer_anonymous = not user_dto.prefer_anonymous
    async with uow.transaction():
        await user_service.save(user_dto)

    await callback.answer(text="Success")
    await manager.switch_to(UserMenuSG.settings)


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
