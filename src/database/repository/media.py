
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Media
from interfaces import BotRegistryProtocol

class MediaRepository:
    
    def __init__(
        self,
        session: AsyncSession,
        bot_registry: BotRegistryProtocol,
    ):
        self._session = session
        self._current_bot = bot_registry.get_current()

    async def count(self) -> int:
        stmt = select(
            func.count(Media.id)
        ).where(Media.bot_id == self._current_bot.id)

        count = await self._session.scalar(stmt)
        return count or 0
