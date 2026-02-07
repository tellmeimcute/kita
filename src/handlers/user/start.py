
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from aiogram.utils.formatting import Bold, Text
from handlers.keyboards import main_kb

from config import Config

router = Router(name="start_handlers")

@router.message(CommandStart())
async def start(
    message: Message,
    config: Config
):
    channel_info = await message.bot.get_chat(config.CHANNEL_ID)
    text = Text(
        "Добро пожаловать в предложку канала ", Bold(channel_info.full_name), "!\n\n",
        "Чтобы предложить пост используйте клавиатуру."
    )
    return message.answer(text.as_html(), reply_markup=main_kb)

@router.message(Command("cancel"))
async def cmd_cancel_state(
    message: Message,
    state: FSMContext
):
    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.clear()
    await message.answer("Состояние сброшено", reply_markup=main_kb)

@router.message(F.text.lower() == "отмена")
async def cancel_state(message: Message, state: FSMContext):
    await cmd_cancel_state(message, state)