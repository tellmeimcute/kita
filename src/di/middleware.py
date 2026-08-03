from aiogram.utils.i18n import I18n
from dishka import Provider, Scope, provide
from redis.asyncio import Redis

from database.redis import TgMessageRedis
from middlewares import (
    AdminMiddleware,
    BanCheckMiddleware,
    KitaI18nMiddleware,
    MediaGroupMiddleware,
    RateLimitMiddleware,
    UserMiddleware,
)


class MiddlewareProvider(Provider):
    scope = Scope.APP

    user_middleware = provide(UserMiddleware)
    bancheck_middleware = provide(BanCheckMiddleware)
    admin_middleware = provide(AdminMiddleware)
    rate_limit_middleware = provide(RateLimitMiddleware)

    @provide
    async def kita_i18n_middleware(self, i18n: I18n) -> KitaI18nMiddleware:
        return KitaI18nMiddleware(i18n=i18n)

    @provide
    async def media_group_middleware(
        self, redis: Redis, tg_message_redis: TgMessageRedis
    ) -> MediaGroupMiddleware:
        return MediaGroupMiddleware(redis=redis, tg_message_redis=tg_message_redis)
