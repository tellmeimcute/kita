from collections.abc import Awaitable, Callable
from logging import getLogger
from typing import Any

from aiogram.types import CallbackQuery, Message, TelegramObject
from dishka import AsyncContainer

from aiogram.utils.i18n import I18n

from core.consts import DISHKA_CONTAINER_KEY
from core.rate_limiters import TokenBucketLimiter
from core.i18n_translator import Translator

from database.dto import UserDTO

from .base import KitaMiddleware

logger = getLogger("kita.middleware")


class RateLimitMiddleware(KitaMiddleware):

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        user_dto: UserDTO = data.get("user_dto")
        if not user_dto or not event.from_user:
            return logger.warning("No user in event. Stop")

        container: AsyncContainer = data.get(DISHKA_CONTAINER_KEY)
        limiter: TokenBucketLimiter = await container.get(TokenBucketLimiter)

        res = await limiter.attempt(user_dto)

        if res.allowed:
            await limiter.unmark_warned(user_dto)
            return await handler(event, data)

        logger.info("RateLimiting UserID %s", user_dto.user_id)

        if await limiter.is_warned(user_dto):
            if isinstance(event, CallbackQuery):
                return await event.answer()
            return

        i18n: I18n = await container.get(I18n)
        translator: Translator = await container.get(Translator)
        
        with i18n.use_locale(user_dto.language_code):
            msg = translator.translate("rate_limited_warning")

        await limiter.mark_warned(user_dto)
        await event.answer(msg)
