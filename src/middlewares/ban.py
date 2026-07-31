from logging import getLogger
from typing import Any, Awaitable, Callable, Dict

from aiogram.types import CallbackQuery, Message, TelegramObject

from database.dto import UserProfileDTO

from .base import KitaMiddleware

logger = getLogger("kita.ban_middleware")


class BanCheckMiddleware(KitaMiddleware):

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        profile_dto: UserProfileDTO = data.get("profile_dto")

        if profile_dto and not profile_dto.is_banned:
            return await handler(event, data)

        logger.debug("Stop banned user")
        if isinstance(event, CallbackQuery):
            await event.answer()
