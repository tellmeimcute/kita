
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.utils.i18n import I18n

from sqlalchemy.ext.asyncio import AsyncSession

from dishka import FromDishka

from core.enums import SettingsMenu
from database.dto import UserDTO
from ui.keyboards import ReplyKeyboard
from helpers.filters import I18nTextFilter
from helpers.schemas.message_payload import MessagePayload
from services.notifier import NotifierService
from services.user import UserService

from helpers.callbacks import ChangeLocaleCallback, SettingsMenuCallback

from ui.settings_menu import SettingsMenuRenderer

router = Router(name="settings")


@router.message(I18nTextFilter("command_get_settings_menu"))
async def new_settings_menu(
    message: Message,
    user_dto: UserDTO,
    renderer: FromDishka[SettingsMenuRenderer],
):
    await renderer.new_settings_menu(user_dto)


@router.callback_query(SettingsMenuCallback.filter())
async def change_menu_page(
    query: CallbackQuery,
    callback_data: SettingsMenuCallback,
    i18n: I18n,
    renderer: FromDishka[SettingsMenuRenderer],
):
    if callback_data.new_menu == SettingsMenu.settings_menu:
        await renderer.settings_menu(query.message)
    if callback_data.new_menu == SettingsMenu.locale_menu:
        await renderer.locale_menu(i18n, query.message)


@router.callback_query(ChangeLocaleCallback.filter())
async def change_locale(
    query: CallbackQuery,
    callback_data: ChangeLocaleCallback,
    session: AsyncSession,
    user_dto: UserDTO,
    user_service: UserService,
    i18n: I18n,
    notifier: FromDishka[NotifierService],
    renderer: FromDishka[SettingsMenuRenderer],
):
    await query.answer(f"Your new locale is {callback_data.locale}!")

    user_dto.language_code = callback_data.locale
    async with session.begin():
        await user_service.update_from_data(user_dto, user_dto.prepare_changed_data())

    with i18n.use_locale(user_dto.language_code):
        await renderer.locale_menu(i18n, query.message)
        payload = MessagePayload(i18n_key="locale_changed_msg", reply_markup=ReplyKeyboard.main(user_dto))
        await notifier.notify_user(user_dto, payload)
