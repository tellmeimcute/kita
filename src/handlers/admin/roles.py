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

logger = getLogger(name="admin_role_change")
router = Router()


@router.message(Command("change_role"))
async def promote_user(
    message: Message, session: AsyncSession, command: CommandObject, config: Config
):
    if not command.args:
        return await message.answer("Укажите userid и role через пробел.\nНапример 000000 admin")

    user_id, role = command.args.split()

    if int(user_id) == config.ADMIN_ID:
        return await message.answer("Этому пользователю нельзя изменять роль.")

    try:
        async with session.begin():
            target = await UserAlchemyDAO.change_role(session, user_id, role)
        await message.answer(
            f"Пользователю {target.username} ({target.user_id}) изменена роль на {target.role}."
        )
    except ValueError:
        return await message.answer("Такой роли не существует.")
    except KeyError:
        return await message.answer(f"Пользователь с id {user_id} не найден.")
    except Exception as e:
        raise e

    await message.bot.send_message(
        user_id,
        f"🤡 Вам назначили роль {target.role}!",
        reply_markup=get_main_kb_by_role(target.role.value),
    )

    admin = message.from_user
    logger.info(
        "%s (%s) изменил роль пользователю %s (%s) на %s",
        admin.username,
        admin.id,
        target.username,
        target.user_id,
        role,
    )
