from unittest.mock import AsyncMock, MagicMock

import pytest

from core.consts import SUGGESTION_CAPTION_LIMIT, SUGGESTION_TEXT_LIMIT
from core.exceptions import UnsupportedPayload
from database.dto import SuggestionFullDTO
from services.suggestion import SuggestionService


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.create = AsyncMock()
    return repo


@pytest.fixture
def mock_parser():
    parser = MagicMock()
    parser.parse_forward_origin.return_value = "origin"
    parser.parse_media.return_value = MagicMock()
    return parser


@pytest.fixture
def service(mock_repo, mock_bot_registry, mock_parser):
    return SuggestionService(
        repo=mock_repo,
        bot_registry=mock_bot_registry,
        parser=mock_parser,
    )


@pytest.fixture
def make_message():
    def _make_message(
        caption: str | None = None,
        text: str | None = None,
        media_group_id: str | None = None,
    ) -> MagicMock:
        msg = MagicMock()
        msg.caption = caption
        msg.text = text
        msg.media_group_id = media_group_id
        return msg

    return _make_message


class TestSuggestionService:
    async def test_create_caption_too_long_with_media_raises(
        self, service, mock_parser, make_message
    ):
        mock_parser.parse_media.return_value = MagicMock()
        msg = make_message(caption="x" * (SUGGESTION_CAPTION_LIMIT + 1))

        with pytest.raises(UnsupportedPayload):
            await service.create(MagicMock(user_id=111), [msg])

    async def test_create_text_too_long_raises(self, service, mock_parser, make_message):
        mock_parser.parse_media.return_value = None
        msg = make_message(text="x" * (SUGGESTION_TEXT_LIMIT + 1))

        with pytest.raises(UnsupportedPayload):
            await service.create(MagicMock(user_id=111), [msg])

    async def test_create_text_at_limit_passes(
        self, service, mock_repo, mock_parser, make_message
    ):
        mock_parser.parse_media.return_value = None
        msg = make_message(caption="x" * SUGGESTION_TEXT_LIMIT)

        expected = MagicMock(spec=SuggestionFullDTO)
        mock_repo.create.return_value = expected

        result = await service.create(MagicMock(user_id=111), [msg])

        assert result == expected
