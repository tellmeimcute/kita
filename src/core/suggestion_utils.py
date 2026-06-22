
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
        return self.translator.get_translated_text(i18n_key)

    def _get_author_plus_origin(self, dto: SuggestionFullDTO):
        author = dto.author
        is_anon = dto.anonymous
        author_name = "Anonymous" if is_anon else author.name

        i18n_kwargs = dict(author_name=author_name, forwarded_from=dto.forwarded_from)
        return self.translator.get_i18n_text(
            i18n_key="author_plus_origin", i18n_kwargs=i18n_kwargs
        )

    def _get_media_group(self, suggestion_dto: SuggestionFullDTO) -> MediaGroupBuilder:
        media_group = MediaGroupBuilder()
        for media in suggestion_dto.media:
            media_group.add(type=media.filetype, media=media.telegram_file_id)
        return media_group

    def get_i18n_kwargs(self, dto: SuggestionFullDTO):
        verdict = self._get_verdict(dto)

        author_plus_origin = self._get_author_plus_origin(dto)
        author_string = author_plus_origin if dto.forwarded_from else dto.author.name

        caption = dto.caption if dto.caption else ""

        i18n_kwargs = dto.to_i18n_kwargs()
        i18n_kwargs.update(
            author_plus_origin=author_plus_origin,
            author_string=author_string,
            caption=caption,
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
                suggestion_id=dto.id,
                reply_markup=kb,
            )

        if dto.render_type == RenderType.MEDIAGROUP:
            media_group: MediaGroupBuilder = self._get_media_group(dto)
            media_group.caption = self.translator.get_i18n_text(i18n_key, i18n_kwargs)
            return MessagePayload(mediagroup=media_group.build(), suggestion_id=dto.id)