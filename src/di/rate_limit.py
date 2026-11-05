from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from dishka import Provider, Scope, provide
from redis.asyncio import Redis

from core.config import Config
from core.rate_limiters import (
    LogApiErrors,
    PaceRequests,
    RetryFloodControl,
    TgApiLimiter,
)


class RateLimitProvider(Provider):
    def __init__(self, *, pace: bool):
        super().__init__()
        self._pace = pace

    @provide(scope=Scope.APP)
    def tg_api_limiter(self, redis: Redis, config: Config) -> TgApiLimiter:
        api = config.api_rate_limit
        return TgApiLimiter(
            redis,
            rate=api.rate,
            burst=api.burst,
            chat_rate=api.chat_rate,
            chat_burst=api.chat_burst,
        )

    @provide(scope=Scope.APP)
    def api_request_middlewares(
        self, config: Config, limiter: TgApiLimiter
    ) -> list[BaseRequestMiddleware]:
        api = config.api_rate_limit
        middlewares: list[BaseRequestMiddleware] = [
            LogApiErrors(),
            RetryFloodControl(max_retries=api.flood_retries),
        ]
        if self._pace and api.enabled:
            middlewares.append(PaceRequests(limiter))
        return middlewares
