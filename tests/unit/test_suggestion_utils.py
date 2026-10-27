from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from aiogram.types import InputMediaPhoto, InputMediaVideo

from core.consts import T_ME
from database.dto import MediaDTO, SuggestionFullDTO, UserBotDTO, UserDTO
from database.enums import SuggestionStatus
from utils.suggestion_utils import SuggestionUtils

USER_ID = 1000
MOMENT = datetime(2024, 5, 1, 10, 30, tzinfo=UTC)
DATE_FORMAT = "%d/%m/%Y, %H:%M:%S"

TRANSLATIONS = {
    "suggestion_status_pending": "Pending",
    "suggestion_status_accepted": "Accepted",
    "suggestion_status_declined": "Declined",
    "author_plus_origin": "{author_name} via {forwarded_from}",
    "media_input": "Suggestion: {caption}",
}


class FakeTranslator:
    def translate(self, i18n_key: str) -> str:
        return TRANSLATIONS[i18n_key]

    def i18n_text(self, i18n_key: str, i18n_kwargs: dict) -> str:
        return TRANSLATIONS[i18n_key].format(**i18n_kwargs)


@pytest.fixture
def userbot_dto() -> UserBotDTO:
    return UserBotDTO(
        token="123456789:token",
        bot_id=123456789,
        username="suggestion_bot",
        owner_id=USER_ID,
        channel_id=-100123456789,
        channel_name="Channel",
        active=True,
        banned=False,
    )


@pytest.fixture
def author() -> UserDTO:
    return UserDTO(
        user_id=USER_ID,
        username="author",
        name="<b>Ann</b>",
        language_code="ru",
        created_at=MOMENT,
        updated_at=MOMENT,
    )


@pytest.fixture
def suggestion_utils(userbot_dto: UserBotDTO) -> SuggestionUtils:
    return SuggestionUtils(userbot_dto, FakeTranslator())


@pytest.fixture
def make_suggestion(author: UserDTO) -> Callable[..., SuggestionFullDTO]:
    def _make_suggestion(**kwargs) -> SuggestionFullDTO:
        default_kwargs = {
            "id": 1,
            "author_id": author.user_id,
            "status": SuggestionStatus.PENDING,
            "caption": "caption",
            "media_group_id": None,
            "forwarded_from": None,
            "anonymous": False,
            "author": author,
            "created_at": MOMENT,
            "updated_at": MOMENT,
        }
        default_kwargs.update(kwargs)

        return SuggestionFullDTO(**default_kwargs)

    return _make_suggestion


@pytest.mark.parametrize("status", list(SuggestionStatus))
def test_verdict_uses_status_translation(
    suggestion_utils: SuggestionUtils,
    make_suggestion: Callable[..., SuggestionFullDTO],
    status: SuggestionStatus,
):
    kwargs = suggestion_utils.get_i18n_kwargs(make_suggestion(status=status))

    assert kwargs["verdict"] == TRANSLATIONS[f"suggestion_status_{status.value.lower()}"]


def test_author_name_is_escaped(
    suggestion_utils: SuggestionUtils,
    make_suggestion: Callable[..., SuggestionFullDTO],
):
    kwargs = suggestion_utils.get_i18n_kwargs(make_suggestion())

    assert kwargs["author_string"] == "&lt;b&gt;Ann&lt;/b&gt;"


def test_anonymous_hides_author_name(
    suggestion_utils: SuggestionUtils,
    make_suggestion: Callable[..., SuggestionFullDTO],
    author: UserDTO,
):
    kwargs = suggestion_utils.get_i18n_kwargs(make_suggestion(anonymous=True))

    assert kwargs["author_string"] == "Anonymous"
    assert author.name not in kwargs["author_string"]


def test_forwarded_from_adds_origin(
    suggestion_utils: SuggestionUtils,
    make_suggestion: Callable[..., SuggestionFullDTO],
):
    kwargs = suggestion_utils.get_i18n_kwargs(make_suggestion(forwarded_from="Source & Co"))

    assert kwargs["author_string"] == "&lt;b&gt;Ann&lt;/b&gt; via Source &amp; Co"


def test_anonymous_with_origin_hides_author_name(
    suggestion_utils: SuggestionUtils,
    make_suggestion: Callable[..., SuggestionFullDTO],
):
    kwargs = suggestion_utils.get_i18n_kwargs(
        make_suggestion(anonymous=True, forwarded_from="Source")
    )

    assert kwargs["author_string"] == "Anonymous via Source"


def test_kwargs_carry_suggestion_and_userbot_fields(
    suggestion_utils: SuggestionUtils,
    make_suggestion: Callable[..., SuggestionFullDTO],
    userbot_dto: UserBotDTO,
):
    suggestion = make_suggestion()

    kwargs = suggestion_utils.get_i18n_kwargs(suggestion)

    assert kwargs["id"] == suggestion.id
    assert kwargs["bot_url"] == T_ME + userbot_dto.username
    assert kwargs["created_at"] == MOMENT.strftime(DATE_FORMAT)
    assert kwargs["updated_at"] == MOMENT.strftime(DATE_FORMAT)
    assert kwargs["author"]["name"] == "&lt;b&gt;Ann&lt;/b&gt;"
    assert kwargs["author"]["username"] == "@author"


def test_caption_and_origin_are_escaped(
    suggestion_utils: SuggestionUtils,
    make_suggestion: Callable[..., SuggestionFullDTO],
):
    kwargs = suggestion_utils.get_i18n_kwargs(
        make_suggestion(caption="<i>look</i>", forwarded_from="<b>chan</b>")
    )

    assert kwargs["caption"] == "&lt;i&gt;look&lt;/i&gt;"
    assert kwargs["forwarded_from"] == "&lt;b&gt;chan&lt;/b&gt;"


def test_missing_caption_and_origin(
    suggestion_utils: SuggestionUtils,
    make_suggestion: Callable[..., SuggestionFullDTO],
):
    kwargs = suggestion_utils.get_i18n_kwargs(make_suggestion(caption=None, forwarded_from=None))

    assert kwargs["caption"] == ""  # noqa: PLC1901
    assert kwargs["forwarded_from"] is None


def test_input_media_builds_media_group(
    suggestion_utils: SuggestionUtils,
    make_suggestion: Callable[..., SuggestionFullDTO],
):
    suggestion = make_suggestion(
        media=[
            MediaDTO(id=1, filetype="photo", telegram_file_id="photo-1"),
            MediaDTO(id=2, filetype="video", telegram_file_id="video-1"),
        ]
    )

    media_group = suggestion_utils.get_input_media(
        suggestion,
        i18n_key="media_input",
        i18n_kwargs={"caption": "look at this"},
    )

    assert [type(item) for item in media_group] == [InputMediaPhoto, InputMediaVideo]
    assert [item.media for item in media_group] == ["photo-1", "video-1"]

    assert media_group[0].caption == "Suggestion: look at this"
    assert media_group[1].caption is None


def test_input_media_without_media_is_empty(
    suggestion_utils: SuggestionUtils,
    make_suggestion: Callable[..., SuggestionFullDTO],
):
    media_group = suggestion_utils.get_input_media(
        make_suggestion(media=[]),
        i18n_key="media_input",
        i18n_kwargs={"caption": "text only"},
    )

    assert media_group == []
