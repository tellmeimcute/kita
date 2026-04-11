

from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.context import FSMContext

from database.dto import SuggestionFullDTO
from helpers.schemas import SuggestionViewerData
from core.exceptions import SQLSuggestionNotFoundError

from services import SuggestionService


class SuggestionQueueManager:
    def __init__(
        self,
        session: AsyncSession,
        suggestion_service: SuggestionService,
        state: FSMContext,
        data: SuggestionViewerData,
    ):
        self.session = session
        self.suggestion_service = suggestion_service
        self.state = state
        self.data = data

    async def dump_into_state(self):
        await self.state.set_data({"viewer_data": self.data.model_dump()})

    async def get_updated_dto(self) -> SuggestionFullDTO:
        suggestion_dto = self.data.suggestion_dto
        async with self.session.begin():
            updated_dto = await self.suggestion_service.get(suggestion_dto.id, solo=True)

        self.data.suggestion_dto.accepted = updated_dto.accepted
        return self.data.suggestion_dto

    async def pop_next(self) -> SuggestionFullDTO | None:
        try:
            if not self.data.suggestion_dtos:
                async with self.session.begin():
                    self.data.suggestion_dtos = await self.suggestion_service.get_active()
        except SQLSuggestionNotFoundError:
            return None

        if not self.data.suggestion_dtos:
            return None

        new_active = self.data.suggestion_dtos.pop(0)
        self.data.suggestion_dto = new_active
        await self.dump_into_state()
        
        return new_active