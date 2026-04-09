from logging import getLogger

from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.context import FSMContext

from config import Config, RuntimeConfig
from database.dto import SUGGESTION_DTOS, SuggestionFullDTO
from helpers.suggestion_utils import SuggestionUtils
from routers.keyboards import ReplyKeyboard
from helpers.schemas.message_payload import MessagePayload
from helpers.schemas import SuggestionViewerData
from helpers.exceptions import SQLModelNotFoundError

from services import NotifierService, SuggestionService

logger = getLogger("kita.suggestion_viewer")


class SuggestionViewer:
    def __init__(
        self,
        data: SuggestionViewerData,
        session: AsyncSession,
        suggestion_service: SuggestionService,
        notifier: NotifierService,
        config: Config,
        runtime_config: RuntimeConfig,
    ):
        self.data = data
        self.session = session
        self.suggestion_service = suggestion_service
        self.notifier = notifier
        self.config = config
        self.runtime_config = runtime_config

        self.utils = SuggestionUtils.from_viewer(self)

    @classmethod
    async def from_state(
        self,
        state: FSMContext,
        session: AsyncSession,
        suggestion_service: SuggestionService,
        notifier: NotifierService,
        config: Config,
        runtime_config: RuntimeConfig,
    ):
        data = await state.get_data()
        viewer_data = SuggestionViewerData.model_validate(data.get("viewer_data"))
        return self(viewer_data, session, suggestion_service, notifier, config, runtime_config)

    async def dump_into_state(self, state: FSMContext, data: SuggestionViewerData):
        await state.set_data({"viewer_data": data.model_dump()})

    async def render_wait_verdict(self):
        payload = MessagePayload(
            i18n_key="send_verdict", reply_markup=ReplyKeyboard.viewer_admin_action()
        )
        await self.notifier.notify_user(self.data.user_dto, payload)

    async def render_start_review(self):
        payload = MessagePayload(
            i18n_key="start_review_suggestions", reply_markup=ReplyKeyboard.viewer_admin_action()
        )
        await self.notifier.notify_user(self.data.user_dto, payload)

    async def render_verdict_rewrite(self):
        payload = MessagePayload(
            i18n_key="verdict_rewrite", reply_markup=ReplyKeyboard.main(self.data.user_dto)
        )
        await self.notifier.notify_user(self.data.user_dto, payload)

    async def render_suggestion(self):
        i18n_key = "admin_get_suggestion_caption"
        kb = ReplyKeyboard.viewer_admin_action()
        payload = self.utils.payload_factory(self.data.suggestion_dto, i18n_key, kb)
        return await self.notifier.notify_user(self.data.user_dto, payload)

    async def post_channel(self, suggestion_dto: SuggestionFullDTO):
        i18n_key = "channel_post_message"
        payload = self.utils.payload_factory(suggestion_dto, i18n_key)
        strategy = self.notifier.send_strategy_factory(self.config.CHANNEL_ID, payload)
        return await self.notifier.send(strategy)

    async def render_empty_queue(self):
        user_dto = self.data.user_dto
        payload = MessagePayload(
            i18n_key="no_active_suggestions", reply_markup=ReplyKeyboard.main(user_dto)
        )
        return await self.notifier.notify_user(user_dto, payload)

    async def render_verdict_exists(self):
        i18n_kwargs = self.utils.get_i18n_kwargs(self.data.suggestion_dto)
        payload = MessagePayload(i18n_key="suggestion_verdict_exists", i18n_kwargs=i18n_kwargs)
        await self.notifier.notify_user(self.data.user_dto, payload)

    async def notify_author(self, suggestion_dto: SUGGESTION_DTOS):
        """send suggestion status to author"""
        i18n_kwargs = self.utils.get_i18n_kwargs(suggestion_dto)
        payload = MessagePayload(
            i18n_key="notify_author_suggestion_status",
            i18n_kwargs=i18n_kwargs,
        )

        await self.notifier.notify_user(suggestion_dto.author, payload)

    async def get_updated_dto(self):
        suggestion_dto = self.data.suggestion_dto

        async with self.session.begin():
            updated_dto = await self.suggestion_service.get(suggestion_dto.id, solo=True)

        suggestion_dto = suggestion_dto.model_copy(update={"accepted": updated_dto.accepted})
        self.data = self.data.model_copy(update={"suggestion_dto": suggestion_dto})

        return self.data.suggestion_dto

    async def to_next_suggestion(self, state: FSMContext) -> SuggestionFullDTO | None:
        """
        Теперь вообще не вызывает рендер, только обновляет состояние, внутреннее и aiogram FSM.
        """
        try:
            if not self.data.suggestion_dtos:
                async with self.session.begin():
                    active_list = await self.suggestion_service.get_active()
                self.data = self.data.model_copy(update={"suggestion_dtos": active_list})
        except SQLModelNotFoundError:
            return

        new_active = self.data.suggestion_dtos.pop(0)
        self.data = self.data.model_copy(
            update={"suggestion_dto": new_active}
        )

        await self.dump_into_state(state, self.data)

        return new_active

    async def go_next_suggestion(self, state: FSMContext):
        """
        Render and store in state next_suggestion if any.
        Else clear state and render empty_queue.
        """
        if await self.to_next_suggestion(state):
            return await self.render_suggestion()

        await state.clear()
        await self.render_empty_queue()
