
from aiogram import html
from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.media_group import MediaGroupBuilder

from core.config import RuntimeConfig
from core.enums import RenderType
from core.exceptions import UnsupportedPayload
from core.i18n_translator import Translator
from core.schemas.message_payload import MessagePayload

from database.dto import SuggestionFullDTO

class SuggestionUtils:
    def __init__(self, runtime_config: RuntimeConfig, translator: Translator):
        self.runtime_config = runtime_config
        self.translator = translator

    def _get_verdict(self, suggestion_dto: SuggestionFullDTO):
        status = suggestion_dto.status.value
        i18n_key = f"suggestion_status_{status}".lower()
        return self.translator.translate(i18n_key)

    def _get_author_plus_origin(self, dto: SuggestionFullDTO):
        author = dto.author
        is_anon = dto.anonymous
        author_name = "Anonymous" if is_anon else author.name

        i18n_kwargs = dict(author_name=author_name, forwarded_from=dto.forwarded_from)
        return self.translator.i18n_text(
            i18n_key="author_plus_origin", i18n_kwargs=i18n_kwargs
        )

    def _get_input_media(self, dto: SuggestionFullDTO, i18n_key: str, i18n_kwargs: dict):
        caption = self.translator.i18n_text(i18n_key, i18n_kwargs)
        mediagroup = MediaGroupBuilder(caption=caption)
        for media in dto.media:
            mediagroup.add(type=media.filetype, media=media.telegram_file_id)
        return mediagroup.build()

    def get_i18n_kwargs(self, dto: SuggestionFullDTO):
        verdict = self._get_verdict(dto)

        author_plus_origin = self._get_author_plus_origin(dto)
        author_string = author_plus_origin if dto.forwarded_from else dto.author.name

        i18n_kwargs = dto.to_i18n_kwargs()
        i18n_kwargs.update(
            author_plus_origin=author_plus_origin,
            author_string=author_string,
            verdict=verdict,
            bot_url=self.runtime_config.bot_url,
        )

        return i18n_kwargs

    def payload_factory(
        self,
        dto: SuggestionFullDTO,
        i18n_key: str,
        kb: ReplyKeyboardMarkup | None = None,
    ):
        if dto.render_type not in (RenderType.MESSAGE, RenderType.MEDIAGROUP):
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