from sqlalchemy import func, select

from database.models import Media

from .base import BaseRepository


class MediaRepository(BaseRepository):
    __slots__ = ()

    async def count(self) -> int:
        stmt = select(func.count(Media.id)).where(Media.bot_id == self.bot.id)

        count = await self._session.scalar(stmt)
        return count or 0
