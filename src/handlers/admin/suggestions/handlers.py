

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.media_group import MediaGroupBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.models import Suggestion, UserAlchemy
from database.dao import SuggestionDAO
from handlers.keyboards import accept_decline_kb, get_main_kb_by_role
from middlewares import AdminMiddleware

from .state import SuggestionViewer
from .logics import (
    get_suggestion_by_id,
    get_active_suggestion,
    post_in_channel,
    update_review_state
)

router = Router(name="suggestions_admin")
router.message.middleware(AdminMiddleware())

@router.message(Command("get_suggestion", prefix='/!'))
async def get_suggestion(
    message: Message, 
    session: AsyncSession,
    command: CommandObject,
    bot: Bot
):
    suggestion_id = command.args
    raw_suggestion = await get_suggestion_by_id(session, suggestion_id)
    if not raw_suggestion:
        return await message.answer(f"Предложки с ID {suggestion_id} не найдено :(")

    suggestion, media_group = raw_suggestion
    await bot.send_message(
        message.chat.id,
        f"Предложка от @{suggestion.author.username} ({suggestion.author_id}):"
    )

    await bot.send_media_group(
        message.chat.id,
        media=media_group.build()
    )


@router.message(F.text.lower() == "смотреть предложку")
async def show_suggestions_admin_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_alchemy: UserAlchemy,
    bot: Bot
):
    raw_suggestion = await get_active_suggestion(session)

    if not raw_suggestion:
        main_kb = get_main_kb_by_role(user_alchemy.role)
        return await message.answer("Нет не рассмотренной предложки :(", reply_markup=main_kb)
    await message.answer("Начинаем просмотр...", reply_markup=accept_decline_kb)

    await state.set_state(SuggestionViewer.in_viewer)

    chat_id = message.chat.id
    suggestion, media_group = raw_suggestion
    suggestions_left = await SuggestionDAO.count(session, Suggestion.accepted.is_(None))

    await update_review_state(suggestion, media_group, chat_id, bot, state, suggestions_left)


@router.message(
    SuggestionViewer.in_viewer, (F.text.lower() == "принять") | (F.text.lower() == "отклонить")
)
async def accept_deny_suggestion(
    message: Message, 
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    user_alchemy: UserAlchemy,
    config: Config,
    with_caption: bool = True,
    is_accepted: bool = False
):
    text = message.text.lower()
    is_accepted = text == "принять" or is_accepted

    data = await state.get_data()
    cur_suggestion_id: int = data["last"]

    # Запостить.
    if is_accepted:
        cur_media_group: MediaGroupBuilder = data["media_group"]
        cur_suggestion: Suggestion = data["suggestion"]
        await post_in_channel(bot, cur_media_group, cur_suggestion, config.CHANNEL_ID, with_caption)

    # Обновить в базе.
    async with session.begin():
        await SuggestionDAO.update_by_id(session, cur_suggestion_id, {"accepted": is_accepted})

    # Получаем новый (следующий) suggestion
    raw_suggestion = await get_active_suggestion(session)
    if not raw_suggestion:
        await state.clear()
        main_kb = get_main_kb_by_role(user_alchemy.role)
        return await message.answer("Предложка закончилась!", reply_markup=main_kb)
    
    chat_id = message.chat.id
    await update_review_state(*raw_suggestion, chat_id, bot, state, data=data)


@router.message(
    SuggestionViewer.in_viewer, (F.text.lower() == "принять без подписи")
)
async def accept_wo_caption(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    user_alchemy: UserAlchemy,
    config: Config
):
    await accept_deny_suggestion(message, session, state, bot, user_alchemy, config, False, True)