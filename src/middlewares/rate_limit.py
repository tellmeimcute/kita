from collections.abc import Awaitable, Callable
from logging import getLogger
from typing import Any

from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.utils.i18n import I18n
from redis.asyncio import Redis

from core.config import Config
from core.i18n_translator import Translator
from core.rate_limiters import TokenBucketLimiter
from database.dto import UserDTO
from interfaces import BotRegistryProtocol

from .base import KitaMiddleware

logger = getLogger("kita.middleware")


class RateLimitMiddleware(KitaMiddleware):
    _attemp_action: str = "TG_UPDATE"
    _warn_key: str = "WARNED"

    def __init__(
        self,
        redis: Redis,
        config: Config,
        bot_registry: BotRegistryProtocol,
        i18n: I18n,
        translator: Translator,
    ):
        self.i18n = i18n
        self.translator = translator

        self.limiter = TokenBucketLimiter(redis, bot_registry, **config.rate_limit.model_dump())

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        user_dto: UserDTO = data.get("user_dto")
        if not user_dto or not event.from_user:
            return logger.warning("No user in event. Stop")

        res = await self.limiter.attempt(user_dto, self._attemp_action)

        if res.allowed:
            await self.limiter.unmark_warned(user_dto, self._warn_key)
            return await handler(event, data)

        logger.info("RateLimiting UserID %s", user_dto.user_id)

        if await self.limiter.is_warned(user_dto, self._warn_key):
            if isinstance(event, CallbackQuery):
                return await event.answer()
            return None

        with self.i18n.use_locale(user_dto.language_code):
            msg = self.translator.translate("rate_limited_warning")

        await self.limiter.mark_warned(user_dto, self._warn_key)
        await event.answer(msg)


class WidgetRateLimit(RateLimitMiddleware):
    _unlimited_widget_ids: set = frozenset()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, CallbackQuery) and event.data:
            callback_data = event.data.split("\x1d")[-1]
            widget_id = callback_data.split(":", maxsplit=1)[0]
            if widget_id in self._unlimited_widget_ids:
                return await handler(event, data)
        return await super().__call__(handler, event, data)


class UserBotRateLimitMiddleware(WidgetRateLimit):
    _attemp_action: str = "USERBOT_ACTION"
    _warn_key: str = "USERBOT_WARNED"
    _unlimited_widget_ids = {"main_menu", "userbot_select_group"}

    def __init__(
        self,
        redis: Redis,
        bot_registry: BotRegistryProtocol,
        i18n: I18n,
        translator: Translator,
    ):
        self.i18n = i18n
        self.translator = translator

        self.limiter = TokenBucketLimiter(
            redis,
            bot_registry,
            max_tokens=4,
            refill_rate=0.05,
        )
