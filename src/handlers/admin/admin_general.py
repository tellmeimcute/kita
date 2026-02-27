from aiogram import Router, html
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import MediaDAO, SuggestionDAO, UserAlchemyDAO
from database.dto import UserDTO
from helpers.filters import I18nTextFilter, TextArgsFilter
from helpers.message_payload import MessagePayload
from helpers.schemas import ChangeRoleCommand, ChangeRoleData, IDCommand
from services import Notifier, UserService

router = Router()

@router.message(I18nTextFilter("command_post_banner"))
async def post_channel_banner(
    message: Message,
    user_dto: UserDTO,
    config: Config,
    notifier: Notifier,
):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Предложка", url=config.bot_url
    )

    payload = MessagePayload(i18n_key="channel_banner", reply_markup=builder.as_markup())
    await notifier.send_channel(config.CHANNEL_ID, payload)

    payload = MessagePayload(i18n_key="channel_banner_sent")
    await notifier.notify_user(user_dto, payload)


@router.message(TextArgsFilter("command_change_role", ChangeRoleCommand))
async def change_user_role(
    message: Message,
    user_dto: UserDTO,
    notifier: Notifier,
    command: ChangeRoleCommand,
    user_service: UserService,
):    
    try:
        cmd_data = ChangeRoleData(
            target_id=command.target_id,
            target_role=command.target_role,
            caller_dto=user_dto,
            notifier=notifier,
        )
        await user_service.change_role(cmd_data)
    except (ValueError, ValidationError):
        payload = MessagePayload(
            i18n_key="command_syntax_error",
            i18n_kwargs={"hint": html.code("COMMAND USERID[int] ROLE[str]")},
        )
        await notifier.notify_user(user_dto, payload)


@router.message(TextArgsFilter("command_ban_filter", IDCommand))
async def ban_user_handler(
    message: Message,
    user_dto: UserDTO,
    command: IDCommand,
    notifier: Notifier,
    user_service: UserService,
):
    try:
        cmd_data = ChangeRoleData(
            target_id=command.target_id,
            target_role="BANNED",
            caller_dto=user_dto,
            notifier=notifier,
        )
        await user_service.change_role(cmd_data, notify_user=False)
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
