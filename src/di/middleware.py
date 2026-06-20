
from aiogram.utils.i18n import I18n
from dishka import Provider, Scope, provide
from redis.asyncio import Redis

from middlewares import (
    AdminMiddleware,
    BanCheckMiddleware,
    MediaGroupMiddleware,
    UserMiddleware,
    KitaI18nMiddleware,
    RateLimitMiddleware,
)

class MiddlewareProvider(Provider):
    user_middleware = provide(UserMiddleware, scope=Scope.APP)
    bancheck_middleware = provide(BanCheckMiddleware, scope=Scope.APP)
    admin_middleware = provide(AdminMiddleware, scope=Scope.APP)
    rate_limit_middleware = provide(RateLimitMiddleware, scope=Scope.APP)

    @provide(scope=Scope.APP)
    async def kita_i18n_middleware(self, i18n: I18n) -> KitaI18nMiddleware:
        return KitaI18nMiddleware(i18n=i18n)

    @provide(scope=Scope.APP)
    async def media_group_middleware(self, redis: Redis) -> MediaGroupMiddleware:
        return MediaGroupMiddleware(redis)