
from aiogram import html
from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.media_group import MediaGroupBuilder

from core.config import RuntimeConfig
from core.enums import RenderType
from core.exceptions import UnsupportedPayload
from core.i18n_translator import Translator
from core.schemas.message_payload import MessagePayload

from database.dto import SuggestionFullDTO
from database.enums import SuggestionStatus

class SuggestionUtils:
    def __init__(self, runtime_config: RuntimeConfig, translator: Translator):
        self.runtime_config = runtime_config
        self.translator = translator

    def get_verdict(self, suggestion_dto: SuggestionFullDTO):
        i18n_key = "none_suggestion"
        if suggestion_dto.status != SuggestionStatus.PENDING:
            is_accepted = suggestion_dto.status == SuggestionStatus.ACCEPTED
            i18n_key = (
                "bool_suggestion_true" if is_accepted else "bool_suggestion_false"
            )
        return self.translator.get_translated_text(i18n_key)

    def get_author_plus_origin(self, suggestion_dto: SuggestionFullDTO):
        author = suggestion_dto.author
        is_anon = suggestion_dto.anonymous
        author_name = "Anonymous" if is_anon else author.name

        return self.translator.get_i18n_text(
            i18n_key="author_plus_origin",
            i18n_kwargs={
                "author_name": author_name,
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

        command = self.translator.get_translated_text("command_open_solo_view")
        command = f"{command} {suggestion_dto.id}"

        i18n_kwargs = suggestion_dto.model_dump(
            include={"id", "caption", "status", "anonymous", "media_group_id", "forwarded_from", "author"}
        )
        i18n_kwargs.update(
            author_plus_origin=author_plus_origin,
            author_string=author_string,
            caption=caption,
            admin_caption=admin_caption,
            command=html.code(command),
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

        if render_type == RenderType.MESSAGE:
            i18n_kwargs = self.get_i18n_kwargs(suggestion_dto)
            return MessagePayload(
                i18n_key=i18n_key,
                i18n_kwargs=i18n_kwargs,
                suggestion_id=suggestion_dto.id,
                reply_markup=kb,
            )

        if render_type == RenderType.MEDIAGROUP:
            content = self.build_mediagroup_content(suggestion_dto, i18n_key=i18n_key)
            return MessagePayload(mediagroup=content, suggestion_id=suggestion_dto.id)

        raise UnsupportedPayload()