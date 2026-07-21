
from logging import getLogger
from dishka import Provider, Scope, provide

from aiogram import Bot

from interfaces import BotRegistryProtocol
from services import BotRegistry

logger = getLogger("kita.providers")

class BotProvider(Provider):
    bot_registry = provide(source=BotRegistry, provides=BotRegistryProtocol, scope=Scope.APP)

    @provide(scope=Scope.REQUEST)
    def get_bot(self, registry: BotRegistryProtocol) -> Bot:
        bot = registry.get_current()
        if bot is not None:
            return bot
        raise ValueError("No Bot available in current context")
