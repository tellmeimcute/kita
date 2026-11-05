import asyncio

from aiogram import Bot
from aiogram.client.session.middlewares.base import (
    BaseRequestMiddleware,
    NextRequestMiddlewareType,
)
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.methods import TelegramMethod
from aiogram.methods.base import Response, TelegramType
from loguru import logger

from .tg_api import TgApiLimiter, chat_id_of, message_cost

MIN_RETRY_DELAY = 1.0


class LogApiErrors(BaseRequestMiddleware):
    """Sits outermost: logs the failure the inner chain gave up on."""

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        try:
            return await make_request(bot, method)
        except TelegramRetryAfter:
            raise
        except TelegramAPIError:
            logger.error("API call {} failed for bot id={}", type(method).__name__, bot.id)
            raise


class RetryFloodControl(BaseRequestMiddleware):
    """Retries a 429 after Telegram's own ``retry_after``"""

    def __init__(self, *, max_retries: int):
        self._max_retries = max_retries

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        for attempt in range(self._max_retries + 1):
            try:
                return await make_request(bot, method)
            except TelegramRetryAfter as exc:
                if attempt == self._max_retries:
                    logger.error(
                        "Flood control on {} gave up after {} retries",
                        type(method).__name__,
                        self._max_retries,
                    )
                    raise

                delay = max(float(exc.retry_after), MIN_RETRY_DELAY)
                logger.warning(
                    "Flood control on {} for bot id={}, retrying in {:.1f}s",
                    type(method).__name__,
                    bot.id,
                    delay,
                )
                await asyncio.sleep(delay)


class PaceRequests(BaseRequestMiddleware):
    """Sleeps until the slot reserved by the GCRA limiter, then sends."""

    def __init__(self, limiter: TgApiLimiter):
        self._limiter = limiter

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        cost = message_cost(method)
        if cost:
            wait = await self._limiter.reserve(bot.id, cost=cost, chat_id=chat_id_of(method))
            if wait > 0:
                logger.debug(
                    "Pacing {} for bot id={} by {:.2f}s",
                    type(method).__name__,
                    bot.id,
                    wait,
                )
                await asyncio.sleep(wait)

        return await make_request(bot, method)
