
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

accept_decline_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Принять"), KeyboardButton(text="Отклонить")],
        [KeyboardButton(text="Принять без подписи")],
        [KeyboardButton(text="Отмена")],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Предложить пост"), KeyboardButton(text="Статистика")],
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