
from logging import getLogger

from aiogram import Bot
from dishka import Provider, Scope, provide
from database.dto import UserBotDTO
from interfaces import BotRegistryProtocol, UnitOfWorkProtocol
from services import BotRegistry, UserBotService

logger = getLogger("kita.providers")

class BotProvider(Provider):
    bot_registry = provide(source=BotRegistry, provides=BotRegistryProtocol, scope=Scope.APP)

    @provide(scope=Scope.REQUEST)
    def get_bot(self, registry: BotRegistryProtocol) -> Bot:
        bot = registry.get_current()
        if bot is not None:
            return bot
        raise ValueError("No Bot available in current context")


    @provide(scope=Scope.REQUEST)
    async def userbot(
        self,
        uow: UnitOfWorkProtocol,
        userbot_service: UserBotService,
        bot: Bot,
    ) -> UserBotDTO:
        async with uow.transaction():
            userbot = await userbot_service.get(bot.id)
        return userbot
