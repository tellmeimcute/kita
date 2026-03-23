from logging import getLogger

from aiogram.fsm.context import FSMContext
from aiogram.utils.media_group import MediaGroupBuilder

from database.dto import SUGGESTION_DTOS, SuggestionFullDTO
from handlers.keyboards import ReplyKeyboard
from helpers.schemas.objects import SuggestionData
from helpers.enums import RenderType
from helpers.message_payload import MessagePayload
from helpers.schemas import SuggestionViewerData

from services import NotifierService, SuggestionService
from config import Config

logger = getLogger("kita.suggestion_viewer")

class SuggestionViewerUtils:
    def __init__(self, config: Config, notifier: NotifierService):
        self.config = config
        self.notifier = notifier

    @classmethod
    def from_viewer(cls, viewer: "SuggestionViewer"):
        return cls(viewer.config, viewer.notifier)
        
    def get_verdict(self, suggestion_dto: SUGGESTION_DTOS):
        i18n_key = "none_suggestion"
        if suggestion_dto.accepted is not None:
            i18n_key = "bool_suggestion_true" if suggestion_dto.accepted else "bool_suggestion_false"
        return self.notifier.get_translated_text(i18n_key)

    def get_author_plus_origin(self, suggestion_dto: SUGGESTION_DTOS):
        return self.notifier.get_i18n_text(
            i18n_key="author_plus_origin", i18n_kwargs={
                "author_name": suggestion_dto.author.name,
                "forwarded_from": suggestion_dto.forwarded_from,
            }
        )

    def get_i18n_kwargs(self, suggestion_dto: SuggestionFullDTO | SuggestionData):
        verdict = self.get_verdict(suggestion_dto)
        author_plus_origin = self.get_author_plus_origin(suggestion_dto)
        author_string = author_plus_origin if suggestion_dto.forwarded_from else suggestion_dto.author.name
        caption = suggestion_dto.caption if suggestion_dto.caption else ""
        
        i18n_kwargs = suggestion_dto.model_dump()
        i18n_kwargs.update(
            author_plus_origin=author_plus_origin,
            author_string=author_string,
            caption=caption,
            verdict=verdict,
            bot_url=self.config.runtime_config.bot_url,
        )

        return i18n_kwargs

    def get_media_group(self, suggestion_dto: SuggestionFullDTO) -> MediaGroupBuilder:
        media_group = MediaGroupBuilder()

        for media in suggestion_dto.media:
            media_group.add(type=media.filetype, media=media.telegram_file_id)

        return media_group
    
    def media_group_payload(self, suggestion_dto: SuggestionFullDTO, i18n_key: str | None = None):
        if not i18n_key:
            i18n_key = "admin_get_suggestion_caption"

        media_group: MediaGroupBuilder = self.get_media_group(suggestion_dto)

        i18n_kwargs = self.get_i18n_kwargs(suggestion_dto)
        media_group.caption = self.notifier.get_i18n_text(i18n_key, i18n_kwargs)

        payload = MessagePayload(content=media_group.build())
        return payload

    def update_status(self, suggestion_dto: SUGGESTION_DTOS, new_status: bool):
        suggestion_dto.accepted = new_status

class SuggestionViewer:
    def __init__(
        self,
        data: SuggestionViewerData,
        suggestion_service: SuggestionService,
        notifier: NotifierService,
        config: Config,
    ):
        self.data = data
        self.suggestion_service = suggestion_service
        self.notifier = notifier
        self.config = config

        self.utils = SuggestionViewerUtils.from_viewer(self)

        self._suggestion_data: SuggestionData = None

    @classmethod
    async def from_state(
        self,
        state: FSMContext,
        suggestion_service: SuggestionService,
        notifier: NotifierService,
        config: Config,
    ):
        data = await state.get_data()
        viewer_data: SuggestionViewerData = data.get("viewer_data")
        return self(viewer_data, suggestion_service, notifier, config)

    @property
    def suggestion_data(self) -> SuggestionData:
        if self._suggestion_data:
            return self._suggestion_data
        
        if self.data.suggestion_dto:
            self._suggestion_data = SuggestionData.model_validate(self.data.suggestion_dto)
            return self._suggestion_data

    @suggestion_data.setter
    def suggestion_data(self, value):
        self._suggestion_data = value

    async def dump_into_state(self, state: FSMContext, data: SuggestionViewerData):
        await state.set_data({"viewer_data": data})

    async def render_wait_verdict(self):
        payload = MessagePayload(i18n_key="send_verdict", reply_markup=ReplyKeyboard.viewer_admin_action())
        await self.notifier.notify_user(self.data.user_dto, payload)

    async def render_start_review(self):
        payload = MessagePayload(i18n_key="start_review_suggestions", reply_markup=ReplyKeyboard.viewer_admin_action())
        await self.notifier.notify_user(self.data.user_dto, payload)

    async def render_verdict_rewrite(self):
        payload = MessagePayload(i18n_key="verdict_rewrite", reply_markup=ReplyKeyboard.main(self.data.user_dto))
        await self.notifier.notify_user(self.data.user_dto, payload)

    async def render_suggestion(self):
        render_type = self.data.render_type

        if render_type == RenderType.MESSAGE:
            payload = MessagePayload(
                i18n_key="admin_get_suggestion_caption",
                i18n_kwargs=self.utils.get_i18n_kwargs(self.data.suggestion_dto),
                reply_markup=ReplyKeyboard.viewer_admin_action(),
            )
        elif render_type == RenderType.MEDIAGROUP:
            payload = self.utils.media_group_payload(self.data.suggestion_dto)

        return await self.notifier.notify_user(self.data.user_dto, payload)
    
    async def render_empty_queue(self):
        user_dto = self.data.user_dto
        payload = MessagePayload(i18n_key="no_active_suggestions", reply_markup=ReplyKeyboard.main(user_dto))
        return await self.notifier.notify_user(user_dto, payload)
    
    async def render_verdict_exists(self):
        i18n_kwargs = self.utils.get_i18n_kwargs(self.data.suggestion_dto)
        payload = MessagePayload(i18n_key="suggestion_verdict_exists", i18n_kwargs=i18n_kwargs)
        await self.notifier.notify_user(self.data.user_dto, payload)

    async def notify_author(self):
        """send suggestion status to author"""
        i18n_kwargs = self.utils.get_i18n_kwargs(self.data.suggestion_dto)
        payload = MessagePayload(
            i18n_key="notify_author_suggestion_status",
            i18n_kwargs=i18n_kwargs,
        )

        await self.notifier.notify_user(self.data.suggestion_dto.author, payload)

    async def get_updated_dto(self):
        suggestion_dto = self.data.suggestion_dto

        updated_dto = await self.suggestion_service.get(suggestion_dto.id, solo=True)
        suggestion_dto = suggestion_dto.model_copy(update={"accepted": updated_dto.accepted})
        self.data = self.data.model_copy(update={"suggestion_dto": suggestion_dto})

        return self.data.suggestion_dto

    async def to_next_suggestion(self, state: FSMContext) -> SuggestionFullDTO | None:
        """
        Теперь вообще не вызывает рендер, только обновляет состояние, внутреннее и aiogram FSM.
        """

        new_active = await self.suggestion_service.get_active()
        if not new_active:
            return
        
        self.data = self.data.model_copy(
            update={"suggestion_dto": new_active}
        )
        self._suggestion_data = SuggestionData.model_validate(self.data.suggestion_dto)

        await self.dump_into_state(state, self.data)

        return new_active
    
    async def post_channel(self):
        i18n_key = "channel_post_message"
        i18n_kwargs = self.utils.get_i18n_kwargs(self.suggestion_data)

        render_type = self.data.render_type
        if render_type == RenderType.MESSAGE:
            payload = MessagePayload(i18n_key=i18n_key, i18n_kwargs=i18n_kwargs)
        elif render_type == RenderType.MEDIAGROUP:
            payload = self.utils.media_group_payload(self.suggestion_data, i18n_key)

        return await self.notifier.send_channel(self.config.CHANNEL_ID, payload)
    
    async def go_next_suggestion(self, state: FSMContext):
        """
        Render and store in state next_suggestion if any.
        Else clear state and render empty_queue.
        """
        if await self.to_next_suggestion(state):
            return await self.render_suggestion()
        
        await state.clear()
        await self.render_empty_queue()