



from abc import ABC

from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from interfaces import BotRegistryProtocol


class BaseRepository(ABC):

    def __init__(
        self,
        session: AsyncSession,
        bot_registry: BotRegistryProtocol,
    ):
        self._session = session
        self._bot_registry = bot_registry
        self._bot = None

    @property
    def bot(self):
        if self._bot:
            return self._bot
        return self._bot_registry.get_current()
    
    def assign_bot(self, bot: Bot):
        self._bot = bot
        