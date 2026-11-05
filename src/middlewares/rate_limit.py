from abc import ABC
from collections.abc import Awaitable, Callable
from math import ceil
from typing import Any, ClassVar

from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.utils.i18n import I18n
from loguru import logger
from redis.asyncio import Redis

from core.config import Config
from core.i18n_translator import Translator
from core.rate_limiters import UserLimiter
from database.dto import UserDTO
from interfaces import BotRegistryProtocol

from .base import KitaMiddleware


class RateLimitMiddleware(KitaMiddleware):
    _scope: ClassVar[str] = "tg_update"

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

        self.limiter = UserLimiter(
            redis=redis,
            bot_registry=bot_registry,
            scope=self._scope,
            max_tokens=config.user_rate_limit.max_tokens,
            refill_rate=config.user_rate_limit.refill_rate,
        )

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        user_dto: UserDTO = data.get("user_dto")
        if not user_dto or not event.from_user:
            return logger.warning("No user in event. Stop")

        res = await self.limiter.attempt(user_dto)

        if res.allowed:
            return await handler(event, data)

        if res.paused:
            if isinstance(event, CallbackQuery):
                return await event.answer()
            return None

        logger.info("RateLimiting UserID {}", user_dto.user_id)

        # BUCKET_SCRIPT already wrote the pause; wait_ms is the full pause
        # duration this caller has to report.
        pause_for = ceil(res.wait_ms / 1000)

        with self.i18n.use_locale(user_dto.language_code):
            msg = self.translator.i18n_text("rate_limited_warning", {"pause_for": pause_for})

        await event.answer(msg)


class BaseWidgetRateLimit(RateLimitMiddleware, ABC):
    _scope: ClassVar[str]
    _unlimited_widget_ids: ClassVar[set]

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


class UserBotRateLimitMiddleware(BaseWidgetRateLimit):
    _scope: ClassVar[str] = "userbot_action"
    _unlimited_widget_ids: ClassVar[set] = {"main_menu", "userbot_select_group"}

    def __init__(
        self,
        redis: Redis,
        bot_registry: BotRegistryProtocol,
        i18n: I18n,
        translator: Translator,
    ):
        self.i18n = i18n
        self.translator = translator

        self.limiter = UserLimiter(
            redis=redis,
            bot_registry=bot_registry,
            scope=self._scope,
            max_tokens=3,
            refill_rate=0.05,
        )
