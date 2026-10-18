from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram_dialog import DialogManager, ShowMode, StartMode
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.filters import I18nTextFilter
from database.dto import UserDTO, UserProfileDTO
from interfaces import (
    MessageNotifierProtocol,
    UnitOfWorkProtocol,
    UserProfileServiceProtocol,
)
from routers.shared_handlers import language_selected
from ui.state_groups import UserMenuSG

router = Router(name="main_menu")

on_language_selected = language_selected(UserMenuSG.settings)


@inject
async def prefer_anon_toggle(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    user_profile_service: FromDishka[UserProfileServiceProtocol],
):
    profile_dto: UserProfileDTO = manager.middleware_data.get("profile_dto")

    profile_dto.prefer_anonymous = not profile_dto.prefer_anonymous
    async with uow.transaction():
        await user_profile_service.save(profile_dto)

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
    notifier: FromDishka[MessageNotifierProtocol],
):
    await notifier.send_text(user_dto, "state_reset", kb=ReplyKeyboardRemove())
    await start_main_menu(message, state, dialog_manager)
