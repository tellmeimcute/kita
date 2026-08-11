from dataclasses import dataclass

from database.dto import SuggestionFullDTO
from database.enums import SuggestionStatus as Status
from interfaces import SuggestionServiceProtocol
from task_queue.tasks import suggestion_accepted


@dataclass
class ModerationResult:
    suggestion_dto: SuggestionFullDTO
    verdict_exists: bool


class ModerateSuggestionUseCase:
    __slots__ = ("_suggestion_service",)

    def __init__(self, suggestion_service: SuggestionServiceProtocol):
        self._suggestion_service = suggestion_service

    async def execute(
        self,
        suggestion_dto: SuggestionFullDTO,
        verdict: Status,
        force_update: bool = False,
        bot_id: int | None = None,
    ) -> ModerationResult:
        if suggestion_dto.status != Status.PENDING and not force_update:
            return ModerationResult(suggestion_dto, True)

        suggestion_dto.status = verdict
        await self._suggestion_service.update(suggestion_dto)

        if verdict == Status.ACCEPTED:
            await suggestion_accepted.kiq(bot_id=bot_id, suggestion_id=suggestion_dto.id)
        return ModerationResult(suggestion_dto, False)
