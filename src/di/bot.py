from aiogram import Bot
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from dishka import Provider, Scope, provide

from core.config import Config
from database.dto import UserBotDTO
from interfaces import BotRegistryProtocol, UnitOfWorkProtocol, UserBotServiceProtocol
from services import BotRegistry
from usecases.ub_token_resolver import UserBotTokenResolver


class BotProvider(Provider):
    scope = Scope.REQUEST

    ub_token_resolver = provide(UserBotTokenResolver, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def bot_registry(
        self,
        config: Config,
        request_middlewares: list[BaseRequestMiddleware],
    ) -> BotRegistryProtocol:
        return BotRegistry(config, request_middlewares)

    @provide
    def get_bot(self, registry: BotRegistryProtocol) -> Bot:
        bot = registry.get_current()
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
