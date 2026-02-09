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

    async with session.begin():
        user_to_promote: UserAlchemy = await UserAlchemyDAO.get_one_or_none_by_id(session, user_id)

    if user_to_promote is None:
        return message.answer(f"Пользователь с id {command.args} не найден.")

    try:
        role = UserRole(role)
    except ValueError:
        return await message.answer("Такой роли не существует.")

    async with session.begin():
        await UserAlchemyDAO.update_by_id(session, user_id, {"role": role})

    await message.answer(
        f"Пользователю {user_to_promote.username} ({user_to_promote.user_id}) изменена роль на {role.value}."
    )

    await message.bot.send_message(
        user_id,
        f"🤡 Вам назначили роль {role.value}!",
        reply_markup=get_main_kb_by_role(role)
    )

    admin = message.from_user
    logger.info(
        "%s (%s) изменил роль пользователю %s (%s) на %s",
        admin.username,
        admin.id,
        user_to_promote.username,
        user_to_promote.user_id,
        role,
    )
