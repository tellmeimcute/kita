from sqlalchemy.ext.asyncio import AsyncSession

from interfaces import BotRegistryProtocol


class BaseRepository:
    __slots__ = (
        "_session",
        "_bot_registry",
        "_bot",
    )

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
