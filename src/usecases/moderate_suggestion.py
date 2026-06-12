
import asyncio
from dataclasses import dataclass

from core.config import Config
from core.suggestion_utils import SuggestionUtils
from core.schemas.message_payload import MessagePayload

from database.dto import SuggestionFullDTO
from services import NotifierService, SuggestionService

@dataclass
class ModerationResult:
    suggestion_dto: SuggestionFullDTO
    verdict_exists: bool

class ModerateSuggestionUseCase:
    def __init__(
        self,
        config: Config,
        notifier: NotifierService,
        utils: SuggestionUtils,
        suggestion_service: SuggestionService,
    ):
        self._suggestion_service = suggestion_service
        self._notifier = notifier
        self._utils = utils
        self._config = config

    async def _process_accepted(self, suggestion_dto: SuggestionFullDTO):
        channel_payload = self._utils.payload_factory(suggestion_dto, "channel_post_message")
        strategy = self._notifier.send_strategy_factory(self._config.CHANNEL_ID, channel_payload)
        
        author_payload = MessagePayload(
            i18n_key="notify_author_suggestion_status",
            i18n_kwargs=self._utils.get_i18n_kwargs(suggestion_dto),
        )

        await asyncio.gather(
            self._notifier.send(strategy),
            self._notifier.notify_user_i18n(suggestion_dto.author, author_payload)
        )
    
    async def execute(
        self,
        suggestion_dto: SuggestionFullDTO,
        verdict: bool,
        force_update: bool = False,
    ) -> ModerationResult:
        if suggestion_dto.accepted is not None and not force_update:
            return ModerationResult(suggestion_dto, True)

        suggestion_dto.accepted = verdict
        await self._suggestion_service.update(suggestion_dto)

        if verdict:
            await self._process_accepted(suggestion_dto)

        return ModerationResult(suggestion_dto, False)