from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.models import Media, Suggestion, UserAlchemy, UserProfile


class HasSessionMaker(Protocol):
    session_maker: async_sessionmaker[AsyncSession]


async def load_suggestion(db: HasSessionMaker, suggestion_id: int) -> Suggestion | None:
    async with db.session_maker() as session:
        return await session.get(Suggestion, suggestion_id)


async def count_suggestions(db: HasSessionMaker) -> int:
    async with db.session_maker() as session:
        return await session.scalar(select(func.count(Suggestion.id))) or 0


async def count_media(db: HasSessionMaker, suggestion_id: int) -> int:
    async with db.session_maker() as session:
        count = await session.scalar(
            select(func.count(Media.id)).where(Media.suggestion_id == suggestion_id)
        )
    return count or 0


async def load_user(db: HasSessionMaker, user_id: int) -> UserAlchemy | None:
    async with db.session_maker() as session:
        return await session.scalar(select(UserAlchemy).where(UserAlchemy.user_id == user_id))


async def load_profile(db: HasSessionMaker, user_id: int) -> UserProfile | None:
    async with db.session_maker() as session:
        return await session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
