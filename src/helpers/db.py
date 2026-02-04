

from typing import Sequence
from database.models import Suggestion, UserAlchemy

from aiogram.types import User as UserTelegram
from sqlalchemy import select, Result, func
from sqlalchemy.ext.asyncio import AsyncSession

# Все хелперы выполняются уже после
# async with session.begin():
# TODO: REDIS


async def get_or_create_user(
    session: AsyncSession, user_tg: UserTelegram
) -> UserAlchemy:
    user_alchemy = await session.scalar(
        select(UserAlchemy).where(UserAlchemy.user_id == user_tg.id)
    )
    if not user_alchemy:
        user_alchemy = UserAlchemy(user_id=user_tg.id, username=user_tg.username)
    user_alchemy = await session.merge(user_alchemy)
    return user_alchemy


async def get_last_suggestions(
    session: AsyncSession, user_id: int, limit: int = 5
) -> Sequence[Suggestion]:
    stmt = (
        select(Suggestion)
        .where(Suggestion.author_id == user_id)
        .order_by(Suggestion.id.desc())
        .limit(limit)
    )
    result: Result = await session.execute(stmt)
    return result.scalars().all()


async def get_suggestions_count(session: AsyncSession, user_id: int) -> int:
    stmt = (
        select(func.count(Suggestion.id))
        .select_from(Suggestion)
        .where(Suggestion.author_id == user_id)
    )
    user_suggestions_count = await session.scalar(stmt)
    return user_suggestions_count or 0
