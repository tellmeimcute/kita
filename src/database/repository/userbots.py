
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import UserBot
from database.dto import UserBotDTO

class UserBotRepository:

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, bot_id: int) -> UserBotDTO | None:
        stmt = (
            select(UserBot)
            .where(UserBot.bot_id == bot_id)
        )
        result = await self._session.execute(stmt)
        orm_model = result.scalar()
        if not orm_model:
            return None
        return UserBotDTO.model_validate(orm_model)

    async def get_active(self) -> Sequence[UserBotDTO]:
        stmt = (
            select(UserBot)
            .where(UserBot.active.is_(True))
        )
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()
        return UserBotDTO.from_model_list(orm_models)
