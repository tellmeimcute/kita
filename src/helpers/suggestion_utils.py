
from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.media_group import MediaGroupBuilder

from core.config import RuntimeConfig
from database.dto import SuggestionFullDTO, SUGGESTION_DTOS
from core.i18n_translator import Translator
from core.enums import RenderType
from helpers.schemas.message_payload import MessagePayload


class SuggestionUtils:
    def __init__(self, runtime_config: RuntimeConfig, translator: Translator):
        self.runtime_config = runtime_config
        self.translator = translator

    def get_verdict(self, suggestion_dto: SUGGESTION_DTOS):
        i18n_key = "none_suggestion"
        if suggestion_dto.accepted is not None:
            i18n_key = (
                "bool_suggestion_true" if suggestion_dto.accepted else "bool_suggestion_false"
            )
        return self.translator.get_translated_text(i18n_key)

    def get_author_plus_origin(self, suggestion_dto: SUGGESTION_DTOS):
        return self.translator.get_i18n_text(
            i18n_key="author_plus_origin",
            i18n_kwargs={
                "author_name": suggestion_dto.author.name,
                "forwarded_from": suggestion_dto.forwarded_from,
            },
        )

    def admin_original_caption(self, caption: str):
        return self.translator.get_i18n_text(
            i18n_key="admin_suggestion_original_caption",
            i18n_kwargs={"caption": caption},
        )

    def get_i18n_kwargs(self, suggestion_dto: SuggestionFullDTO):
        verdict = self.get_verdict(suggestion_dto)
        author_plus_origin = self.get_author_plus_origin(suggestion_dto)
        author_string = (
            author_plus_origin if suggestion_dto.forwarded_from else suggestion_dto.author.name
        )

        caption = suggestion_dto.caption if suggestion_dto.caption else ""
        admin_caption = self.admin_original_caption(caption) if suggestion_dto.caption else ""

        i18n_kwargs = suggestion_dto.model_dump()
        i18n_kwargs.update(
            author_plus_origin=author_plus_origin,
            author_string=author_string,
            caption=caption,
            admin_caption=admin_caption,
            verdict=verdict,
            bot_url=self.runtime_config.bot_url,
        )

        return i18n_kwargs

    def get_media_group(self, suggestion_dto: SuggestionFullDTO) -> MediaGroupBuilder:
        media_group = MediaGroupBuilder()

        for media in suggestion_dto.media:
            media_group.add(type=media.filetype, media=media.telegram_file_id)

        return media_group

    def build_mediagroup_content(self, suggestion_dto: SuggestionFullDTO, i18n_key: str):
        media_group: MediaGroupBuilder = self.get_media_group(suggestion_dto)
        
        i18n_kwargs = self.get_i18n_kwargs(suggestion_dto)
        media_group.caption = self.translator.get_i18n_text(i18n_key, i18n_kwargs)
        return media_group.build()
    
    def payload_factory(
        self,
        suggestion_dto: SuggestionFullDTO,
        i18n_key: str,
        kb: ReplyKeyboardMarkup | None = None,
    ):
        render_type = suggestion_dto.render_type
        i18n_kwargs = self.get_i18n_kwargs(suggestion_dto)

        payload = None

        if render_type == RenderType.MESSAGE:
            payload = MessagePayload(i18n_key=i18n_key, i18n_kwargs=i18n_kwargs, reply_markup=kb)
        elif render_type == RenderType.MEDIAGROUP:
            content = self.build_mediagroup_content(suggestion_dto, i18n_key=i18n_key)
            payload = MessagePayload(content=content)

        if not payload:
            raise ValueError("Unsupported render_type")

        return payload