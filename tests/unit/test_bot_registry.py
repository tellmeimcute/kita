from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from core.exceptions import BotNotRegisteredError
from services.bots import BotCache, BotContext, BotSessionFactory

TEST_BOT_ID = 12345
TEST_BOT_TOKEN = f"{TEST_BOT_ID}:245872673:AAF7VsJ1ksP4k0f9zk7NpF2nvxd69_ZlPyY"
CACHE_SIZE = 2


def make_bot(bot_id: int) -> MagicMock:
    bot = MagicMock()
    bot.id = bot_id
    return bot


class TestBotCache:
    def test_put_then_get(self):
        cache = BotCache(CACHE_SIZE)
        bot = make_bot(TEST_BOT_ID)

        cache.put(bot)

        assert cache.get(TEST_BOT_ID) is bot

    def test_get_unknown_bot_returns_none(self):
        assert BotCache(CACHE_SIZE).get(TEST_BOT_ID) is None

    def test_oldest_bot_is_evicted(self):
        cache = BotCache(CACHE_SIZE)
        first, second, third = make_bot(1), make_bot(2), make_bot(3)

        cache.put(first)
        cache.put(second)
        cache.put(third)

        assert cache.get(1) is None
        assert cache.all() == [second, third]

    def test_get_refreshes_the_eviction_order(self):
        cache = BotCache(CACHE_SIZE)
        first, second, third = make_bot(1), make_bot(2), make_bot(3)
        cache.put(first)
        cache.put(second)

        cache.get(1)
        cache.put(third)

        assert cache.get(2) is None
        assert cache.all() == [first, third]

    def test_put_replaces_the_same_id(self):
        cache = BotCache(CACHE_SIZE)
        old, new = make_bot(TEST_BOT_ID), make_bot(TEST_BOT_ID)

        cache.put(old)
        cache.put(new)

        assert cache.all() == [new]

    def test_remove(self):
        cache = BotCache(CACHE_SIZE)
        cache.put(make_bot(TEST_BOT_ID))

        cache.remove(TEST_BOT_ID)

        assert cache.get(TEST_BOT_ID) is None

    def test_remove_unknown_bot_is_silent(self):
        BotCache(CACHE_SIZE).remove(TEST_BOT_ID)


class TestBotContext:
    def test_starts_empty(self):
        assert BotContext().current() is None

    def test_set_and_reset(self):
        context = BotContext()
        bot = make_bot(TEST_BOT_ID)

        token = context.set(bot)
        assert context.current() is bot

        context.reset(token)
        assert context.current() is None

    async def test_using_sets_and_clears_the_bot(self):
        context = BotContext()
        bot = make_bot(TEST_BOT_ID)

        async with context.using(bot) as current:
            assert current is bot
            assert context.current() is bot

        assert context.current() is None

    async def test_using_clears_the_bot_on_exception(self):
        context = BotContext()

        with pytest.raises(RuntimeError):
            async with context.using(make_bot(TEST_BOT_ID)):
                raise RuntimeError("boom")

        assert context.current() is None


class TestBotSessionFactory:
    def test_created_bot_uses_the_shared_session(self, mock_config):
        factory = BotSessionFactory(mock_config)

        bot = factory.create(TEST_BOT_TOKEN)

        assert bot.session is factory._shared_session
        assert isinstance(bot.default, DefaultBotProperties)
        assert bot.default.parse_mode == ParseMode.HTML

    def test_shared_session_carries_the_middlewares(self, mock_config):
        first, second = MagicMock(), MagicMock()

        factory = BotSessionFactory(mock_config, [first, second])

        assert list(factory._shared_session.middleware) == [first, second]

    def test_no_middlewares_by_default(self, mock_config):
        assert list(BotSessionFactory(mock_config)._shared_session.middleware) == []

    async def test_temp_bot_gets_its_own_session(self, mock_config):
        middleware = MagicMock()
        factory = BotSessionFactory(mock_config, [middleware])

        async with factory.temp_bot(TEST_BOT_TOKEN) as bot:
            assert isinstance(bot.session, AiohttpSession)
            assert bot.session is not factory._shared_session
            assert list(bot.session.middleware) == [middleware]

    async def test_temp_bot_closes_only_its_own_session(self, mock_config):
        factory = BotSessionFactory(mock_config)

        async with factory.temp_bot(TEST_BOT_TOKEN) as bot:
            bot.session.close = AsyncMock()

        bot.session.close.assert_awaited_once()

    async def test_close_closes_the_shared_session(self, mock_config):
        factory = BotSessionFactory(mock_config)
        factory._shared_session.close = AsyncMock()

        await factory.close()

        factory._shared_session.close.assert_awaited_once()


class TestBotRegistry:
    def test_get_or_create_reuses_the_same_token(self, registry):
        first = registry.get_or_create(1, "1:token")
        second = registry.get_or_create(1, "1:token")

        assert first is second

    @patch("services.bots.session.Bot")
    def test_get_or_create_replaces_a_changed_token(self, bot_cls, registry):
        old_bot = make_bot(1)
        old_bot.token = "1:old"
        new_bot = make_bot(1)
        new_bot.token = "1:new"
        bot_cls.side_effect = [old_bot, new_bot]

        first = registry.get_or_create(1, "1:old")
        second = registry.get_or_create(1, "1:new")

        assert first is old_bot
        assert second is new_bot
        assert registry.get_or_create(1, "1:new") is new_bot

    async def test_remove_forgets_the_bot(self, registry):
        registry.get_or_create(1, "1:token")

        registry.remove(1)

        with pytest.raises(BotNotRegisteredError):
            async with registry.with_bot(1):
                pass

    async def test_with_bot_targets_a_cached_bot(self, registry):
        bot = registry.get_or_create(1, "1:token")

        async with registry.with_bot(1) as current:
            assert current is bot
            assert registry.get_current() is bot

        assert registry.get_current() is None

    async def test_with_bot_clears_the_current_bot_on_exception(self, registry):
        registry.get_or_create(1, "1:token")

        with pytest.raises(RuntimeError):
            async with registry.with_bot(1):
                raise RuntimeError("boom")

        assert registry.get_current() is None

    async def test_with_bot_accepts_a_bot_instance(self, registry):
        bot = Bot(token=TEST_BOT_TOKEN)

        async with registry.with_bot(bot) as current:
            assert current is bot

        assert registry.get_current() is None

    async def test_with_bot_raises_for_unknown_bot(self, registry):
        with pytest.raises(BotNotRegisteredError) as error:
            async with registry.with_bot(42):
                pass

        assert error.value.bot_id == 42
        assert registry.get_current() is None

    async def test_with_bot_with_token_creates_the_bot(self, registry):
        async with registry.with_bot(1, token="1:token") as bot:
            assert bot.id == 1

    async def test_temp_bot_delegates_to_the_factory(self, registry):
        async with registry.temp_bot(TEST_BOT_TOKEN) as bot:
            assert isinstance(bot.session, AiohttpSession)
            assert bot.session is not registry._sessions._shared_session

    def test_allowed_updates_roundtrip(self, registry):
        registry.allowed_updates = ["message", "callback_query"]

        assert registry.allowed_updates == ["message", "callback_query"]

    def test_allowed_updates_rejects_other_types(self, registry):
        with pytest.raises(ValueError, match="allowed updates should be list"):
            registry.allowed_updates = ("message",)

    async def test_close_closes_the_shared_session(self, registry):
        registry._sessions._shared_session.close = AsyncMock()

        await registry.close()

        registry._sessions._shared_session.close.assert_awaited_once()
