from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from core.exceptions import BotNotRegisteredError

TEST_BOT_ID = 12345
TEST_BOT_TOKEN = f"{TEST_BOT_ID}:245872673:AAF7VsJ1ksP4k0f9zk7NpF2nvxd69_ZlPyY"


class FakeClientSession:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


class TestBotRegistry:
    def test_initialization(self, registry):
        assert len(registry._storage) == 0
        assert registry._current_bot.get() is None

    def test_register_bot(self, registry, mock_bot):
        registry.register(mock_bot)

        assert mock_bot.id in registry._storage
        assert registry.get(mock_bot.id) == mock_bot

    def test_register_bot_eviction(self, registry, mock_config):
        mock_config.bot_cache_max_size = 3
        registry.cache_max_size = 3

        for i in range(5):
            bot = MagicMock()
            bot.id = i
            registry.register(bot)

        assert registry.get(0) is None
        assert registry.get(1) is None

    def test_get_bot_not_found(self, registry):
        assert registry.get(999) is None

    def test_get_or_create_cached(self, registry):
        mock_bot = MagicMock()
        mock_bot.id = TEST_BOT_ID
        mock_bot.token = "valid_token"
        registry.register(mock_bot)

        result = registry.get_or_create(TEST_BOT_ID, "valid_token")

        assert result == mock_bot

    @patch("services.bot_registry.Bot")
    def test_get_or_create_new_bot(self, mock_bot_cls, registry):
        mock_bot_cls.return_value.id = TEST_BOT_ID
        mock_bot_cls.return_value.token = f"{TEST_BOT_ID}:valid_token"

        result = registry.get_or_create(TEST_BOT_ID, f"{TEST_BOT_ID}:valid_token")

        assert result is not None
        assert TEST_BOT_ID in registry._storage
        mock_bot_cls.assert_called_once_with(
            token=f"{TEST_BOT_ID}:valid_token",
            session=registry._shared_session,
            default=registry._default,
        )

    @patch("services.bot_registry.Bot")
    def test_get_or_create_different_token_creates_new(self, mock_bot_cls, registry):
        mock_bot = MagicMock()
        mock_bot.id = TEST_BOT_ID
        mock_bot.token = f"{TEST_BOT_ID}:old_token"
        registry.register(mock_bot)

        mock_bot_cls.return_value.id = TEST_BOT_ID
        mock_bot_cls.return_value.token = f"{TEST_BOT_ID}:different_token"

        result = registry.get_or_create(TEST_BOT_ID, f"{TEST_BOT_ID}:different_token")

        assert result.token == f"{TEST_BOT_ID}:different_token"
        assert result.id == TEST_BOT_ID
        mock_bot_cls.assert_called_once_with(
            token=f"{TEST_BOT_ID}:different_token",
            session=registry._shared_session,
            default=registry._default,
        )

    def test_remove_bot(self, registry):
        mock_bot = MagicMock()
        mock_bot.id = TEST_BOT_ID
        registry.register(mock_bot)

        registry.remove(TEST_BOT_ID)

        assert registry.get(TEST_BOT_ID) is None

    def test_get_all(self, registry):
        all_test_count = 3
        for i in range(all_test_count):
            bot = MagicMock()
            bot.id = i
            registry.register(bot)

        all_bots = registry.get_all()

        assert len(all_bots) == all_test_count

    def test_set_get_reset_current(self, registry):
        mock_bot = MagicMock()
        mock_bot.id = TEST_BOT_ID

        token = registry.set_current(mock_bot)
        assert registry.get_current() == mock_bot

        registry.reset_current(token)
        assert registry.get_current() is None


class TestBotRegistryAsync:
    async def test_with_bot_context_manager(self, registry):
        mock_bot = MagicMock()
        mock_bot.id = TEST_BOT_ID
        registry.register(mock_bot)

        async with registry.with_bot(TEST_BOT_ID) as bot:
            assert registry.get_current() == bot
            assert bot.id == TEST_BOT_ID

        assert registry.get_current() is None

    async def test_with_bot_context_manager_cleans_up_on_exception(self, registry):
        mock_bot = MagicMock()
        mock_bot.id = TEST_BOT_ID
        registry.register(mock_bot)

        with pytest.raises(RuntimeError):
            async with registry.with_bot(TEST_BOT_ID) as bot:
                assert registry.get_current() == bot
                raise RuntimeError("test error")

        assert registry.get_current() is None

    async def test_with_bot_accepts_bot_instance(self, registry):
        bot = Bot(token=TEST_BOT_TOKEN)

        async with registry.with_bot(bot) as current:
            assert current is bot
            assert registry.get_current() is bot

        assert registry.get_current() is None

    async def test_with_bot_raises_for_unknown_bot(self, registry):
        with pytest.raises(BotNotRegisteredError) as error:
            async with registry.with_bot(TEST_BOT_ID):
                pass

        assert error.value.bot_id == TEST_BOT_ID
        assert registry.get_current() is None

    async def test_with_bot_with_token_creates_bot(self, registry):
        async with registry.with_bot(TEST_BOT_ID, token=TEST_BOT_TOKEN) as bot:
            assert isinstance(bot, Bot)
            assert bot.id == TEST_BOT_ID
            assert registry.get_current() is bot

        assert registry.get_current() is None

    async def test_close(self, registry):
        registry._shared_session.close = AsyncMock()

        await registry.close()

        registry._shared_session.close.assert_called_once()


class TestTempBot:
    async def test_temp_bot_gets_isolated_session(self, registry):
        async with (
            registry.temp_bot(TEST_BOT_TOKEN) as first,
            registry.temp_bot(TEST_BOT_TOKEN) as second,
        ):
            assert isinstance(first.session, AiohttpSession)
            assert first.session is not second.session
            assert first.session is not registry._shared_session

    async def test_temp_bot_uses_given_token(self, registry):
        async with registry.temp_bot(TEST_BOT_TOKEN) as tmp_bot:
            assert tmp_bot.token == TEST_BOT_TOKEN

    async def test_temp_bot_keeps_default_properties(self, registry):
        async with registry.temp_bot(TEST_BOT_TOKEN) as tmp_bot:
            assert isinstance(tmp_bot.default, DefaultBotProperties)
            assert tmp_bot.default.parse_mode == ParseMode.HTML

    async def test_temp_bot_keeps_configured_proxy(self, registry, mock_config):
        async with registry.temp_bot(TEST_BOT_TOKEN) as tmp_bot:
            assert tmp_bot.session._proxy == mock_config.proxy

    async def test_temp_bot_closing_does_not_close_shared_session(self, registry):
        shared_client_session = FakeClientSession()
        registry._shared_session._session = shared_client_session

        async with registry.temp_bot(TEST_BOT_TOKEN) as tmp_bot:
            bot_client_session = FakeClientSession()
            tmp_bot.session._session = bot_client_session

        assert bot_client_session.closed is True
        assert shared_client_session.closed is False

    async def test_cached_bots_share_registry_session(self, registry):
        first = registry.get_or_create(1, "1:token")
        second = registry.get_or_create(2, "2:token")

        assert first.session is second.session is registry._shared_session
