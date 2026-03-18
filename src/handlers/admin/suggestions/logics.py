from logging import getLogger

from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao import SuggestionDAO
from database.dto import SuggestionFullDTO
from handlers.keyboards import get_viewer_accept_decline_kb, get_main_kb_by_role
from helpers.enums import RenderType, ViewerAdminAction
from helpers.message_payload import MessagePayload
from helpers.schemas import SuggestionViewerData
from helpers.utils import get_media_group
from services.notifier import NotifierService
from config import Config

logger = getLogger("kita.suggestion_viewer")

class SuggestionViewerRenderer:
    def __init__(self, notifier: NotifierService, data: SuggestionViewerData, config: Config):
        self.notifier = notifier
        self.data = data

        self.config = config
        self._update_render_type()

    @classmethod
    async def from_state(cls, notifier: NotifierService, state: FSMContext, config: Config):
        state_data = await state.get_data()
        viewer_data = state_data.get("viewer_data")
        return cls(notifier, viewer_data, config)

    @classmethod
    def from_data(cls, notifier: NotifierService, viewer_data: SuggestionViewerData, config: Config):
        return cls(notifier, viewer_data, config)

    def _get_i18n_kwargs(self):
        suggestion_dto = self.data.suggestion_dto
        
        i18n_key = "none_suggestion"
        if suggestion_dto.accepted is not None:
            i18n_key = "bool_suggestion_true" if suggestion_dto.accepted else "bool_suggestion_false"

        verdict = self.notifier.get_translated_text(i18n_key)
        author_plus_origin = self.notifier.get_i18n_text(
            i18n_key="author_plus_origin", i18n_kwargs={
                "author_name": suggestion_dto.author.name,
                "forwarded_from": suggestion_dto.forwarded_from,
            }
        )

        i18n_kwargs = {
            "author_username": suggestion_dto.author.username,
            "author_name": suggestion_dto.author.name,
            "author_string": author_plus_origin if suggestion_dto.forwarded_from else suggestion_dto.author.name,
            "author_id": suggestion_dto.author_id,
            "suggestion_id": suggestion_dto.id,
            "original_caption": suggestion_dto.caption,
            "forwarded_from": suggestion_dto.forwarded_from,
            "author_plus_origin": author_plus_origin,
            "verdict": verdict,
            "bot_url": self.config.runtime_config.bot_url,
        }
        return i18n_kwargs

    def _update_render_type(self):
        suggestion_dto = self.data.suggestion_dto

        render_type = (
            RenderType.MESSAGE 
            if not suggestion_dto.media and suggestion_dto.caption else
            RenderType.MEDIAGROUP
        )

        self.data = self.data.model_copy(
            update={"render_type": render_type}
        )

    def _build_media_group_payload(self, i18n_key="admin_get_suggestion_caption"):
        suggestion_dto = self.data.suggestion_dto
        notifier = self.notifier

        media_group = get_media_group(
            suggestion_dto.media, suggestion_dto.media_group_id
        )

        i18n_kwargs = self._get_i18n_kwargs()
        translated = notifier.get_translated_text(i18n_key)
        suggestion_caption = notifier.get_formatted_text(translated, i18n_kwargs)

        media_group.caption = suggestion_caption

        payload = MessagePayload(content=media_group.build())
        return payload

    async def render_send_verdict(self, i18n_key="send_verdict"):
        payload = MessagePayload(i18n_key=i18n_key, reply_markup=get_viewer_accept_decline_kb())
        await self.notifier.notify_user(self.data.user_dto, payload)

    async def render_verdict_rewrite(self):
        notifier = self.notifier
        user_dto = self.data.user_dto

        kb = get_main_kb_by_role(user_dto.role)
        payload = MessagePayload(i18n_key="verdict_rewrite", reply_markup=kb)
        await notifier.notify_user(user_dto, payload)

    async def render_suggestion(self):
        notifier = self.notifier
        user_dto = self.data.user_dto

        match self.data.render_type:
            case RenderType.MESSAGE:
                payload = MessagePayload(
                    i18n_key="admin_get_suggestion_caption",
                    i18n_kwargs=self._get_i18n_kwargs(),
                    reply_markup=get_viewer_accept_decline_kb(),
                )
            case RenderType.MEDIAGROUP:
                payload = self._build_media_group_payload()

        return await notifier.notify_user(user_dto, payload)

    async def update_state_data(self, state: FSMContext):
        self._update_render_type()
        await state.set_data(
            {"viewer_data": self.data}
        )

    async def _post_in_channel(self, with_caption: bool = True):
        notifier = self.notifier
        channel_id = self.data.channel_id

        i18n_key = "channel_post_message"
        i18n_key = i18n_key if with_caption else f"{i18n_key}_no_caption"
        i18n_kwargs = self._get_i18n_kwargs()

        match self.data.render_type:
            case RenderType.MESSAGE:
                payload = MessagePayload(i18n_key=i18n_key, i18n_kwargs=i18n_kwargs)
            case RenderType.MEDIAGROUP:
                payload = self._build_media_group_payload(i18n_key)
        
        return await notifier.send_channel(channel_id, payload)
    
    async def notify_author(self, status):
        i18n_kwargs = self._get_i18n_kwargs()

        i18n_key = "bool_suggestion_true" if status else "bool_suggestion_false"
        verdict = self.notifier.get_translated_text(i18n_key)
        i18n_kwargs["verdict"] = verdict

        payload = MessagePayload(
            i18n_key="notify_author_suggestion_status",
            i18n_kwargs=i18n_kwargs,
        )

        await self.notifier.notify_user(
            self.data.suggestion_dto.author, payload
        )

    async def post_in_channel(self, viewer_action: ViewerAdminAction):
        suggestion_dto = self.data.suggestion_dto
        user_dto = self.data.user_dto
        notifier = self.notifier

        with_caption = True
        if viewer_action == ViewerAdminAction.ACCEPT_NO_CAPTION or \
            not suggestion_dto.caption:
            with_caption = False
            
        if not with_caption and not suggestion_dto.media:
            payload = MessagePayload(i18n_key="error_empty_suggestion")
            await notifier.notify_user(user_dto, payload=payload)
            return False
        
        await self._post_in_channel(with_caption)
        return True

    async def render_verdict_exists(self):
        suggestion_dto = self.data.suggestion_dto
        user_dto = self.data.user_dto
        notifier = self.notifier

        i18n_kwargs = {
            "id": f"{suggestion_dto.id}",
            "verdict": f"{suggestion_dto.accepted}",
        }

        payload = MessagePayload(i18n_key="suggestion_verdict_exists", i18n_kwargs=i18n_kwargs)
        await notifier.notify_user(user_dto, payload)

    async def render_no_active_suggestions(self):
        notifier = self.notifier
        user_dto = self.data.user_dto

        kb = get_main_kb_by_role(user_dto.role)
        payload = MessagePayload(i18n_key="no_active_suggestions", reply_markup=kb)
        return await notifier.notify_user(user_dto, payload)

    async def go_next(
        self,
        session: AsyncSession,
        state: FSMContext
    ):
        new_active = await SuggestionDAO.get_active(session)
        if not new_active:
            await state.clear()
            return await self.render_no_active_suggestions()
        
        # Update
        new_active_dto = SuggestionFullDTO.model_validate(new_active)
        self.data = self.data.model_copy(
            update={"suggestion_dto": new_active_dto}
        )

        await self.update_state_data(state)
        await self.render_suggestion()

        logger.debug(
            "SuggestionViewerRenderer render next suggestion ID %s", new_active_dto.id
        )
