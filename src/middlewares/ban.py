from logging import getLogger
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from database.dto import UserDTO

logger = getLogger("kita.ban_middleware")


class BanCheckMiddleware(BaseMiddleware):
    """
    Не пропускает если пользователь в бане.
    data["user_dto"] уже должен существовать.
    Должен стоять после UserMiddleware (для дебилов)
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        user_dto: UserDTO = data.get("user_dto")
        if not user_dto or user_dto.is_banned:
            logger.debug("Stop banned user")
            return
        return await handler(event, data)
