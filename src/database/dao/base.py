
from typing import Sequence, Generic, TypeVar, Any

from sqlalchemy import select, Result, func, ColumnElement
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.abstract_model import AbstractModel

T = TypeVar("T", bound=AbstractModel)

class BaseDao(Generic[T]):
    model: type[T]

    @classmethod
    async def get_result(
        cls,
        session: AsyncSession,
        filters: ColumnElement[bool] | None = None,
        options: Sequence[Any] | None = None,
        order_by: Any = None,
        offset: int = 0,
        limit: int = 5
    ) -> Result:
        
        stmt = (
            select(cls.model)
            .where(filters)
            .offset(offset)
            .limit(limit)
            .order_by(order_by)
        )

        if options:
            stmt = stmt.options(*options)

        result: Result = await session.execute(stmt)
        return result

    @classmethod
    async def get_one_or_none(
        cls, 
        session: AsyncSession,
        filters: ColumnElement[bool],
        children: Sequence[Any] | Any = None,
        order_by: Any = None
    ):
        options = None
        if not isinstance(children, Sequence):
            children = (children,)

        if children:
            options = (selectinload(child) for child in children)

        result: Result = await cls.get_result(session, filters, options, order_by, limit=1)
        return result.scalars().first()

    @classmethod
    async def get_one_or_none_by_id(cls, session: AsyncSession, data_id: int) -> T | None:
        return await session.scalar(
            select(cls.model).where(cls.model.id == data_id)
        )
    
    @classmethod
    async def count(cls, session: AsyncSession, filters: ColumnElement[bool] | None = None) -> int:
        stmt = (
            select(func.count(cls.model.id))
            .where(filters)
        )
        count = await session.scalar(stmt)
        return count or 0
    
    @classmethod
    async def get(
        cls,
        session: AsyncSession,
        filters: ColumnElement[bool] | None = None,
        order_by: Any = None,
        offset: int = 0,
        limit: int = 5
    ) -> Sequence[T]:
        result = await cls.get_result(session, filters, None, order_by, offset, limit)
        return result.scalars().all()