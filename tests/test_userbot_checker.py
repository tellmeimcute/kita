from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramUnauthorizedError
from aiogram.types import ChatMemberAdministrator

from utils.userbot_checker import UserBotChecker

# Constants
TEST_CHANNEL_ID = "123456789"
EXPECTED_CHANNEL_ID = -100123456789


class TestUserBotChecker:
    @pytest.fixture
    def checker(self):
        return UserBotChecker()

    def test_get_channel_id_with_at(self, checker):
        result = checker.get_channel_id("@mychannel")
        assert result == "@mychannel"

    def test_get_channel_id_without_prefix(self, checker):
        result = checker.get_channel_id(TEST_CHANNEL_ID)
        assert result == EXPECTED_CHANNEL_ID

    def test_get_channel_id_trims_whitespace(self, checker):
        result = checker.get_channel_id(f"  {TEST_CHANNEL_ID}  ")
        assert result == EXPECTED_CHANNEL_ID

    def test_get_channel_id_non_numeric_raises(self, checker):
        with pytest.raises(ValueError):
            checker.get_channel_id("not-a-number")

    async def test_check_token_invalid_format(self, checker):
        result = await checker.check_token(None, "invalid_token", {})

        assert result.success is False
        assert result.detail_i18n_key == "reg_bot_token_invalid"

    async def test_check_token_bot_id_mismatch(self, checker):
        result = await checker.check_token(999, "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw", {})

        assert result.success is False
        assert result.detail_i18n_key == "reg_bot_token_from_another_bot"

    @patch("utils.userbot_checker.Bot")
    async def test_check_token_success(self, mock_bot_cls, mock_bot, checker):
        bot_token = mock_bot.token
        token_bot_id = mock_bot.id

        user = await mock_bot.get_me()
        mock_bot_cls.return_value = mock_bot

        result = await checker.check_token(token_bot_id, bot_token, {})

        assert result.success is True
        assert result.bot_info == user
        assert result.token == bot_token
        assert result.bot_id == token_bot_id
        mock_bot_cls.assert_called_once_with(token=bot_token)

    async def test_check_channel_rights_success(self, checker, mock_bot):
        mock_member = MagicMock(spec=ChatMemberAdministrator)
        mock_member.status = ChatMemberStatus.ADMINISTRATOR
        mock_member.can_post_messages = True
        mock_bot.get_chat_member = AsyncMock(return_value=mock_member)

        result = await checker.check_channel_rights(mock_bot, TEST_CHANNEL_ID)

        assert result == mock_member

    async def test_check_channel_rights_not_admin(self, checker, mock_bot):
        mock_member = MagicMock(spec=ChatMemberAdministrator)
        mock_member.status = ChatMemberStatus.ADMINISTRATOR
        mock_member.can_post_messages = False
        mock_bot.get_chat_member = AsyncMock(return_value=mock_member)

        result = await checker.check_channel_rights(mock_bot, TEST_CHANNEL_ID)

        assert result is None

    async def test_check_channel_rights_not_member(self, checker, mock_bot):
        mock_bot.get_chat_member = AsyncMock(
            side_effect=TelegramBadRequest(method="getChatMember", message="Chat not found")
        )

        result = await checker.check_channel_rights(mock_bot, TEST_CHANNEL_ID)

        assert result is None

    async def test_full_check_success(self, checker, mock_bot):
        result = await checker.full_check(mock_bot, TEST_CHANNEL_ID)

        assert result.success is True

    async def test_full_check_unauthorized(self, checker, mock_bot):
        mock_bot.get_me = AsyncMock(
            side_effect=TelegramUnauthorizedError(method="getMe", message="Unauthorized")
        )

        result = await checker.full_check(mock_bot, TEST_CHANNEL_ID)

        assert result.success is False
        assert result.detail_i18n_key == "reg_bot_token_invalid"

    async def test_full_check_bad_request(self, checker, mock_bot):
        mock_bot.get_chat = AsyncMock(
            side_effect=TelegramBadRequest(method="getChat", message="Chat not found")
        )

        result = await checker.full_check(mock_bot, TEST_CHANNEL_ID)

        assert result.success is False
        assert result.detail_i18n_key == "reg_bot_bad_request"

    async def test_full_check_no_admin_rights(self, checker, mock_bot):
        checker.check_channel_rights = AsyncMock(return_value=None)

        result = await checker.full_check(mock_bot, TEST_CHANNEL_ID)

        assert result.success is False
        assert result.detail_i18n_key == "reg_bot_permission_error"
