from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import CallbackQuery, Message, TelegramObject
from dishka import AsyncContainer
from loguru import logger

from core.consts import DISHKA_CONTAINER_KEY
from database.dto import UserProfileDTO
from interfaces import MessageNotifierProtocol

from .base import KitaMiddleware


class AdminMiddleware(KitaMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        profile_dto: UserProfileDTO = data.get("profile_dto")
        if profile_dto and profile_dto.is_admin:
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            await event.answer()

        container: AsyncContainer = data.get(DISHKA_CONTAINER_KEY)
        notifier = await container.get(MessageNotifierProtocol)

        try:
            await notifier.send_text(event.from_user.id, "warning_not_enough_permission")
        except Exception:
            logger.exception("Failed to send permission warning to user {}", event.from_user.id)
