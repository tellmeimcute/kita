from logging import getLogger

from aiogram import Bot
from dishka import Provider, Scope, provide

from database.dto import UserBotDTO
from interfaces import BotRegistryProtocol, UnitOfWorkProtocol
from services import BotRegistry, UserBotService

logger = getLogger("kita.providers")


class BotProvider(Provider):
    scope = Scope.REQUEST

    bot_registry = provide(source=BotRegistry, provides=BotRegistryProtocol, scope=Scope.APP)

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
        userbot_service: UserBotService,
        bot: Bot,
    ) -> UserBotDTO:
        async with uow.transaction():
            return await userbot_service.get(bot.id)
