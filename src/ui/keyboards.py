from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.i18n import gettext as _

from database.dto import UserDTO
from database.roles import UserRole


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
    def cancel(cls):
        return cls.build([KeyboardButton(text=_("command_cancel"))])

    @classmethod
    def confirm_decline(cls):
        return cls.build([KeyboardButton(text=_("confirm")), KeyboardButton(text=_("decline"))])

    @classmethod
    def viewer_admin_action(cls):
        return cls.build(
            [KeyboardButton(text=_("viewer_accept")), KeyboardButton(text=_("viewer_decline"))],
            [KeyboardButton(text=_("ban_btn"))],
            [KeyboardButton(text=_("command_cancel"))],
        )

    @classmethod
    def user_main(cls):
        return cls.build(
            [
                KeyboardButton(text=_("command_suggest_post")),
                KeyboardButton(text=_("command_open_menu")),
            ],
        )

    @classmethod
    def admin_main(cls):
        return cls.build(
            [
                KeyboardButton(text=_("command_suggest_post")),
                KeyboardButton(text=_("command_open_menu")),
            ],
            [KeyboardButton(text=_("command_enter_viewer"))],
            [KeyboardButton(text=_("command_get_admin_menu"))],
        )

    @classmethod
    def main(cls, user_dto: UserDTO):
        if user_dto.is_admin:
            return cls.admin_main()
        return cls.user_main()