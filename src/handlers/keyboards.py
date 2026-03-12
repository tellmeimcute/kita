from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.i18n import gettext as _

#from aiogram.utils.keyboard import ReplyKeyboardBuilder
from database.roles import UserRole


def get_cancel_kb():
    cancel_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_("command_cancel"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    return cancel_kb

def get_confirm_decline_kb():
    confirm_decline_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_("confirm")), KeyboardButton(text=_("decline"))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
    return confirm_decline_kb

def get_viewer_accept_decline_kb():
    accept_decline_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_("viewer_accept")), KeyboardButton(text=_("viewer_decline"))],
            [KeyboardButton(text=_("viewer_accept_no_caption")), KeyboardButton(text=_("command_ban_filter"))],
            [KeyboardButton(text=_("command_cancel"))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
    return accept_decline_kb

def get_main_kb_by_role(user_role: UserRole):
    if user_role == UserRole.ADMIN:
        main_kb_admin = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=_("command_suggest_post")), KeyboardButton(text=_("command_user_stats"))],
                [KeyboardButton(text=_("command_enter_viewer"))],
                [KeyboardButton(text=_("command_get_admin_menu"))],
            ],
            resize_keyboard=True,
            is_persistent=True,
        )
        return main_kb_admin
    
    main_kb_user = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_("command_suggest_post")), KeyboardButton(text=_("command_user_stats"))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
    return main_kb_user

def get_admin_kb():
    admin_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_("command_post_banner")), KeyboardButton(text=_("command_admin_stats")), KeyboardButton(text=_("command_mass_message"))],
            [KeyboardButton(text=_("command_ban_filter")), KeyboardButton(text=_("command_unban_filter"))],
            [KeyboardButton(text=_("command_admin_help"))], [KeyboardButton(text=_("command_cancel"))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
    return admin_kb