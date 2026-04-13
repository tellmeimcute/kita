
import asyncio

from core.config import Config
from database.dto import SuggestionFullDTO
from helpers.suggestion_utils import SuggestionUtils
from helpers.schemas.message_payload import MessagePayload
from services import NotifierService


class SuggestionModerationService:
    def __init__(self, notifier: NotifierService, utils: SuggestionUtils, config: Config):
        self.notifier = notifier
        self.utils = utils
        self.config = config

    async def process_accepted(self, suggestion_dto: SuggestionFullDTO):
        channel_payload = self.utils.payload_factory(suggestion_dto, "channel_post_message")
        strategy = self.notifier.send_strategy_factory(self.config.CHANNEL_ID, channel_payload)
        
        author_payload = MessagePayload(
            i18n_key="notify_author_suggestion_status",
            i18n_kwargs=self.utils.get_i18n_kwargs(suggestion_dto),
        )

        asyncio.gather(
            self.notifier.send(strategy),
            self.notifier.notify_user_i18n(suggestion_dto.author, author_payload)
        )