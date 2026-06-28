
from aiogram.fsm.context import FSMContext

from core.schemas import SuggestionViewerData
from database.dto import SuggestionFullDTO
from interfaces import UnitOfWorkProtocol, SuggestionServiceProtocol

class SuggestionQueueManager:

    __slots__ = (
        "uow",
        "suggestion_service",
        "state",
        "data",
    )

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        suggestion_service: SuggestionServiceProtocol,
        state: FSMContext,
        data: SuggestionViewerData,
    ):
        self.uow = uow
        self.suggestion_service = suggestion_service
        self.state = state
        self.data = data

    async def dump_into_state(self):
        await self.state.set_data({"viewer_data": self.data.model_dump(mode="json")})

    async def get_updated_dto(self) -> SuggestionFullDTO:
        suggestion_dto = self.data.suggestion_dto
        updated_dto = await self.suggestion_service.get(suggestion_dto.id)

        self.data.suggestion_dto.status = updated_dto.status
        return self.data.suggestion_dto

    async def pop_next(self, dump_into_state=True) -> SuggestionFullDTO | None:
        if not self.data.suggestion_dtos:
            async with self.uow.transaction():
                self.data.suggestion_dtos = await self.suggestion_service.get_active()

        if not self.data.suggestion_dtos:
            return None

        new_active = self.data.suggestion_dtos.pop(0)
        self.data.suggestion_dto = new_active

        if dump_into_state:
            await self.dump_into_state()
        
        return new_active