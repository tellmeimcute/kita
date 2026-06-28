from logging import getLogger
from typing import Any, Awaitable, Callable, Dict

from aiogram.types import CallbackQuery, Message, TelegramObject

from database.dto import UserDTO
from .base import KitaMiddleware

logger = getLogger("kita.ban_middleware")


class BanCheckMiddleware(KitaMiddleware):

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        user_dto: UserDTO = data.get("user_dto")

        if user_dto and not user_dto.is_banned:
            return await handler(event, data)

        logger.debug("Stop banned user")
        if isinstance(event, CallbackQuery):
            await event.answer()
