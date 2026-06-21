
from typing import Sequence, Any

from sqlalchemy import Result, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import UserAlchemy, Suggestion
from database.dto import UserDTO
from database.enums import UserRole, SuggestionStatus

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
        await self._session.refresh(orm)
        return UserDTO.model_validate(orm)

    async def get_active(self) -> Sequence[UserDTO]:
        stmt = (
            select(UserAlchemy)
            .where(
                (UserAlchemy.role != UserRole.BANNED) & UserAlchemy.is_bot_blocked.is_not(True)
            )
        )

        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()
        return UserDTO.from_model_list(orm_models)

    async def get_admins(self) -> Sequence[UserDTO]:
        stmt = (
            select(UserAlchemy)
            .where(UserAlchemy.role == UserRole.ADMIN)
        )

        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()
        return UserDTO.from_model_list(orm_models)

    async def get_banned(self) -> Sequence[UserDTO]:
        stmt = (
            select(UserAlchemy)
            .where(UserAlchemy.role == UserRole.BANNED)
        )
        
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()
        return UserDTO.from_model_list(orm_models)

    async def count(self) -> int:
        stmt = select(func.count(UserAlchemy.id))
        count = await self._session.scalar(stmt)
        return count or 0
    
    async def admins_count(self) -> int:
        stmt = (
            select(func.count(UserAlchemy.id))
            .where(UserAlchemy.role == UserRole.ADMIN)
        )
        count = await self._session.scalar(stmt)
        return count or 0
    
    async def banned_count(self) -> int:
        stmt = (
            select(func.count(UserAlchemy.id))
            .where(UserAlchemy.role == UserRole.BANNED)
        )
        count = await self._session.scalar(stmt)
        return count or 0
    
    async def user_stats(self):
        stmt = select(
            func.count(UserAlchemy.id).label("users_total"),
            func.count(UserAlchemy.id).filter(UserAlchemy.role == UserRole.USER).label("users"),
            func.count(UserAlchemy.id).filter(UserAlchemy.role == UserRole.ADMIN).label("admins"),
            func.count(UserAlchemy.id).filter(UserAlchemy.role == UserRole.BANNED).label("banned"),
        )
        result: Result = await self._session.execute(stmt)
        return result.one()
    
    async def decline_all_suggestions(self, user_id: int):
        stmt = (
            update(Suggestion)
            .where(Suggestion.author_id == user_id)
            .values(status=SuggestionStatus.DECLINED)
        )
        await self._session.execute(stmt)
        