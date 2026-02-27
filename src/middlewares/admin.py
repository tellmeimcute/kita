from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from database.models import UserAlchemy


class AdminMiddleware(BaseMiddleware):
    """
    Пропускает дальше только если пользователь админ.
    data["user_dto"] уже должен существовать.
    Должен стоять после UserMiddleware (для дебилов)
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        user_dto: UserAlchemy = data.get("user_dto")
        if not user_dto or not user_dto.is_admin:
            return
        return await handler(event, data)
