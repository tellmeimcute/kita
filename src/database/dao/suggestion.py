from typing import Sequence

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

    @classmethod
    async def get_active_count(cls, session: AsyncSession) -> int:
        return await cls.count(session, cls.model.accepted.is_(None))

    @classmethod
    async def get_active(cls, session: AsyncSession, last: bool = False) -> Suggestion | None:
        """
        Возвращает первый в очереди не рассмотренный Suggestion.
        Если last=True, возвращает последний.
        """
        order_by = None if not last else Suggestion.id.desc()
        return await cls.get_one_or_none(
            session, Suggestion.accepted.is_(None), (Suggestion.media, Suggestion.author), order_by
        )

    @classmethod
    async def get_one_or_none_by_id(
        cls, session: AsyncSession, data_id: int, solo: bool = False
    ) -> Suggestion | None:
        children = (Suggestion.media, Suggestion.author) if not solo else None
        return await cls.get_one_or_none(session, Suggestion.id == data_id, children)
