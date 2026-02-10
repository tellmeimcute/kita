from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.media_group import MediaGroupBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import SuggestionDAO, UserAlchemyDAO
from database.models import Suggestion, UserAlchemy
from handlers.keyboards import accept_decline_kb, get_main_kb_by_role
from helpers.utils import ban_user

from .logics import (
    get_active_suggestion,
    get_suggestion_by_id,
    go_next_suggestion,
    post_in_channel,
    update_review_state,
)
from .state import SuggestionViewer

router = Router(name="admin_suggestions")


@router.message(Command("get_suggestion", prefix="/!"))
async def get_suggestion(
    message: Message,
    session: AsyncSession,
    command: CommandObject,
    bot: Bot,
):
    suggestion_id = command.args
    raw_suggestion = await get_suggestion_by_id(session, suggestion_id)
    if not raw_suggestion:
        return await message.answer(f"Предложки с ID {suggestion_id} не найдено :(")

    suggestion, media_group = raw_suggestion
    await bot.send_message(
        message.chat.id, f"Предложка от @{suggestion.author.username} ({suggestion.author_id}):"
    )

    await bot.send_media_group(message.chat.id, media=media_group.build())


@router.message(F.text.lower() == "смотреть предложку")
async def show_suggestions_admin_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_alchemy: UserAlchemy,
    bot: Bot,
):
    raw_suggestion = await get_active_suggestion(session)

    if not raw_suggestion:
        main_kb = get_main_kb_by_role(user_alchemy.role)
        return await message.answer("Нет не рассмотренной предложки :(", reply_markup=main_kb)
    await message.answer("Начинаем просмотр...", reply_markup=accept_decline_kb)

    await state.set_state(SuggestionViewer.in_viewer)

    chat_id = message.chat.id
    suggestion, media_group = raw_suggestion
    suggestions_left = await SuggestionDAO.get_active_count(session)

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
    is_accepted: bool = False,
):
    text = message.text.lower()
    is_accepted = text == "принять" or is_accepted

    data = await state.get_data()
    cur_suggestion_id: int = data["last"]

    async with session.begin():
        cur_suggestion = await SuggestionDAO.get_one_or_none_by_id(
            session, cur_suggestion_id, solo=True
        )

        # Запостить (если принято) и обновить в базе.
        if cur_suggestion.accepted is None:
            if is_accepted:
                cur_media_group: MediaGroupBuilder = data["media_group"]
                await post_in_channel(
                    bot, cur_media_group, cur_suggestion, config.CHANNEL_ID, with_caption
                )

            cur_suggestion.accepted = is_accepted

    # Получаем новый (следующий) suggestion
    return await go_next_suggestion(message, session, state, bot, user_alchemy.role, data)


@router.message(SuggestionViewer.in_viewer, F.text.lower() == "бан")
async def ban_suggestion_author(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    user_alchemy: UserAlchemy,
    config: Config,
):
    data = await state.get_data()
    cur_suggestion: Suggestion = data["suggestion"]

    async with session.begin():
        caller_id = message.from_user.id
        target_id = cur_suggestion.author_id
        if not await ban_user(session, target_id, config):
            return await bot.send_message(caller_id, "Этому пользователю нельзя изменять роль.")

    # Получаем новый (следующий) suggestion
    return await go_next_suggestion(message, session, state, bot, user_alchemy.role, data)


@router.message(SuggestionViewer.in_viewer, (F.text.lower() == "принять без подписи"))
async def accept_wo_caption(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    user_alchemy: UserAlchemy,
    config: Config,
):
    await accept_deny_suggestion(message, session, state, bot, user_alchemy, config, False, True)
