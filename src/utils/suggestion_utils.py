from aiogram.utils.media_group import MediaGroupBuilder

from core.html import quote
from core.i18n_translator import Translator
from database.dto import SuggestionFullDTO, UserBotDTO


class SuggestionUtils:
    __slots__ = (
        "_userbot_dto",
        "_translator",
    )

    def __init__(
        self,
        userbot_dto: UserBotDTO,
        translator: Translator,
    ):
        self._userbot_dto = userbot_dto
        self._translator = translator

    def _get_verdict(self, suggestion_dto: SuggestionFullDTO):
        status = suggestion_dto.status.value
        i18n_key = f"suggestion_status_{status}".lower()
        return self._translator.translate(i18n_key)

    def _get_author_plus_origin(self, dto: SuggestionFullDTO):
        author = dto.author
        is_anon = dto.anonymous
        author_name = "Anonymous" if is_anon else quote(author.name)

        i18n_kwargs = dict(author_name=author_name, forwarded_from=quote(dto.forwarded_from))
        return self._translator.i18n_text(i18n_key="author_plus_origin", i18n_kwargs=i18n_kwargs)

    def get_input_media(self, dto: SuggestionFullDTO, i18n_key: str, i18n_kwargs: dict):
        caption = self._translator.i18n_text(i18n_key, i18n_kwargs)
        mediagroup = MediaGroupBuilder(caption=caption)
        for media in dto.media:
            mediagroup.add(type=media.filetype, media=media.telegram_file_id)
        return mediagroup.build()

    def get_i18n_kwargs(self, dto: SuggestionFullDTO):
        verdict = self._get_verdict(dto)

        author_string = "Anonymous" if dto.anonymous else quote(dto.author.name)
        if dto.forwarded_from:
            author_string = self._get_author_plus_origin(dto)

        i18n_kwargs = dto.to_i18n_kwargs()
        i18n_kwargs.update(
            author_string=author_string,
            verdict=verdict,
            bot_url=self._userbot_dto.bot_url,
        )

        return i18n_kwargs
