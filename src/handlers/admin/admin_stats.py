from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao import MediaDAO, SuggestionDAO, UserAlchemyDAO

router = Router()


@router.message(F.text.lower() == "админ статистика")
async def promote_user(
    message: Message,
    session: AsyncSession,
):
    user_count = await UserAlchemyDAO.count(session)
    suggestions_count = await SuggestionDAO.count(session)
    media_count = await MediaDAO.count(session)

    await message.answer(
        f"👤 Всего пользователей: {user_count}\n\n"
        f"📄 Всего постов предложено: {suggestions_count}\n"
        f"🎨 Всего медиа файлов: {media_count}\n"
    )
