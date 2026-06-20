
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Media

class MediaRepository:
    
    def __init__(self, session: AsyncSession):
        self._session = session

    async def count(self) -> int:
        stmt = select(func.count(Media.id))
        count = await self._session.scalar(stmt)
        return count or 0
