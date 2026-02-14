from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.types import User as UserTelegram
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import UserAlchemyDAO
from database.dto import UserDTO
from database.models import UserAlchemy
from database.roles import UserRole


class UserMiddleware(BaseMiddleware):
    """
    ВЫДАЕТ UserAlchemy В ХЕНДЛЕРЫ
    data["user_alchemy"] ORM
    data["user_dto] DTO
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        session: AsyncSession | None = data.get("session")
        if not session:
            return await handler(event, data)

        user_tg: UserTelegram = None

        if isinstance(event, (Message, CallbackQuery)):
            user_tg = event.from_user

        if not user_tg:
            return await handler(event, data)

        config: Config = data["config"]

        user_role = UserRole.USER
        if user_tg.id == config.ADMIN_ID:
            user_role = UserRole.ADMIN

        async with session.begin():
            user_alchemy: UserAlchemy = await UserAlchemyDAO.get_or_create_user(
                session, user_tg.id, user_tg.username, user_role
            )

        user_dto = UserDTO.model_validate(user_alchemy)

        data["user_alchemy"] = user_alchemy
        data["user_dto"] = user_dto

        return await handler(event, data)
