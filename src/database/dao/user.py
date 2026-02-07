
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao.base import BaseDao
from database.models import UserAlchemy


class UserAlchemyDAO(BaseDao[UserAlchemy]):
    model = UserAlchemy

    @classmethod
    async def get_one_or_none_by_id(cls, session: AsyncSession, data_id: int):
        return await session.scalar(
            select(cls.model).where(cls.model.user_id == data_id)
        )
    
    @classmethod
    async def get_or_create_user(cls, session: AsyncSession, user_id: int, username: str):
        user_alchemy = await cls.get_one_or_none_by_id(session, user_id)

        if not user_alchemy:
            user_alchemy = cls.model(user_id=user_id, username=username)
            user_alchemy = await session.merge(user_alchemy)

        return user_alchemy