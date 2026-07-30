
from typing import Sequence, Any

from sqlalchemy import select, update
from database.models import UserBot
from database.dto import UserBotDTO
from .base import BaseRepository


class UserBotRepository(BaseRepository):

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

    async def create(
        self,
        token: str,
        bot_id: int,
        username: str,
        owner_id: int,
        channel_id: int,
        channel_name: str,
    ):
        orm_model = UserBot(
            token=token,
            bot_id=bot_id,
            username=username,
            owner_id=owner_id,
            channel_id=channel_id,
            channel_name=channel_name,
        )

        self._session.add(orm_model)
        await self._session.flush()

    async def update(self, bot_id: int, **data: Any):
        stmt = (
            update(UserBot)
            .where(UserBot.bot_id == bot_id)
            .values(data)
        )
        await self._session.execute(stmt)

    async def save(self, dto: UserBotDTO):
        if changed := dto.prepare_changed_data():
            await self.update(dto.bot_id, **changed)