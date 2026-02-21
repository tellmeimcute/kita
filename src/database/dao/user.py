from typing import Sequence

from aiogram.types import User as UserTelegram

from sqlalchemy import Result, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao.base import BaseDao
from database.models import Suggestion, UserAlchemy
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
        user_tg: UserTelegram,
        role: UserRole,
    ):
        user_alchemy = await cls.get_one_or_none_by_id(session, user_tg.id)

        if not user_alchemy:
            user_alchemy = await cls.create(
                session, 
                user_id=user_tg.id, 
                username=user_tg.username, 
                name=user_tg.full_name, 
                role=role,
            )
        return user_alchemy

    @classmethod
    async def update_by_id(cls, session: AsyncSession, data_id: int, data: dict):
        stmt = update(cls.model).where(cls.model.user_id == data_id).values(data)
        await session.execute(stmt)
        await session.flush()

    @classmethod
    async def get_admins(cls, session: AsyncSession) -> Sequence[UserAlchemy]:
        return await cls.get(session, UserAlchemy.role == UserRole.ADMIN)

    @classmethod
    async def get_admins_count(cls, session: AsyncSession) -> int:
        return await cls.count(session, cls.model.role == UserRole.ADMIN)

    @classmethod
    async def get_banned(cls, session: AsyncSession) -> Sequence[UserAlchemy]:
        return await cls.get(session, UserAlchemy.role == UserRole.BANNED)

    @classmethod
    async def get_banned_count(cls, session: AsyncSession) -> int:
        return await cls.count(session, cls.model.role == UserRole.BANNED)

    @classmethod
    async def get_users_stats(
        cls,
        session: AsyncSession,
    ):
        stmt = select(
            func.count(cls.model.id).label("total"),
            func.count(cls.model.id).filter(cls.model.role == UserRole.ADMIN).label("admins"),
            func.count(cls.model.id).filter(cls.model.role == UserRole.BANNED).label("banned"),
        )
        result: Result = await session.execute(stmt)
        return result.one()

    @classmethod
    async def decline_all_suggestions(cls, session: AsyncSession, user_id: int):
        decline_suggestion = (
            update(Suggestion).where(Suggestion.author_id == user_id).values(accepted=False)
        )

        await session.execute(decline_suggestion)
        await session.flush()

    @classmethod
    async def change_role(cls, session: AsyncSession, user_id: int, role: UserRole | str):
        if isinstance(role, str):
            role = UserRole(role)

        target = await cls.get_one_or_none_by_id(session, user_id)
        if not target:
            raise KeyError("User not found")

        if role == UserRole.BANNED:
            await cls.decline_all_suggestions(session, user_id)

        target.role = role
        return target
