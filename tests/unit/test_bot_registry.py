from unittest.mock import AsyncMock, MagicMock, patch

import pytest

TEST_BOT_ID = 12345


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
            token=f"{TEST_BOT_ID}:valid_token", **registry.bot_settings
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
            token=f"{TEST_BOT_ID}:different_token", **registry.bot_settings
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

    async def test_close(self, registry):
        registry._session.close = AsyncMock()

        await registry.close()

        registry._session.close.assert_called_once()
