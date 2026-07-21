
from typing import Literal

from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.media_group import MediaGroupBuilder

from core.schemas import BotInfo
from core.enums import RenderType
from core.exceptions import UnsupportedPayload
from core.i18n_translator import Translator
from core.schemas.message_payload import MessagePayload
from database.dto import SuggestionFullDTO

class SuggestionUtils:

    __slots__ = (
        "_bot_info",
        "_translator",
    )

    def __init__(
        self,
        bot_info: BotInfo,
        translator: Translator,
    ):
        self._bot_info = bot_info
        self._translator = translator

    def _get_verdict(self, suggestion_dto: SuggestionFullDTO):
        status = suggestion_dto.status.value
        i18n_key = f"suggestion_status_{status}".lower()
        return self._translator.translate(i18n_key)

    def _get_author_plus_origin(self, dto: SuggestionFullDTO):
        author = dto.author
        is_anon = dto.anonymous
        author_name = "Anonymous" if is_anon else author.name

        i18n_kwargs = dict(author_name=author_name, forwarded_from=dto.forwarded_from)
        return self._translator.i18n_text(
            i18n_key="author_plus_origin", i18n_kwargs=i18n_kwargs
        )

    def _get_input_media(self, dto: SuggestionFullDTO, i18n_key: str, i18n_kwargs: dict):
        caption = self._translator.i18n_text(i18n_key, i18n_kwargs)
        mediagroup = MediaGroupBuilder(caption=caption)
        for media in dto.media:
            mediagroup.add(type=media.filetype, media=media.telegram_file_id)
        return mediagroup.build()

    def get_i18n_kwargs(self, dto: SuggestionFullDTO):
        verdict = self._get_verdict(dto)

        author_string = "Anonymous" if dto.anonymous else dto.author.name
        if dto.forwarded_from:
            author_string = self._get_author_plus_origin(dto)

        i18n_kwargs = dto.to_i18n_kwargs()
        i18n_kwargs.update(
            author_string=author_string,
            verdict=verdict,
            bot_url=self._bot_info.bot_url,
        )

        return i18n_kwargs

    def payload_factory(
        self,
        dto: SuggestionFullDTO,
        i18n_key: Literal["suggestion_caption", "channel_post_message"] = "suggestion_caption",
        kb: ReplyKeyboardMarkup | None = None,
    ):
        if dto.render_type not in {RenderType.MESSAGE, RenderType.MEDIAGROUP}:
            raise UnsupportedPayload

        i18n_kwargs = self.get_i18n_kwargs(dto)
        
        if dto.render_type == RenderType.MESSAGE:
            return MessagePayload(
                i18n_key=i18n_key,
                i18n_kwargs=i18n_kwargs,
                reply_markup=kb,
            )

        if dto.render_type == RenderType.MEDIAGROUP:
            media = self._get_input_media(dto, i18n_key, i18n_kwargs)
            return MessagePayload(media=media)