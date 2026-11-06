from aiogram import Bot
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from dishka import Provider, Scope, provide

from core.config import Config
from core.userbot_dispatcher import UserbotDispatcherState
from database.dto import UserBotDTO
from interfaces import (
    BotContextProtocol,
    BotResolverProtocol,
    BotSessionProtocol,
    UnitOfWorkProtocol,
    UserBotServiceProtocol,
)
from services.bots import BotCache, BotContext, BotResolver, BotSessionFactory
from usecases.ub_token_resolver import UserBotTokenResolver


class BotProvider(Provider):
    scope = Scope.REQUEST

    ub_token_resolver = provide(UserBotTokenResolver, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def userbot_dispatcher_state(self) -> UserbotDispatcherState:
        return UserbotDispatcherState()

    @provide(scope=Scope.APP)
    def bot_cache(self, config: Config) -> BotCache:
        return BotCache(config.bot_cache_max_size)

    @provide(scope=Scope.APP)
    def bot_sessions(
        self,
        config: Config,
        request_middlewares: list[BaseRequestMiddleware],
    ) -> BotSessionProtocol:
        return BotSessionFactory(config, request_middlewares)

    @provide(scope=Scope.APP)
    def bot_context(self) -> BotContextProtocol:
        return BotContext()

    @provide(scope=Scope.APP)
    def bot_resolver(
        self,
        sessions: BotSessionProtocol,
        cache: BotCache,
        context: BotContextProtocol,
    ) -> BotResolverProtocol:
        return BotResolver(sessions, cache, context)

    @provide
    def get_bot(self, context: BotContextProtocol) -> Bot:
        bot = context.get_current()
        if bot is not None:
            return bot
        raise ValueError("No Bot available in current context")

    @provide
    async def userbot(
        self,
        uow: UnitOfWorkProtocol,
        userbot_service: UserBotServiceProtocol,
        bot: Bot,
    ) -> UserBotDTO:
        async with uow.transaction():
            return await userbot_service.get(bot.id)
