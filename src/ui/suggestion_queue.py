from collections.abc import Sequence

from aiogram.fsm.context import FSMContext

from database.dto import SuggestionFullDTO
from interfaces import BotContextProtocol, SuggestionServiceProtocol, UnitOfWorkProtocol
from interfaces.mixins import BotMixin


class SuggestionQueue(BotMixin):
    """
    Keeps pending suggestion ids in the FSM;
    DTOs are fetched from the DB on demand.
    """

    __slots__ = (
        "suggestion_service",
        "uow",
        "fsm",
    )

    def __init__(
        self,
        bot_context: BotContextProtocol,
        suggestion_service: SuggestionServiceProtocol,
        uow: UnitOfWorkProtocol,
        fsm_context: FSMContext,
    ):
        super().__init__(bot_context)
        self.suggestion_service = suggestion_service
        self.uow = uow
        self.fsm = fsm_context

    async def get_queue(self) -> list[int]:
        data = await self.fsm.get_data()
        return data.get("suggestion_queue", [])

    async def seed_queue(self, ids: Sequence[int]) -> list[int]:
        queue = list(ids)
        await self.fsm.update_data({"suggestion_queue": queue})
        return queue

    async def next_suggestion(self) -> SuggestionFullDTO | None:
        queue = await self.get_queue()

        while True:
            if not queue:
                async with self.uow.transaction():
                    new_ids = await self.suggestion_service.get_active_ids()

                if not new_ids:
                    return None

                queue = await self.seed_queue(new_ids)

            suggestion_id = queue.pop(0)
            await self.fsm.update_data({"suggestion_queue": queue})

            async with self.uow.transaction():
                dto = await self.suggestion_service.get_active_by_id(suggestion_id)

            if dto is not None:
                return dto
