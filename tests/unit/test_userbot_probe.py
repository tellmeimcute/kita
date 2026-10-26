from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramUnauthorizedError

from core.exceptions import (
    BadRequestError,
    InsufficientPermissionsError,
    InvalidTokenError,
    NotAChannelError,
    TokenFromAnotherBotError,
)
from utils.userbot_probe import (
    parse_token,
    probe_token,
    probe_userbot,
    validate_channel_id,
)

TEST_CHANNEL_ID = "123456789"
EXPECTED_CHANNEL_ID = -100123456789
VALID_TOKEN = "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"


class TestValidateChannelId:
    def test_with_at(self):
        assert validate_channel_id("@mychannel") == "@mychannel"

    def test_without_prefix(self):
        assert validate_channel_id(TEST_CHANNEL_ID) == EXPECTED_CHANNEL_ID

    def test_trims_whitespace(self):
        assert validate_channel_id(f"  {TEST_CHANNEL_ID}  ") == EXPECTED_CHANNEL_ID

    def test_already_prefixed(self):
        assert validate_channel_id(str(EXPECTED_CHANNEL_ID)) == EXPECTED_CHANNEL_ID

    def test_non_numeric(self):
        assert validate_channel_id("not-a-number") is None

    def test_none(self):
        assert validate_channel_id(None) is None

    def test_blank(self):
        assert validate_channel_id("   ") is None


class TestParseToken:
    def test_valid(self):
        assert parse_token(VALID_TOKEN) == VALID_TOKEN

    def test_trims_whitespace(self):
        assert parse_token(f"  {VALID_TOKEN}  ") == VALID_TOKEN

    def test_invalid_format(self):
        with pytest.raises(InvalidTokenError):
            parse_token("invalid_token")

    def test_none(self):
        with pytest.raises(InvalidTokenError):
            parse_token(None)

    def test_bot_id_mismatch(self):
        with pytest.raises(TokenFromAnotherBotError):
            parse_token(VALID_TOKEN, expected_bot_id=999)

    def test_bot_id_match(self):
        assert parse_token(VALID_TOKEN, expected_bot_id=123456789) == VALID_TOKEN


class TestProbeToken:
    async def test_success(self, mock_bot):
        result = await probe_token(mock_bot)

        assert result == mock_bot.get_me.return_value

    async def test_unauthorized(self, mock_bot):
        mock_bot.get_me = AsyncMock(
            side_effect=TelegramUnauthorizedError(method="getMe", message="Unauthorized")
        )

        with pytest.raises(InvalidTokenError):
            await probe_token(mock_bot)


class TestProbeUserbot:
    async def test_success(self, mock_bot, mock_channel):
        mock_channel.type = "channel"

        result = await probe_userbot(mock_bot, TEST_CHANNEL_ID)

        assert result.ok is True
        assert result.error is None
        assert result.bot_info == mock_bot.get_me.return_value
        assert result.channel is mock_channel

    async def test_invalid_token(self, mock_bot):
        mock_bot.get_me = AsyncMock(
            side_effect=TelegramUnauthorizedError(method="getMe", message="Unauthorized")
        )

        result = await probe_userbot(mock_bot, TEST_CHANNEL_ID)

        assert result.ok is False
        assert isinstance(result.error, InvalidTokenError)
        assert result.bot_info is None

    async def test_bad_request(self, mock_bot):
        mock_bot.get_chat = AsyncMock(
            side_effect=TelegramBadRequest(method="getChat", message="Chat not found")
        )

        result = await probe_userbot(mock_bot, TEST_CHANNEL_ID)

        assert result.ok is False
        assert isinstance(result.error, BadRequestError)

    async def test_not_a_channel(self, mock_bot, mock_channel):
        mock_channel.type = "group"

        result = await probe_userbot(mock_bot, TEST_CHANNEL_ID)

        assert result.ok is False
        assert isinstance(result.error, NotAChannelError)

    async def test_no_post_permission(self, mock_bot, mock_channel):
        mock_channel.type = "channel"
        mock_bot.get_chat_member = AsyncMock(
            return_value=MagicMock(status=ChatMemberStatus.ADMINISTRATOR, can_post_messages=False)
        )

        result = await probe_userbot(mock_bot, TEST_CHANNEL_ID)

        assert result.ok is False
        assert isinstance(result.error, InsufficientPermissionsError)
