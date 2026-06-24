

from dataclasses import dataclass
from dishka import AsyncContainer

from core.events import EventBus, SuggestionAcceptedEvent
from database.dto import SuggestionFullDTO
from database.enums import SuggestionStatus as Status
from services import SuggestionService

@dataclass
class ModerationResult:
    suggestion_dto: SuggestionFullDTO
    verdict_exists: bool

class ModerateSuggestionUseCase:

    __slots__ = (
        "_suggestion_service",
        "_event_bus",
        "_container"
    )

    def __init__(
        self,
        suggestion_service: SuggestionService,
        event_bus: EventBus,
        container: AsyncContainer,
    ):
        self._suggestion_service = suggestion_service
        self._event_bus = event_bus
        self._container = container

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
            self._event_bus.dispatch(SuggestionAcceptedEvent(
                container=self._container,
                suggestion_dto=suggestion_dto,
            ))

        return ModerationResult(suggestion_dto, False)