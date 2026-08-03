from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import CallbackQuery, Message, TelegramObject
from dishka import AsyncContainer

from core.consts import DISHKA_CONTAINER_KEY
from core.i18n_translator import Translator
from core.schemas.message_payload import MessagePayload
from database.dto import UserProfileDTO
from ui.senders.payload import TextSender

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
        translator = await container.get(Translator)

        payload = MessagePayload(i18n_key="warning_not_enough_permission")
        strategy = TextSender(
            bot=event.bot,
            target_id=event.from_user.id,
            payload=payload,
            translator=translator,
        )
        await strategy.send()
