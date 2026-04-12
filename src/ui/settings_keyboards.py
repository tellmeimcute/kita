
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _
from aiogram.utils.i18n import I18n

from helpers.callbacks import ChangeLocaleCallback
from core.enums import SettingsMenu
from helpers.callbacks import SettingsMenuCallback

class SettingsKeyboards:

    @classmethod
    def options_list(cls):
        kb = InlineKeyboardBuilder()

        kb.button(
            text=_(SettingsMenu.locale_menu_btn),
            callback_data=SettingsMenuCallback(new_menu=SettingsMenu.locale_menu).pack(),
        )

        kb.adjust(1)
        return kb.as_markup()

    @classmethod
    def locale_list(cls, i18n: I18n):
        kb = InlineKeyboardBuilder()
        for locale in i18n.available_locales:
            kb.button(text=locale, callback_data=ChangeLocaleCallback(locale=locale).pack())

        kb.button(text=_(SettingsMenu.settings_menu_btn), callback_data=SettingsMenuCallback(new_menu=SettingsMenu.settings_menu).pack())
        kb.adjust(1)

        return kb.as_markup()