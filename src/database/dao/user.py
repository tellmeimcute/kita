
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao.base import BaseDao
from database.models import UserAlchemy
from database.roles import UserRole

class UserAlchemyDAO(BaseDao[UserAlchemy]):
    model = UserAlchemy

    @classmethod
    async def get_one_or_none_by_id(cls, session: AsyncSession, data_id: int):
        return await cls.get_one_or_none(session, filters=cls.model.user_id == data_id)
    
    @classmethod
    async def get_or_create_user(
        cls,
        session: AsyncSession,
        user_id: int,
        username: str,
        user_role: UserRole = UserRole.USER,
    ):
        user_alchemy = await cls.get_one_or_none_by_id(session, user_id)
        if not user_alchemy:
            user_alchemy = await cls.create(session, user_id=user_id, username=username, role=user_role)
        return user_alchemy