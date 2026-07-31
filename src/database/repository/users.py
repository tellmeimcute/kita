
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from database.dto import UserDTO
from database.models import UserAlchemy

from .base import BaseRepository


class UserRepository(BaseRepository):

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

    async def get_or_create(self, prep_user_dto: UserDTO) -> UserDTO:
        values = prep_user_dto.model_dump(exclude={"created_at", "updated_at"})
        stmt = (
            insert(UserAlchemy)
            .values(**values)
            .on_conflict_do_nothing()
            .returning(UserAlchemy)
        )

        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()
        if orm_model is None:
            return await self.get_by_id(prep_user_dto.user_id)

        return UserDTO.model_validate(orm_model)

    async def update(self, user_id: int, **data: Any):
        stmt = update(UserAlchemy).where(UserAlchemy.user_id == user_id).values(data)
        await self._session.execute(stmt)

    async def create(self, dto: UserDTO):
        orm = UserAlchemy(**dto.model_dump())
        self._session.add(orm)
        await self._session.flush()
        return UserDTO.model_validate(orm)

    async def count(self) -> int:
        stmt = select(func.count(UserAlchemy.id))
        count = await self._session.scalar(stmt)
        return count or 0
