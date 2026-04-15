
from aiogram.types import ReplyKeyboardRemove

from ui.keyboards import ReplyKeyboard
from database.dto import SuggestionFullDTO, UserDTO
from helpers.suggestion_utils import SuggestionUtils
from helpers.schemas.message_payload import MessagePayload
from services import NotifierService

class SuggestionRenderer:

    def __init__(
        self,
        notifier: NotifierService,
        suggestion_utils: SuggestionUtils,
    ):
        self.notifier = notifier
        self.utils = suggestion_utils

    async def wait_verdict(self, user_dto: UserDTO):
        payload = MessagePayload(
            i18n_key="wait_verdict_text", reply_markup=ReplyKeyboard.viewer_admin_action()
        )
        await self.notifier.notify_user(user_dto, payload)

    async def start_review(self, user_dto: UserDTO):
        payload = MessagePayload(
            i18n_key="start_review_suggestions", reply_markup=ReplyKeyboard.viewer_admin_action()
        )
        await self.notifier.notify_user(user_dto, payload)

    async def verdict_rewrite(self, user_dto: UserDTO):
        payload = MessagePayload(
            i18n_key="verdict_rewrite", reply_markup=ReplyKeyboardRemove()
        )
        await self.notifier.notify_user(user_dto, payload)

    async def suggestion(self, user_dto: UserDTO, suggestion_dto: SuggestionFullDTO):
        i18n_key = "admin_get_suggestion_caption"
        kb = ReplyKeyboard.viewer_admin_action()
        payload = self.utils.payload_factory(suggestion_dto, i18n_key, kb)
        return await self.notifier.notify_user(user_dto, payload)

    async def empty_queue(self, user_dto: UserDTO):
        user_dto = user_dto
        payload = MessagePayload(
            i18n_key="no_active_suggestions", reply_markup=ReplyKeyboardRemove()
        )
        return await self.notifier.notify_user(user_dto, payload)

    async def verdict_exists(self, user_dto: UserDTO, suggestion_dto: SuggestionFullDTO):
        i18n_kwargs = self.utils.get_i18n_kwargs(suggestion_dto)
        payload = MessagePayload(i18n_key="suggestion_verdict_exists", i18n_kwargs=i18n_kwargs)
        await self.notifier.notify_user(user_dto, payload)