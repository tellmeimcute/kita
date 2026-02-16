from logging import getLogger

from aiogram import Router, html
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dto import UserDTO
from helpers.schemas import ChangeRoleCommand
from helpers.message_payload import MessagePayload
from services.notifier import Notifier

from helpers.utils import ban_user

logger = getLogger(name="admin_role_change")
router = Router()


@router.message(Command("change_role"))
async def change_user_role(
    message: Message,
    session: AsyncSession,
    user_dto: UserDTO,
    command: CommandObject,
    config: Config,
    notifier: Notifier,
):
    if not command.args:
        payload = MessagePayload(
            i18n_key="command_syntax_error",
            i18n_kwargs={"hint": html.code("/change_role USERID ROLE")},
        )      
        return await notifier.notify_user(user_dto, payload)
    
    try:
        raw_target_id, raw_target_role = command.args.split(maxsplit=1)
        cmd_data = ChangeRoleCommand(
            target_id=raw_target_id,
            target_role=raw_target_role.upper(),
            caller_dto=user_dto,
            notifier=notifier,
            bot_owner_id=config.ADMIN_ID,
        )
        await ban_user(session, cmd_data)
    except (ValueError, ValidationError):
        payload = MessagePayload(
            i18n_key="command_syntax_error",
            i18n_kwargs={"hint": html.code("Maybe ROLE not exists.")},
        )
        await notifier.notify_user(user_dto, payload)