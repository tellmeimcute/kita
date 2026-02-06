
from aiogram import Bot

from aiogram.types import Message
from aiogram.utils.media_group import MediaGroupBuilder

from sqlalchemy import Result
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Suggestion
from database.dao import SuggestionDAO, UserAlchemyDAO

async def get_suggestions_logic(
    message: Message, 
    session: AsyncSession, 
    bot: Bot, 
    suggestion_id: int
):
    async with session.begin():
        suggestion: Suggestion = await SuggestionDAO.get_one_or_none(
            session, Suggestion.id == suggestion_id, (Suggestion.media, Suggestion.author)
        )

        #author = await UserAlchemyDAO.get_one_or_none_by_id(session, suggestion.author_id)

    if not suggestion:
        return
    
    medias = suggestion.media
    media_group = MediaGroupBuilder(
        caption=suggestion.caption
    )

    for media in medias:
        media_group.add(type=media.filetype, media=media.telegram_file_id)

    await bot.send_message(
        message.chat.id,
        f"Предложка от @{suggestion.author.username} ({suggestion.author_id}):"
    )

    await bot.send_media_group(
        message.chat.id,
        media=media_group.build()
    )


async def show_last_suggestion(
    message: Message,
    session: AsyncSession,
    bot: Bot
) -> int | None:
    async with session.begin():
        suggestion: Result = await SuggestionDAO.get_one_or_none(
            session, Suggestion.accepted.is_(None), (Suggestion.media, Suggestion.author)
        )

    if not suggestion:
        return None

    caption = (
        f"Предложка от @{suggestion.author.username} ({suggestion.author_id}):\n\n"
        f"ID: {suggestion.id}\n"
        f"Original caption:\n"
        f"{suggestion.caption}"
    )

    media_group = MediaGroupBuilder(caption=caption)

    for media in suggestion.media:
        media_group.add(type=media.filetype, media=media.telegram_file_id)

    await bot.send_media_group(
        message.chat.id,
        media=media_group.build()
    )

    return suggestion.id


async def change_accepted_state_suggestion(
    message: Message,
    session: AsyncSession,
    suggestion_id: int,
    is_accepted: bool
):
    async with session.begin():
        suggestion: Result = await SuggestionDAO.get_one_or_none_by_id(session, suggestion_id)
        suggestion.accepted = is_accepted
        await session.merge(suggestion)
    
    #await message.answer(f"suggestion {suggestion_id} {"accepted" if is_accepted else "declined"}.")