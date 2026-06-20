
from typing import Sequence, Any

from sqlalchemy import Result, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Suggestion
from database.dto import SuggestionBaseDTO, SuggestionFullDTO
from database.enums import SuggestionStatus

from core.schemas.objects import UserStats

class SuggestionRepository:
    
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, suggestion_id: int) -> SuggestionFullDTO | None:
        stmt = (
            select(Suggestion)
            .where(Suggestion.id == suggestion_id)
            .options(selectinload(Suggestion.media), selectinload(Suggestion.author))
        )

        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()
        if not orm_model:
            return None
        return SuggestionFullDTO.model_validate(orm_model)
    
    async def get_active(
        self,
        limit=10,
        offset=0,
    ) -> Sequence[SuggestionFullDTO]:
        stmt = (
            select(Suggestion)
            .where(Suggestion.status == SuggestionStatus.PENDING)
            .options(selectinload(Suggestion.media), selectinload(Suggestion.author))
            .offset(offset)
            .limit(limit)
            .order_by(Suggestion.id.asc())
        )

        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()
        return SuggestionFullDTO.from_model_list(orm_models)
    
    async def update(self, suggestion_id: int, **data: Any):
        stmt = update(Suggestion).where(Suggestion.id == suggestion_id).values(data)
        await self._session.execute(stmt)

    async def save(self, dto: SuggestionBaseDTO):
        changed = dto.prepare_changed_data()
        if not changed:
            return
        await self.update(dto.id, **changed)

    async def create(self, **data) -> SuggestionFullDTO:
        orm = Suggestion(**data)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return SuggestionFullDTO.model_validate(orm)
    
    async def get_user_stats(self, user_id: int) -> UserStats | None:
        stmt = select(
            func.count(Suggestion.id).label("total"),
            func.count(Suggestion.id).filter(Suggestion.status == SuggestionStatus.ACCEPTED).label("accepted"),
            func.count(Suggestion.id).filter(Suggestion.status == SuggestionStatus.DECLINED).label("declined"),
        ).where(Suggestion.author_id == user_id)

        result: Result = await self._session.execute(stmt)
        row = result.one_or_none()
        if not row:
            return None
        return UserStats.model_validate(row)

    async def count(self) -> int:
        stmt = select(func.count(Suggestion.id))
        count = await self._session.scalar(stmt)
        return count or 0
    