from sqlalchemy.ext.asyncio import AsyncSession

from interfaces import BotRegistryProtocol
from interfaces.mixins import BotMixin


class BaseRepository(BotMixin):
    __slots__ = ("_session",)

    def __init__(
        self,
        session: AsyncSession,
        bot_registry: BotRegistryProtocol,
    ):
        super().__init__(bot_registry)
        self._session = session
