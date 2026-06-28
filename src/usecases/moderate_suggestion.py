

from dataclasses import dataclass
from core.events import EventBus, SuggestionAcceptedEvent
from database.dto import SuggestionFullDTO
from database.enums import SuggestionStatus as Status
from interfaces import SuggestionServiceProtocol

@dataclass
class ModerationResult:
    suggestion_dto: SuggestionFullDTO
    verdict_exists: bool

class ModerateSuggestionUseCase:

    __slots__ = (
        "_suggestion_service",
        "_event_bus",
    )

    def __init__(
        self, suggestion_service: SuggestionServiceProtocol, event_bus: EventBus
    ):
        self._suggestion_service = suggestion_service
        self._event_bus = event_bus

    async def execute(
        self,
        suggestion_dto: SuggestionFullDTO,
        verdict: Status,
        force_update: bool = False,
    ) -> ModerationResult:
        
        if suggestion_dto.status != Status.PENDING and not force_update:
            return ModerationResult(suggestion_dto, True)

        suggestion_dto.status = verdict
        await self._suggestion_service.update(suggestion_dto)

        if verdict == Status.ACCEPTED:
            await self._event_bus.dispatch(SuggestionAcceptedEvent(
                suggestion_dto=suggestion_dto,
            ))

        return ModerationResult(suggestion_dto, False)