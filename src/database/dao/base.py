from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import ColumnElement, Result, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, selectinload

from database.models.abstract_model import AbstractModel

T = TypeVar("T", bound=AbstractModel)


class BaseDao(Generic[T]):
    model: type[T]

    @classmethod
    def _build_select_query(
        cls,
        filters: ColumnElement[bool] | None = None,
        options: Sequence[Any] | None = None,
        order_by: Any = None,
    ):
        stmt = select(cls.model)

        if filters is not None:
            stmt = stmt.where(filters)
        if options is not None:
            stmt = stmt.options(*options)
        if order_by is not None:
            stmt = stmt.order_by(order_by)

        return stmt

    @classmethod
    async def get_result(
        cls,
        session: AsyncSession,
        filters: ColumnElement[bool] | None = None,
        options: Sequence[Any] | None = None,
        order_by: Any = None,
        offset: int = 0,
        limit: int | None = None,
    ) -> Result:
        stmt = cls._build_select_query(filters, options, order_by)
        stmt = stmt.offset(offset)

        if limit is not None:
            stmt = stmt.limit(limit)

        result: Result = await session.execute(stmt)
        return result

    @classmethod
    async def get_one_or_none(
        cls,
        session: AsyncSession,
        filters: ColumnElement[bool],
        options: Sequence[Any] | Any = None,
        order_by: Any = None,
    ) -> T | None:
        if options is None:
            opt_seq = ()
        elif isinstance(options, Sequence) and not isinstance(options, str):
            opt_seq = options
        else:
            opt_seq = (options,)

        processed_options = []
        for opt in opt_seq:
            if isinstance(opt, InstrumentedAttribute):
                processed_options.append(selectinload(opt))
            else:
                processed_options.append(opt)

        result = await cls.get_result(
            session,
            filters=filters,
            options=processed_options if processed_options else None,
            order_by=order_by,
            limit=1,
        )
        return result.scalars().first()

    @classmethod
    async def get_one_or_none_by_id(cls, session: AsyncSession, data_id: int) -> T | None:
        return await cls.get_one_or_none(session, filters=cls.model.id == data_id)

    @classmethod
    async def count(cls, session: AsyncSession, filters: ColumnElement[bool] | None = None) -> int:
        stmt = select(func.count(cls.model.id))
        if filters is not None:
            stmt = stmt.where(filters)

        count = await session.scalar(stmt)
        return count or 0

    @classmethod
    async def get(
        cls,
        session: AsyncSession,
        filters: ColumnElement[bool] | None = None,
        options: Sequence[Any] | None = None,
        order_by: Any = None,
        offset: int = 0,
        limit: int | None = None,
    ) -> Sequence[T]:
        result = await cls.get_result(session, filters, options, order_by, offset, limit)
        return result.scalars().all()

    @classmethod
    async def create_from_data(cls, session: AsyncSession, **data: Any) -> T:
        obj = cls.model(**data)
        session.add(obj)
        await session.flush()
        await session.refresh(obj)
        return obj

    @classmethod
    async def create(cls, session: AsyncSession, model: T) -> T:
        session.add(model)
        await session.flush()
        await session.refresh(model)
        return model

    @classmethod
    async def update_by_id(cls, session: AsyncSession, data_id: int, data: dict):
        stmt = update(cls.model).where(cls.model.id == data_id).values(data)

        await session.execute(stmt)
        await session.flush()
