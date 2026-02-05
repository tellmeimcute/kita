

from aiogram import Router

from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from aiogram.utils.media_group import MediaGroupBuilder

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Suggestion
from database.dao.suggestion import SuggestionDAO
from database.dao.user import UserAlchemyDAO

from config import Config

router = Router(name="suggestions_admin")
#router.message.middleware()

@router.message(Command("get_suggestion"))
async def get_suggestion(
    message: Message, 
    session: AsyncSession,
    config: Config, 
    command: CommandObject
):
    if message.from_user.id != config.ADMIN_ID:
        return

    suggestion_id = command.args

    async with session.begin():
        suggestion: Suggestion = await SuggestionDAO.get_one_or_none_with_children(
            session, Suggestion.media, Suggestion.id == suggestion_id
        )

    if not suggestion:
        return
    medias = suggestion.media

    media_group = MediaGroupBuilder(
        caption=suggestion.caption
    )

    for media in medias:
        media_group.add(type=media.filetype, media=media.telegram_file_id)

    author = await UserAlchemyDAO.get_one_or_none_by_id(session, suggestion.author_id)
    await message.bot.send_message(
        message.chat.id,
        f"Предложка от @{author.username} ({suggestion.author_id}):"
    )

    await message.bot.send_media_group(
        message.chat.id,
        media=media_group.build()
    )
