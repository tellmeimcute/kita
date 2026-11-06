from sqlalchemy.ext.asyncio import AsyncSession

from interfaces import BotContextProtocol
from interfaces.mixins import BotMixin


class BaseRepository(BotMixin):
    __slots__ = ("_session",)

    def __init__(
        self,
        session: AsyncSession,
        bot_context: BotContextProtocol,
    ):
        super().__init__(bot_context)
        self._session = session
