

import asyncio

from logging import getLogger
from typing import List

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import SuggestionDAO, UserAlchemyDAO
from database.models import Suggestion, UserAlchemy
from database.roles import UserRole
from handlers.keyboards import cancel_kb, get_main_kb_by_role
from helpers.utils import build_album_suggestions
from middlewares import MediaGroupMiddleware

from .state import PostStates

logger = getLogger("user_suggestions")

router = Router(name="suggestions_user")
router.message.middleware(MediaGroupMiddleware(latency=0.25))

@router.message(F.text == "Предложить пост")
async def suggest_post(message: Message, state: FSMContext):
    await state.set_state(PostStates.waiting_for_post)
    text = (
        "Отправьте картинки/видео/gif одним постом.\n\n"
        "Отменить действие можно в клавиатуре или командой /cancel"
    )
    await message.answer(text, reply_markup=cancel_kb)

@router.message(PostStates.waiting_for_post, ~F.media_group_id)
async def process_suggestion(
    message: Message,
    state: FSMContext, 
    session: AsyncSession,
    bot: Bot,
    user_alchemy: UserAlchemy,
    media_group_id: int | None = None,
    album: List[Message] | None = None,
):
    user_id = message.from_user.id
    username = message.from_user.username

    album = album or (message,)
    suggestion, medias, media_group = build_album_suggestions(album, user_id, media_group_id)

    if not medias:
        return await bot.send_message(chat_id=user_id, text="Отправьте картинки/видео/gif.")
    
    async with session.begin():
        session.add_all((suggestion, *medias))

    admins = await UserAlchemyDAO.get(session, UserAlchemy.role == UserRole.ADMIN)
    for admin in admins:
        try:
            await bot.send_message(
                chat_id=admin.user_id, text=f"Новый пост от @{username} ({user_id}):"
            )
            await bot.send_media_group(chat_id=admin.user_id, media=media_group.build())
        except Exception as e:
            logger.error("Ошибка при уведомлении админа ID %s username %s: %s", admin.id, admin.username, e)
        finally:
            await asyncio.sleep(0.05)

    main_kb = get_main_kb_by_role(user_alchemy.role)
    await bot.send_message(chat_id=user_id, text="Отправлено на модерацию.", reply_markup=main_kb)
    await state.clear()

@router.message(PostStates.waiting_for_post, F.media_group_id)
async def process_media_group_suggestion(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    album: List[Message],
    user_alchemy: UserAlchemy,
    media_group_id: str,
    bot: Bot,
):
    await process_suggestion(
        message, state, session, bot, user_alchemy, media_group_id, album
    )


@router.message(F.text == "Статистика")
async def statistic(message: Message, session: AsyncSession):
    user_id = message.from_user.id

    user_suggestions_count = await SuggestionDAO.count(session, Suggestion.author_id == user_id)
    accepted_suggestions = await SuggestionDAO.count(session, (Suggestion.author_id == user_id) & (Suggestion.accepted == True))

    await message.answer(
        f"Постов предожено: {user_suggestions_count}\n\n"
        f"✅ Принято: {accepted_suggestions}\n"
    )