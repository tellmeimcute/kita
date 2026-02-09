from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from database.roles import UserRole

main_kb_user = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Предложить пост"), KeyboardButton(text="Статистика")],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

main_kb_admin = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Предложить пост"), KeyboardButton(text="Статистика")],
        [KeyboardButton(text="Смотреть предложку")],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

accept_decline_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Принять"), KeyboardButton(text="Отклонить")],
        [KeyboardButton(text="Принять без подписи")],
        [KeyboardButton(text="Отмена")],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Отмена")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)


def get_main_kb_by_role(user_role: UserRole):
    if user_role == UserRole.ADMIN:
        return main_kb_admin
    return main_kb_user
