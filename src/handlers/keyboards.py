from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.i18n import gettext as _

#from aiogram.utils.keyboard import ReplyKeyboardBuilder
from database.roles import UserRole


def get_cancel_kb():
    cancel_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_("cancel_command"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    return cancel_kb


def get_accept_decline_kb():
    accept_decline_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_("viewer_accept")), KeyboardButton(text=_("viewer_decline"))],
            [KeyboardButton(text=_("viewer_accept_no_caption")), KeyboardButton(text=_("command_ban_filter"))],
            [KeyboardButton(text=_("cancel_command"))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
    return accept_decline_kb

def get_main_kb_by_role(user_role: UserRole):
    if user_role == UserRole.ADMIN:
        main_kb_admin = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=_("suggest_post_command")), KeyboardButton(text=_("user_stats_command"))],
                [KeyboardButton(text=_("enter_viewer_command"))],
                [KeyboardButton(text=_("admin_stats_command"))],
            ],
            resize_keyboard=True,
            is_persistent=True,
        )
        return main_kb_admin
    
    main_kb_user = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_("suggest_post_command")), KeyboardButton(text=_("user_stats_command"))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
    return main_kb_user