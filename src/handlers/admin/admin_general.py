from pydantic import ValidationError

from aiogram import Router, html
from aiogram.types import Message
from aiogram.utils.i18n import lazy_gettext as __
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao import MediaDAO, SuggestionDAO, UserAlchemyDAO
from database.dto import UserDTO

from helpers.message_payload import MessagePayload
from helpers.schemas import ChangeRoleCommand
from helpers.filters import TargetIdFilter, I18nTextFilter
from helpers.utils import ban_user

from services.notifier import Notifier
from config import Config

router = Router()


@router.message(TargetIdFilter("command_ban_filter"))
async def ban_user_handler(
    message: Message,
    session: AsyncSession,
    user_dto: UserDTO,
    target_id: int,
    notifier: Notifier,
    config: Config,
):
    try:
        cmd_data = ChangeRoleCommand(
            target_id=target_id,
            target_role="BANNED",
            caller_dto=user_dto,
            notifier=notifier,
            bot_owner_id=config.ADMIN_ID,
        )
        if await ban_user(session, cmd_data, notify_user=False) is False:
            return

    except (ValueError, ValidationError):
        payload = MessagePayload(
            i18n_key="command_syntax_error",
            i18n_kwargs={"hint": html.code("Validation Error.")},
        )
        return await notifier.notify_user(user_dto, payload)


@router.message(I18nTextFilter("command_admin_stats"))
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
