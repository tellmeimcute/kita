from dataclasses import dataclass

from database.enums import SuggestionStatus as Status
from interfaces import (
    BotContextProtocol,
    SuggestionServiceProtocol,
    SuggestionTaskDispatcherProtocol,
    UnitOfWorkProtocol,
)
from interfaces.mixins import BotMixin


@dataclass
class ModerationResult:
    suggestion_id: int
    applied: bool
    status: Status | None  # None → suggestion not found


class ModerateSuggestionUseCase(BotMixin):
    __slots__ = ("_uow", "_suggestion_service", "_task_dispatcher")

    def __init__(
        self,
        bot_context: BotContextProtocol,
        uow: UnitOfWorkProtocol,
        suggestion_service: SuggestionServiceProtocol,
        task_dispatcher: SuggestionTaskDispatcherProtocol,
    ):
        super().__init__(bot_context)
        self._uow = uow
        self._suggestion_service = suggestion_service
        self._task_dispatcher = task_dispatcher

    async def execute(
        self,
        suggestion_id: int,
        verdict: Status,
    ) -> ModerationResult:
        async with self._uow.transaction():
            applied = await self._suggestion_service.apply_verdict(suggestion_id, verdict)

        if not applied:
            return ModerationResult(
                suggestion_id,
                applied=False,
                status=await self._current_status(suggestion_id),
            )

        if verdict == Status.ACCEPTED:
            await self._task_dispatcher.accepted(self.bot.id, suggestion_id)

        return ModerationResult(suggestion_id, applied=True, status=verdict)

    async def _current_status(self, suggestion_id: int) -> Status | None:
        async with self._uow.transaction():
            suggestion_dto = await self._suggestion_service.get(suggestion_id)

        return suggestion_dto.status if suggestion_dto else None
