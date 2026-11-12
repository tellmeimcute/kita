from dataclasses import dataclass
from typing import ClassVar

from loguru import logger

from database.enums import SuggestionStatus as Status
from events import Event, SuggestionAccepted, SuggestionDeclined
from interfaces import (
    BotContextProtocol,
    EventBusProtocol,
    SuggestionServiceProtocol,
    UnitOfWorkProtocol,
)
from interfaces.mixins import BotMixin


@dataclass
class ModerationResult:
    suggestion_id: int
    applied: bool
    status: Status | None  # None → suggestion not found


class ModerateSuggestionUseCase(BotMixin):
    VERDICT_EVENTS: ClassVar[dict[Status, type[Event]]] = {
        Status.ACCEPTED: SuggestionAccepted,
        Status.DECLINED: SuggestionDeclined,
    }

    __slots__ = ("_uow", "_suggestion_service", "_events")

    def __init__(
        self,
        bot_context: BotContextProtocol,
        uow: UnitOfWorkProtocol,
        suggestion_service: SuggestionServiceProtocol,
        events: EventBusProtocol,
    ):
        super().__init__(bot_context)
        self._uow = uow
        self._suggestion_service = suggestion_service
        self._events = events

    async def execute(
        self,
        suggestion_id: int,
        verdict: Status,
    ) -> ModerationResult:
        async with self._uow.transaction():
            applied = await self._suggestion_service.apply_verdict(suggestion_id, verdict)

            if applied:
                await self._publish_verdict(suggestion_id, verdict)

        if not applied:
            return ModerationResult(
                suggestion_id,
                applied=False,
                status=await self._current_status(suggestion_id),
            )

        return ModerationResult(suggestion_id, applied=True, status=verdict)

    async def _publish_verdict(self, suggestion_id: int, verdict: Status) -> None:
        event_type = self.VERDICT_EVENTS.get(verdict)

        if event_type is None:
            logger.warning("Verdict {} of suggestion {} has no event", verdict, suggestion_id)
            return

        await self._events.publish(event_type(bot_id=self.bot.id, suggestion_id=suggestion_id))

    async def _current_status(self, suggestion_id: int) -> Status | None:
        async with self._uow.transaction():
            suggestion_dto = await self._suggestion_service.get(suggestion_id)

        return suggestion_dto.status if suggestion_dto else None
