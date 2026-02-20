from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.i18n import lazy_gettext as __
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao import MediaDAO, SuggestionDAO, UserAlchemyDAO
from helpers.filters import I18nTextFilter


router = Router()


@router.message(I18nTextFilter("admin_stats_command"))
async def promote_user(
    message: Message,
    session: AsyncSession,
):
    suggestions_count = await SuggestionDAO.count(session)
    media_count = await MediaDAO.count(session)

    user_stats = await UserAlchemyDAO.get_users_stats(session)

    await message.answer(
        f"👤 Всего пользователей: {user_stats.total}\n"
        f"🤡 Забаненых пользователей: {user_stats.banned}\n"
        f"😎 Кол-во админов: {user_stats.admins}\n\n"
        f"📄 Всего постов предложено: {suggestions_count}\n"
        f"🎨 Всего медиа файлов: {media_count}\n"
    )
