from collections.abc import Sequence

from aiogram.fsm.context import FSMContext

from database.dto import SuggestionFullDTO
from interfaces import BotRegistryProtocol, SuggestionServiceProtocol, UnitOfWorkProtocol

from .base import BaseService


class SuggestionQueue(BaseService):
    __slots__ = (
        "suggestion_service",
        "uow",
        "fsm",
    )

    def __init__(
        self,
        bot_registry: BotRegistryProtocol,
        suggestion_service: SuggestionServiceProtocol,
        uow: UnitOfWorkProtocol,
        fsm_context: FSMContext,
    ):
        super().__init__(bot_registry)
        self.suggestion_service = suggestion_service
        self.uow = uow
        self.fsm = fsm_context

    async def get_queue(self) -> list[dict]:
        data = await self.fsm.get_data()
        return data.get("suggestion_queue", [])

    async def _from_queue(self, queue: list[dict]) -> SuggestionFullDTO:
        val = queue.pop(0)
        result = SuggestionFullDTO.model_validate(val)

        await self.fsm.update_data({"suggestion_queue": queue})
        return result

    async def seed_queue(self, suggestions: Sequence[SuggestionFullDTO]) -> list[dict]:
        queue = [s.model_dump(mode="json") for s in suggestions]
        await self.fsm.update_data({"suggestion_queue": queue})
        return queue

    async def next_suggestion(self) -> SuggestionFullDTO | None:
        queue = await self.get_queue()

        if queue:
            return await self._from_queue(queue)

        async with self.uow.transaction():
            new_suggestions = await self.suggestion_service.get_active()

        if not new_suggestions:
            return None

        queue = await self.seed_queue(new_suggestions)
        return await self._from_queue(queue)
