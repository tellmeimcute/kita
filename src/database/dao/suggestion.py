from sqlalchemy import Result, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao.base import BaseDao
from database.models import Suggestion


class SuggestionDAO(BaseDao[Suggestion]):
    model = Suggestion

    @classmethod
    async def get_stats_by_user_id(
        cls,
        session: AsyncSession,
        user_id: int,
    ):
        stmt = select(
            func.count(cls.model.id).label("total"),
            func.count(cls.model.id).filter(cls.model.accepted == True).label("accepted"),
            func.count(cls.model.id).filter(cls.model.accepted == False).label("declined"),
        ).where(cls.model.author_id == user_id)

        result: Result = await session.execute(stmt)
        return result.one()
