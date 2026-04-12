
from aiogram.filters.callback_data import CallbackData


class ChangeLocaleCallback(CallbackData, prefix="change_locale"):
    locale: str


class SettingsMenuCallback(CallbackData, prefix="settings"):
    new_menu: str