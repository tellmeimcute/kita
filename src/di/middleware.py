
from aiogram.utils.i18n import I18n
from dishka import Provider, Scope, provide
from redis.asyncio import Redis

from middlewares import (
    AdminMiddleware,
    BanCheckMiddleware,
    MediaGroupMiddleware,
    SessionMiddleware,
    UserMiddleware,
    KitaI18nMiddleware,
)

class MiddlewareProvider(Provider):
    session_middleware = provide(SessionMiddleware, scope=Scope.APP)
    user_middleware = provide(UserMiddleware, scope=Scope.APP)
    bancheck_middleware = provide(BanCheckMiddleware, scope=Scope.APP)
    admin_middleware = provide(AdminMiddleware, scope=Scope.APP)

    @provide(scope=Scope.APP)
    async def kita_i18n_middleware(self, i18n: I18n) -> KitaI18nMiddleware:
        return KitaI18nMiddleware(i18n=i18n)

    @provide(scope=Scope.APP)
    async def media_group_middleware(self, redis: Redis) -> MediaGroupMiddleware:
        return MediaGroupMiddleware(redis)