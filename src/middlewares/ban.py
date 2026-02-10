from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from database.models import UserAlchemy


class BanCheckMiddleware(BaseMiddleware):
    """
    Не пропускает если пользователь в бане.
    data["user_alchemy"] уже должен существовать.
    Должен стоять после UserMiddleware (для дебилов)
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        user_alchemy: UserAlchemy = data.get("user_alchemy")
        if not user_alchemy or user_alchemy.is_banned:
            return
        return await handler(event, data)
