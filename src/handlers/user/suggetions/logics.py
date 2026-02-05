from typing import Sequence

from aiogram import Bot
from aiogram.fsm.state import State
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Suggestion
from database.dao.suggestion import SuggestionDAO

from helpers.utils import build_album_suggestions


async def suggestion_logic(
    session: AsyncSession,
    bot: Bot,
    album: Sequence[Message],
    state: State,
    user_id: int,
    username: str,
    admin_id: int,
    media_group_id: str | None = None,
):
    suggestion, medias, media_group = build_album_suggestions(album, user_id, media_group_id)

    if not len(medias):
        return await bot.send_message(
            chat_id=user_id, text="Отправьте картинки/видео/gif."
        )

    await bot.send_message(
        chat_id=admin_id, text=f"Новый пост от @{username} ({user_id}):"
    )

    await bot.send_media_group(chat_id=admin_id, media=media_group.build())

    await bot.send_message(chat_id=user_id, text="Отправлено.")

    await state.clear()

    async with session.begin():
        session.add_all((suggestion, *medias))


async def statistic_logic(
        message: Message,
        session: AsyncSession, 
        user_id: int
    ):
    async with session.begin():
        user_suggestions = await SuggestionDAO.get(session, Suggestion.author_id == user_id, Suggestion.id.desc())
        user_suggestions_count = await SuggestionDAO.count(session, Suggestion.author_id == user_id)

    await message.answer(
        f"Постов предожено: {user_suggestions_count}.\n{user_suggestions}"
    )