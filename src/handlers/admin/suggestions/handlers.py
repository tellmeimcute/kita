

from aiogram import Router, F, Bot
from aiogram.filters import MagicData
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.utils.media_group import MediaGroupBuilder

from sqlalchemy.ext.asyncio import AsyncSession
from database.dao import SuggestionDAO
from config import Config

from .state import SuggestionViewer
from .logics import (
    get_suggestions_logic, show_last_suggestion
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

    raw_suggestion = await show_last_suggestion(message, session, bot)
    if not raw_suggestion:
        return await message.answer("Нет не рассмотренной предложки :(")

    suggestion, media_group = raw_suggestion
    await state.set_state(SuggestionViewer.in_viewer)
    await state.set_data({"last": suggestion.id, "media_group": media_group})

@router.message(
    SuggestionViewer.in_viewer,
    (F.text.lower() == "принять") | (F.text.lower() == "отклонить")
)
async def accept_deny_suggestion(
    message: Message, 
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    config: Config
):
    text = message.text.lower()
    is_accepted = True if text == "принять" else False

    data = await state.get_data()
    cur_id: int = data["last"]

    # Запостить.
    if is_accepted:
        media_group: MediaGroupBuilder = data["media_group"]
        suggestion_caption = f"{media_group.caption if media_group.caption else ""}"
        media_group.caption = f"#предложка\n{suggestion_caption}"
        await bot.send_media_group(config.CHANNEL_ID, media=media_group.build())

    # Обновить в базе.
    async with session.begin():
        await SuggestionDAO.update_by_id(session, cur_id, {"accepted": is_accepted})

    # Получаем новый (следующий) suggestion
    raw_suggestion = await show_last_suggestion(message, session, bot)
    if not raw_suggestion:
        await state.clear()
        return await message.answer("Предложка закончилась!", reply_markup=ReplyKeyboardRemove())
    
    suggestion, media_group = raw_suggestion
    await state.set_data({"last": suggestion.id, "media_group": media_group})