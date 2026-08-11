from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import CallbackQuery, Message, TelegramObject
from loguru import logger

from database.dto import UserProfileDTO

from .base import KitaMiddleware


class BanCheckMiddleware(KitaMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        profile_dto: UserProfileDTO = data.get("profile_dto")

        if profile_dto and not profile_dto.is_banned:
            return await handler(event, data)

        logger.debug("Stop banned user")
        if isinstance(event, CallbackQuery):
            await event.answer()
