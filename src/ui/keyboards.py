from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.i18n import gettext as _

class ReplyKeyboard:
    @classmethod
    def build(cls, *buttons: list[KeyboardButton], one_time: bool = False):
        new_kb = ReplyKeyboardMarkup(
            keyboard=buttons,
            resize_keyboard=True,
            one_time_keyboard=one_time,
        )
        return new_kb

    @classmethod
    def viewer_admin_action(cls):
        return cls.build(
            [KeyboardButton(text=_("viewer_accept")), KeyboardButton(text=_("viewer_decline"))],
            [KeyboardButton(text=_("ban_btn"))],
            [KeyboardButton(text=_("command_cancel"))],
        )