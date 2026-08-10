from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from database.models import UserBot


class UserBotTokenResolver:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self._session_maker = session_maker

    async def resolve(self, bot_id: int) -> str | None:
        async with self._session_maker() as session:
            return await session.scalar(select(UserBot.token).where(UserBot.bot_id == bot_id))
