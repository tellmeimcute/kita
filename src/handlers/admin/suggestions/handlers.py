

from aiogram import Router, F, Bot
from aiogram.filters import MagicData
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession

from .state import SuggestionViewer

from .logics import (
    get_suggestions_logic, show_last_suggestion,
    change_accepted_state_suggestion
)

router = Router(name="suggestions_admin")
router.message.filter(
    MagicData(F.event.from_user.id == F.config.ADMIN_ID)
)

#router.message.middleware()

@router.message(Command("get_suggestion", prefix='/!'))
async def get_suggestion(
    message: Message, 
    session: AsyncSession,
    command: CommandObject,
    bot: Bot
):
    suggestion_id = command.args
    await get_suggestions_logic(message, session, bot, suggestion_id)


@router.message(F.text.lower() == "смотреть предложку")
async def show_suggestions_admin_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot
):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Принять")],
            [KeyboardButton(text="Отклонить")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

    await message.answer(
        "Начинаем просмотр...",
        reply_markup=keyboard
    )

    last_suggestion_id = await show_last_suggestion(message, session, bot)
    if not last_suggestion_id:
        return await message.answer("Нет не рассмотренной предложки :(")

    await state.set_state(SuggestionViewer.in_viewer)
    await state.set_data({"last": last_suggestion_id})

@router.message(
    (F.text.lower() == "принять") | (F.text.lower() == "отклонить"),
    SuggestionViewer.in_viewer
)
async def accept_cur_suggestion(
    message: Message, 
    session: AsyncSession,
    state: FSMContext,
    bot: Bot
):
    text = message.text.lower()
    is_accepted = True if text == "принять" else False

    data = await state.get_data()
    cur_id: int = data["last"]
    await change_accepted_state_suggestion(message, session, cur_id, is_accepted)

    last_suggestion_id = await show_last_suggestion(message, session, bot)
    if not last_suggestion_id:
        await state.clear()
        return await message.answer("Предложка закончилась!", reply_markup=ReplyKeyboardRemove())
        
    await state.set_data({"last": last_suggestion_id})



