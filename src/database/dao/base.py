
from typing import Sequence, Generic, TypeVar, Any

from sqlalchemy import select, Result, func, ColumnElement
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.abstract_model import AbstractModel

T = TypeVar("T", bound=AbstractModel)

class BaseDao(Generic[T]):
    model: type[T]

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
        stmt = (
            select(cls.model)
            .where(filters)
            .order_by(order_by)
            .offset(offset)
            .limit(limit)
        )

        result: Result = await session.execute(stmt)
        return result.scalars().all()
    
    @classmethod
    async def get_one_or_none_with_children(
        cls, session: AsyncSession, child: Any, filters: ColumnElement[bool]
    ) -> T | None:
        stmt = (
            select(cls.model)
            .options(
                selectinload(child)
            )
            .where(filters)
        )

        result: Result = await session.execute(stmt)
        return result.scalar_one_or_none()