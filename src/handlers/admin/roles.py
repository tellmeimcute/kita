from logging import getLogger

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import UserAlchemyDAO
from database.models import UserAlchemy
from database.roles import UserRole
from handlers.keyboards import get_main_kb_by_role
from services.notifier import Notifier

logger = getLogger(name="admin_role_change")
router = Router()


@router.message(Command("change_role"))
async def change_user_role(
    message: Message,
    session: AsyncSession,
    command: CommandObject,
    config: Config,
    notifier: Notifier,
):
    caller_id = message.from_user.id
    if not command.args:
        return await message.answer("Укажите userid и role через пробел.\nНапример 000000 admin")

    user_id, role = command.args.split()

    if int(user_id) == config.ADMIN_ID:
        return await notifier.answer_admin_user_immune(caller_id)

    try:
        async with session.begin():
            target = await UserAlchemyDAO.change_role(session, user_id, role)
        await notifier.answer_admin_user_role_changed(
            caller_id, target.username, target.user_id, target.role
        )
    except ValueError:
        return await notifier.answer_admin_role_not_exist(caller_id)
    except KeyError:
        return await notifier.answer_admin_user_not_found(caller_id, user_id)
    except Exception as e:
        raise e

    await notifier.notify_user_role_changed(target.user_id, target.role)

    admin = message.from_user
    logger.info(
        "%s (%s) изменил роль пользователю %s (%s) на %s",
        admin.username,
        admin.id,
        target.username,
        target.user_id,
        role,
    )
