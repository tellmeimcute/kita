from sqlalchemy.ext.asyncio import AsyncSession

from interfaces import BotRegistryProtocol


class BaseRepository:
    __slots__ = (
        "_session",
        "_bot_registry",
    )

    def __init__(
        self,
        session: AsyncSession,
        bot_registry: BotRegistryProtocol,
    ):
        self._session = session
        self._bot_registry = bot_registry

    @property
    def bot(self):
        return self._bot_registry.get_current()
