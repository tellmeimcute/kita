from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from database.models import UserAlchemy
from database.roles import UserRole



class AdminMiddleware(BaseMiddleware):
    """
    Пропускает дальше только если пользователь админ.
    data["user_alchemy"] уже должен существовать
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        user_alchemy: UserAlchemy = data.get("user_alchemy")
        if not user_alchemy or user_alchemy.role != UserRole.ADMIN:
            return
        return await handler(event, data)
