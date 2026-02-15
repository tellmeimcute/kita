from logging import getLogger

from aiogram import Router, html
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import UserAlchemyDAO
from database.dto import UserDTO
from database.roles import UserRole
from handlers.keyboards import get_main_kb_by_role
from helpers.message_payload import MessagePayload
from services.notifier import Notifier

logger = getLogger(name="admin_role_change")
router = Router()


class ChangeRoleCommand(BaseModel):
    user_id: int
    role: UserRole


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
        raw_user_id, raw_role = command.args.split(maxsplit=1)
        cmd_data = ChangeRoleCommand(user_id=raw_user_id, role=raw_role)
    except (ValueError, ValidationError):
        payload = MessagePayload(
            i18n_key="command_syntax_error",
            i18n_kwargs={
                "hint": html.code("Validation Error. ROLE not exist or not valid USERID")
            },
        )
        return await notifier.notify_user(user_dto, payload)

    if cmd_data.user_id == config.ADMIN_ID:
        payload = MessagePayload(i18n_key="error_user_immune")
        return await notifier.notify_user(user_dto, payload)

    try:
        async with session.begin():
            target_orm = await UserAlchemyDAO.change_role(session, cmd_data.user_id, cmd_data.role)
            target_dto = UserDTO.model_validate(target_orm)
    except KeyError:
        i18n_kwargs = {"user_id": cmd_data.user_id}
        payload = MessagePayload(i18n_key="user_not_found", i18n_kwargs=i18n_kwargs)
        return await notifier.notify_user(user_dto, payload)
    except Exception as e:
        return logger.error(e)

    # Уведомление админа, роль успешно поменяна
    i18n_kwargs = {
        "username": target_dto.username,
        "user_id": target_dto.user_id,
        "role": target_dto.role,
    }
    payload = MessagePayload(i18n_key="answer_admin_role_changed", i18n_kwargs=i18n_kwargs)
    await notifier.notify_user(user_dto, payload)

    # Уведомление юзера что ему поменяли роль
    kb = get_main_kb_by_role(cmd_data.role)
    i18n_kwargs = {"role": cmd_data.role}
    payload = MessagePayload(
        i18n_key="notify_user_role_changed", i18n_kwargs=i18n_kwargs, reply_markup=kb
    )
    await notifier.notify_user(target_dto, payload)

    admin = message.from_user
    logger.info(
        "%s (%s) изменил роль пользователю %s (%s) на %s",
        admin.username,
        admin.id,
        target_dto.username,
        target_dto.user_id,
        cmd_data.role,
    )
