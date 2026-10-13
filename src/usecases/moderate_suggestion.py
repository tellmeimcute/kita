from dataclasses import dataclass

from database.dto import SuggestionFullDTO
from database.enums import SuggestionStatus as Status
from interfaces import (
    BotRegistryProtocol,
    SuggestionServiceProtocol,
    SuggestionTaskDispatcherProtocol,
    UnitOfWorkProtocol,
)
from interfaces.mixins import BotMixin


@dataclass
class ModerationResult:
    suggestion_dto: SuggestionFullDTO
    verdict_exists: bool


class ModerateSuggestionUseCase(BotMixin):
    __slots__ = ("_uow", "_suggestion_service", "_task_dispatcher")

    def __init__(
        self,
        bot_registry: BotRegistryProtocol,
        uow: UnitOfWorkProtocol,
        suggestion_service: SuggestionServiceProtocol,
        task_dispatcher: SuggestionTaskDispatcherProtocol,
    ):
        super().__init__(bot_registry)
        self._uow = uow
        self._suggestion_service = suggestion_service
        self._task_dispatcher = task_dispatcher

    async def execute(
        self,
        suggestion_dto: SuggestionFullDTO,
        verdict: Status,
        force_update: bool = False,
    ) -> ModerationResult:
        if suggestion_dto.status != Status.PENDING and not force_update:
            return ModerationResult(suggestion_dto, True)

        suggestion_dto.status = verdict

        async with self._uow.transaction():
            await self._suggestion_service.update(suggestion_dto)

        if verdict == Status.ACCEPTED:
            await self._task_dispatcher.accepted(self.bot.id, suggestion_dto.id)
        return ModerationResult(suggestion_dto, False)
