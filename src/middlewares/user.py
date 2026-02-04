from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from sqlalchemy.ext.asyncio import AsyncSession
from database.models.user import UserAlchemy
from aiogram.types import User as UserTelegram

from helpers.db import get_or_create_user


class UserMiddleware(BaseMiddleware):
    """
    ВЫДАЕТ UserAlchemy В ХЕНДЛЕРЫ
    data["user_alchemy"]
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

        async with session.begin():
            user_alchemy: UserAlchemy = await get_or_create_user(session, user_tg)

        data["user_alchemy"] = user_alchemy
        return await handler(event, data)
