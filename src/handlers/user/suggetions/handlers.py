
from typing import List

from aiogram import F, Router, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Suggestion
from database.dao import SuggestionDAO

from middlewares import MediaGroutMiddleware
from handlers.keyboards import cancel_kb, main_kb

from helpers.utils import build_album_suggestions
from config import Config

from .state import PostStates

router = Router(name="suggestions_user")
router.message.middleware(MediaGroutMiddleware(latency=0.25))

@router.message(F.text == "Предложить пост")
async def propose_post(message: Message, state: FSMContext):
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
    config: Config,
    media_group_id: int | None = None,
    album: List[Message] | None = None,
):
    user_id = message.from_user.id
    username = message.from_user.username

    if album is None:
        album = (message,)

    suggestion, medias, media_group = build_album_suggestions(album, user_id, media_group_id)

    if not len(medias):
        return await bot.send_message(
            chat_id=user_id, text="Отправьте картинки/видео/gif."
        )

    await bot.send_message(
        chat_id=config.ADMIN_ID, text=f"Новый пост от @{username} ({user_id}):"
    )

    await bot.send_media_group(chat_id=config.ADMIN_ID, media=media_group.build())

    await bot.send_message(chat_id=user_id, text="Отправлено.", reply_markup=main_kb)
    await state.clear()

    async with session.begin():
        session.add_all((suggestion, *medias))


@router.message(PostStates.waiting_for_post, F.media_group_id)
async def process_media_group_suggestion(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    album: List[Message],
    media_group_id: str,
    bot: Bot,
    config: Config
):
    await process_suggestion(message, state, session, bot, config, media_group_id, album)


@router.message(F.text == "Статистика")
async def statistic(message: Message, session: AsyncSession):
    user_id = message.from_user.id

    async with session.begin():
        user_suggestions = await SuggestionDAO.get(session, Suggestion.author_id == user_id, Suggestion.id.desc())
        user_suggestions_count = await SuggestionDAO.count(session, Suggestion.author_id == user_id)

    accepted_suggestions = [s for s in user_suggestions if s.accepted]

    await message.answer(
        f"Постов предожено: {user_suggestions_count}\n\n"
        f"✅ Принято: {len(accepted_suggestions)}\n"
    )