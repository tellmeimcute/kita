
from aiogram import Router
from database.models import UserAlchemy
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

router = Router(name="start_handlers")

@router.message(CommandStart())
async def start(message: Message, user_alchemy: UserAlchemy):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Предложить пост")],
            [KeyboardButton(text="Статистика")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
    return message.answer(f"{user_alchemy}", reply_markup=keyboard)