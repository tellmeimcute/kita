from logging import getLogger

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import UserAlchemyDAO
from database.models import UserAlchemy
from database.roles import UserRole
from database.dto import UserDTO
from handlers.keyboards import get_main_kb_by_role
from helpers.message_payload import MessagePayload
from services.notifier import Notifier

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
        return await message.answer("Укажите userid и role через пробел.\nНапример 000000 admin")

    user_id, role = command.args.split()

    if int(user_id) == config.ADMIN_ID:
        payload = MessagePayload(i18n_key="command_user_immune")
        return await notifier.notify_user(user_dto, payload)
    try:
        async with session.begin():
            target_orm = await UserAlchemyDAO.change_role(session, user_id, role)
            target_dto = UserDTO.model_validate(target_orm)

        i18n_kwargs = {
            "username": target_dto.username,
            "user_id": target_dto.user_id,
            "role": target_dto.role,
        }
        payload = MessagePayload(i18n_key="answer_admin_role_changed", i18n_kwargs=i18n_kwargs)
        await notifier.notify_user(user_dto, payload)
    except ValueError:
        i18n_kwargs = {"role": role}
        payload = MessagePayload(i18n_key="role_not_exist", i18n_kwargs=i18n_kwargs)
        return await notifier.notify_user(user_dto, payload)
    except KeyError:
        i18n_kwargs = {"user_id": user_id}
        payload = MessagePayload(i18n_key="user_not_found", i18n_kwargs=i18n_kwargs)
        return await notifier.notify_user(user_dto, payload)
    except Exception as e:
        return logger.error(e)
    
    kb = get_main_kb_by_role(role)
    i18n_kwargs = {"role": role}
    payload = MessagePayload(i18n_key="notify_user_role_changed", i18n_kwargs=i18n_kwargs, reply_markup=kb)
    await notifier.notify_user(target_dto, payload)

    admin = message.from_user
    logger.info(
        "%s (%s) изменил роль пользователю %s (%s) на %s",
        admin.username,
        admin.id,
        target_dto.username,
        target_dto.user_id,
        role,
    )
