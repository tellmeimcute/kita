from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, literal, select, update
from sqlalchemy.dialects.postgresql import insert

from database.dto import UserBotDTO
from database.models import UserBot

from .base import BaseRepository


class UserBotRepository(BaseRepository):
    __slots__ = ()

    async def get(self, bot_id: int) -> UserBotDTO | None:
        stmt = select(UserBot).where(UserBot.bot_id == bot_id)
        result = await self._session.execute(stmt)
        orm_model = result.scalar()
        if not orm_model:
            return None
        return UserBotDTO.model_validate(orm_model)

    async def get_active(self) -> Sequence[UserBotDTO]:
        stmt = select(UserBot).where(UserBot.active.is_(True))
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()
        return UserBotDTO.from_model_list(orm_models)

    async def get_by_owner_id(self, owner_id: int) -> Sequence[UserBotDTO]:
        stmt = select(UserBot).where(UserBot.owner_id == owner_id)

        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()
        return UserBotDTO.from_model_list(orm_models)

    async def count_by_owner_id(self, owner_id: int) -> int:
        stmt = select(func.count(UserBot.id)).where(UserBot.owner_id == owner_id)
        count = await self._session.scalar(stmt)
        return count or 0

    async def create(
        self,
        token: str,
        bot_id: int,
        username: str,
        owner_id: int,
        channel_id: int,
        channel_name: str,
        *,
        max_per_owner: int | None = None,
    ) -> UserBotDTO | None:
        columns = UserBot.__table__.c
        values = {
            "token": token,
            "bot_id": bot_id,
            "username": username,
            "owner_id": owner_id,
            "channel_id": channel_id,
            "channel_name": channel_name,
        }

        source = select(
            *[literal(value, type_=columns[name].type) for name, value in values.items()]
        )

        if max_per_owner is not None:
            await self._session.execute(select(func.pg_advisory_xact_lock(owner_id)))

            owner_count = (
                select(func.count(UserBot.id))
                .where(UserBot.owner_id == owner_id)
                .scalar_subquery()
            )
            source = source.where(owner_count < max_per_owner)

        stmt = (
            insert(UserBot)
            .from_select(list(values), source)
            .on_conflict_do_nothing(index_elements=[UserBot.bot_id])
            .returning(UserBot)
        )

        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()
        if not orm_model:
            return None
        return UserBotDTO.model_validate(orm_model)

    async def update(self, bot_id: int, **data: Any):
        stmt = update(UserBot).where(UserBot.bot_id == bot_id).values(**data)
        await self._session.execute(stmt)

    async def save(self, dto: UserBotDTO):
        if changed := dto.prepare_changed_data():
            await self.update(dto.bot_id, **changed)

    async def toggle_active(self, bot_id: int) -> UserBotDTO | None:
        stmt = (
            update(UserBot)
            .where(UserBot.bot_id == bot_id, UserBot.banned.is_(False))
            .values(active=~UserBot.active)
            .returning(UserBot)
        )

        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()
        if not orm_model:
            return None
        return UserBotDTO.model_validate(orm_model)

    async def deactivate(self, bot_id: int) -> UserBotDTO | None:
        stmt = (
            update(UserBot)
            .where(UserBot.bot_id == bot_id, UserBot.active.is_(True))
            .values(active=False)
            .returning(UserBot)
        )

        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()
        if not orm_model:
            return None
        return UserBotDTO.model_validate(orm_model)

    async def activate(self, bot_id: int) -> UserBotDTO | None:
        stmt = (
            update(UserBot)
            .where(
                UserBot.bot_id == bot_id,
                UserBot.active.is_(False),
                UserBot.banned.is_(False),
            )
            .values(active=True)
            .returning(UserBot)
        )

        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()
        if not orm_model:
            return None
        return UserBotDTO.model_validate(orm_model)
