
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.formatting import Bold, Text

from database.models import UserAlchemy
from config import Config
from handlers.keyboards import get_main_kb_by_role

router = Router(name="start_handlers")

@router.message(CommandStart())
async def start(
    message: Message,
    user_alchemy: UserAlchemy,
    config: Config
):
    channel_info = await message.bot.get_chat(config.CHANNEL_ID)
    text = Text(
        "Добро пожаловать в предложку канала ", Bold(channel_info.full_name), "!\n\n",
        "Чтобы предложить пост используйте клавиатуру."
    )

    main_kb = get_main_kb_by_role(user_alchemy.role)
    return message.answer(text.as_html(), reply_markup=main_kb)

@router.message(Command("cancel"))
async def cmd_cancel_state(
    message: Message,
    state: FSMContext,
    user_alchemy: UserAlchemy
):
    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.clear()
    main_kb = get_main_kb_by_role(user_alchemy.role)
    await message.answer("Состояние сброшено", reply_markup=main_kb)

@router.message(F.text.lower() == "отмена")
async def cancel_state(message: Message, state: FSMContext, user_alchemy: UserAlchemy):
    await cmd_cancel_state(message, state, user_alchemy)