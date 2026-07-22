
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import UserAlchemy
from database.dto import UserDTO


class UserRepository:

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, user_id: int) -> UserDTO | None:
        stmt = (
            select(UserAlchemy)
            .where(UserAlchemy.user_id == user_id)
        )

        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()
        if not orm_model:
            return None
        return UserDTO.model_validate(orm_model)

    async def update(self, user_id: int, **data: Any):
        stmt = update(UserAlchemy).where(UserAlchemy.user_id == user_id).values(data)
        await self._session.execute(stmt)

    async def save(self, dto: UserDTO):
        if changed := dto.prepare_changed_data():
            await self.update(dto.user_id, **changed)

    async def create(self, dto: UserDTO):
        orm = UserAlchemy(**dto.model_dump())
        self._session.add(orm)
        await self._session.flush()
        return UserDTO.model_validate(orm)

    async def count(self) -> int:
        stmt = select(func.count(UserAlchemy.id))
        count = await self._session.scalar(stmt)
        return count or 0
