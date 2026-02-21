from aiogram import Router, html
from aiogram.types import Message
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import MediaDAO, SuggestionDAO, UserAlchemyDAO
from database.dto import UserDTO
from helpers.filters import I18nTextFilter, TextArgsFilter
from helpers.message_payload import MessagePayload
from helpers.schemas import ChangeRoleCommand, ChangeRoleData, IDCommand
from helpers.utils import ban_user
from services.notifier import Notifier

router = Router()


@router.message(TextArgsFilter("command_change_role", ChangeRoleCommand))
async def change_user_role(
    message: Message,
    session: AsyncSession,
    user_dto: UserDTO,
    config: Config,
    notifier: Notifier,
    command: ChangeRoleCommand,
):    
    try:
        cmd_data = ChangeRoleData(
            target_id=command.target_id,
            target_role=command.target_role,
            caller_dto=user_dto,
            notifier=notifier,
            bot_owner_id=config.ADMIN_ID,
        )
        await ban_user(session, cmd_data)
    except (ValueError, ValidationError):
        payload = MessagePayload(
            i18n_key="command_syntax_error",
            i18n_kwargs={"hint": html.code("COMMAND USERID[int] ROLE[str]")},
        )
        await notifier.notify_user(user_dto, payload)


@router.message(TextArgsFilter("command_ban_filter", IDCommand))
async def ban_user_handler(
    message: Message,
    session: AsyncSession,
    user_dto: UserDTO,
    command: IDCommand,
    notifier: Notifier,
    config: Config,
):
    try:
        cmd_data = ChangeRoleData(
            target_id=command.target_id,
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
async def global_stats_handler(
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
