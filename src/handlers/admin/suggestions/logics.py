from logging import getLogger

from aiogram import html
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao import SuggestionDAO
from database.dto import SuggestionFullDTO
from handlers.keyboards import get_accept_decline_kb, get_main_kb_by_role
from helpers.enums import RenderType, ViewerAdminAction
from helpers.message_payload import MessagePayload
from helpers.schemas import SuggestionViewerData
from helpers.utils import get_media_group
from services.notifier import Notifier

logger = getLogger("admin_suggestions")

class SuggestionViewerRenderer:
    def __init__(self, notifier: Notifier, data: SuggestionViewerData):
        self.notifier = notifier
        self.data = data

        self._update_render_type()

    def _update_render_type(self):
        suggestion_dto = self.data.suggestion_dto
        if not suggestion_dto.media and suggestion_dto.caption:
            self.data.render_type = RenderType.MESSAGE
        else:
            self.data.render_type = RenderType.MEDIAGROUP

    @classmethod
    async def from_state(cls, notifier: Notifier, state: FSMContext):
        state_data = await state.get_data()
        viewer_data = state_data.get("viewer_data")
        return cls(notifier, viewer_data)

    @classmethod
    async def from_data(cls, notifier: Notifier, viewer_data):
        return cls(notifier, viewer_data)

    def _get_i18n_kwargs(self):
        suggestion_dto = self.data.suggestion_dto
        i18n_kwargs = {
            "author_username": html.bold(suggestion_dto.author.username),
            "author_id": suggestion_dto.author_id,
            "suggestion_id": suggestion_dto.id,
            "original_caption": suggestion_dto.caption,
            "verdict": suggestion_dto.accepted,
        }
        return i18n_kwargs

    async def _render_message(self, i18n_key="admin_get_suggestion_caption"):
        kb = get_accept_decline_kb()
        i18n_kwargs = self._get_i18n_kwargs()
        payload = MessagePayload(
            i18n_key=i18n_key, i18n_kwargs=i18n_kwargs, reply_markup=kb
        )

        return payload

    async def _render_media_group(self, i18n_key="admin_get_suggestion_caption"):
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
        payload = MessagePayload(i18n_key=i18n_key, reply_markup=get_accept_decline_kb())
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
                payload = await self._render_message()
            case RenderType.MEDIAGROUP:
                payload = await self._render_media_group()

        return await notifier.notify_user(user_dto, payload)

    async def update_state_data(self, state: FSMContext):
        self._update_render_type()
        await state.set_data(
            {"viewer_data": self.data}
        )

    async def _post_in_channel(self, with_caption: bool = True):
        notifier = self.notifier
        channel_id = self.data.channel_id

        match self.data.render_type:
            case RenderType.MESSAGE:
                i18n_key = "channel_post_message" if with_caption else "channel_post_message_no_caption"
                payload = await self._render_message(i18n_key)
            case RenderType.MEDIAGROUP:
                i18n_key = "channel_post_mediagroup" if with_caption else "channel_post_mediagroup_no_caption"
                payload = await self._render_media_group(i18n_key)
        
        return await notifier.send_channel(channel_id, payload)
    
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
            "id": html.bold(f"{suggestion_dto.id}"),
            "verdict": html.bold(f"{suggestion_dto.accepted}"),
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
        self.data.suggestion_dto = new_active_dto
        await self.update_state_data(state)
        await self.render_suggestion()
