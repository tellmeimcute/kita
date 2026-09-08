from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatFullInfo, User
from aiogram.utils.i18n import I18n
from cryptography.fernet import Fernet

from core.cryptographer import Cryptographer
from core.i18n_translator import Translator
from database.dto import SuggestionFullDTO, UserDTO, UserProfileDTO
from database.enums import SuggestionStatus
from services.bot_registry import BotRegistry


@pytest.fixture
def test_user_dto() -> UserDTO:
    return UserDTO(
        user_id=2131,
        username="test_user",
        name="testing",
        language_code="ru",
    )


@pytest.fixture
def test_profile_dto(mock_bot, test_user_dto) -> UserProfileDTO:
    return UserProfileDTO(
        bot_id=mock_bot.id,
        user_id=test_user_dto.user_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def test_suggestion(test_user_dto) -> SuggestionFullDTO:
    return SuggestionFullDTO(
        id=1,
        author_id=test_user_dto.user_id,
        status=SuggestionStatus.PENDING,
        caption="test_test",
        media_group_id=None,
        forwarded_from=None,
        anonymous=False,
        author=test_user_dto,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_channel():
    channel = MagicMock(spec=ChatFullInfo)
    channel.id = 123456789

    return channel


@pytest.fixture
def mock_bot(mock_channel):
    bot = MagicMock(spec=Bot)
    bot.id = 666
    bot.token = "666:valid_token"
    bot.send_message = AsyncMock(return_value=MagicMock())
    bot.send_media_group = AsyncMock(return_value=[MagicMock()])
    bot.forward_messages = AsyncMock(return_value=[MagicMock()])
    bot.copy_messages = AsyncMock(return_value=[MagicMock()])
    bot.edit_message_text = AsyncMock(return_value=MagicMock())

    user = MagicMock(spec=User)
    bot.get_me = AsyncMock(return_value=user)
    bot.__aenter__ = AsyncMock(return_value=bot)
    bot.__aexit__ = AsyncMock(return_value=False)

    bot.get_chat = AsyncMock(return_value=mock_channel)
    bot.get_chat_member = AsyncMock(
        return_value=MagicMock(status=ChatMemberStatus.ADMINISTRATOR, can_post_messages=True)
    )

    return bot


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.proxy = "http://proxy.example.com:8080"
    config.bot_cache_max_size = 10

    config.webhook_secret.get_secret_value.return_value = "test-master-secret"
    config.encryption_key.get_secret_value.return_value = Fernet.generate_key().decode()

    config.rate_limit = MagicMock()
    config.rate_limit.model_dump.return_value = {"max_tokens": 5, "refill_rate": 0.3}

    return config


@pytest.fixture
def cryptographer(mock_config):
    return Cryptographer(mock_config)


@pytest.fixture
def mock_cryptographer():
    return MagicMock(spec=Cryptographer)


@pytest.fixture
def mock_bot_registry(mock_bot):
    registry = MagicMock()
    registry.get_current.return_value = mock_bot
    return registry


@pytest.fixture
def registry(mock_config):
    return BotRegistry(mock_config)


@pytest.fixture
def mock_redis():
    return AsyncMock()


@pytest.fixture
def mock_i18n():
    return MagicMock(spec=I18n)


@pytest.fixture
def mock_fsm():
    return AsyncMock()


@pytest.fixture
def mock_translator():
    translator = MagicMock(spec=Translator)
    translator.translate.return_value = "rate limited warning text"
    return translator
