from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.formatting import Bold, Text

from config import Config
from database.models import UserAlchemy
from handlers.keyboards import get_main_kb_by_role
from services.notifier import Notifier

router = Router(name="start_handlers")


@router.message(CommandStart())
async def start(
    message: Message,
    user_alchemy: UserAlchemy,
    config: Config,
):
    text = Text(
        "Добро пожаловать в предложку канала ",
        Bold(config.channel_name),
        "!\n\n",
        "Чтобы предложить пост используйте клавиатуру.",
    )

    main_kb = get_main_kb_by_role(user_alchemy.role)
    return await message.answer(text.as_html(), reply_markup=main_kb)


@router.message(Command("cancel"))
async def cmd_cancel_state(
    message: Message,
    state: FSMContext,
    user_alchemy: UserAlchemy,
    notifier: Notifier,
):
    current_state = await state.get_state()
    if current_state:
        await state.clear()

    await notifier.answer_user_state_reset(user_alchemy.user_id, user_alchemy.role)


@router.message(F.text.lower() == "отмена")
async def cancel_state(
    message: Message,
    state: FSMContext,
    user_alchemy: UserAlchemy,
    notifier: Notifier,
):
    await cmd_cancel_state(message, state, user_alchemy, notifier)
