from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from core.exceptions import BotNotRegisteredError
from interfaces import BotSessionProtocol
from services.bots import BotCache, BotResolver, BotSessionFactory

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
    def test_starts_empty(self, bot_context):
        assert bot_context.get_current() is None

    def test_set_and_reset(self, bot_context):
        bot = make_bot(TEST_BOT_ID)

        token = bot_context.set_current(bot)
        assert bot_context.get_current() is bot

        bot_context.reset_current(token)
        assert bot_context.get_current() is None

    async def test_using_sets_and_clears_the_bot(self, bot_context):
        bot = make_bot(TEST_BOT_ID)

        async with bot_context.using(bot) as current:
            assert current is bot
            assert bot_context.get_current() is bot

        assert bot_context.get_current() is None

    async def test_using_clears_the_bot_on_exception(self, bot_context):
        with pytest.raises(RuntimeError):
            async with bot_context.using(make_bot(TEST_BOT_ID)):
                raise RuntimeError("boom")

        assert bot_context.get_current() is None


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


class TestBotResolver:
    def test_get_or_create_reuses_the_same_token(self, resolver):
        first = resolver.get_or_create(1, "1:token")
        second = resolver.get_or_create(1, "1:token")

        assert first is second

    def test_get_or_create_rejects_a_token_of_another_bot(self, resolver):
        with pytest.raises(ValueError, match="Token belongs to bot 2"):
            resolver.get_or_create(1, "2:token")

        assert resolver.get_or_create(1, "1:token").id == 1

    def test_get_or_create_replaces_a_changed_token(self, bot_context):
        old_bot = make_bot(1)
        old_bot.token = "1:old"
        new_bot = make_bot(1)
        new_bot.token = "1:new"

        sessions = MagicMock(spec=BotSessionProtocol)
        sessions.create.side_effect = [old_bot, new_bot]
        resolver = BotResolver(sessions, BotCache(CACHE_SIZE), bot_context)

        first = resolver.get_or_create(1, "1:old")
        second = resolver.get_or_create(1, "1:new")

        assert first is old_bot
        assert second is new_bot
        assert resolver.get_or_create(1, "1:new") is new_bot

    async def test_remove_forgets_the_bot(self, resolver):
        resolver.get_or_create(1, "1:token")

        resolver.remove(1)

        with pytest.raises(BotNotRegisteredError):
            async with resolver.with_bot(1):
                pass

    async def test_with_bot_targets_a_cached_bot(self, resolver, bot_context):
        bot = resolver.get_or_create(1, "1:token")

        async with resolver.with_bot(1) as current:
            assert current is bot
            assert bot_context.get_current() is bot

        assert bot_context.get_current() is None

    async def test_with_bot_clears_the_current_bot_on_exception(self, resolver, bot_context):
        resolver.get_or_create(1, "1:token")

        with pytest.raises(RuntimeError):
            async with resolver.with_bot(1):
                raise RuntimeError("boom")

        assert bot_context.get_current() is None

    async def test_with_bot_accepts_a_bot_instance(self, resolver, bot_context):
        bot = Bot(token=TEST_BOT_TOKEN)

        async with resolver.with_bot(bot) as current:
            assert current is bot
            assert bot_context.get_current() is bot

        assert bot_context.get_current() is None

    async def test_with_bot_raises_for_unknown_bot(self, resolver):
        with pytest.raises(BotNotRegisteredError) as error:
            async with resolver.with_bot(42):
                pass

        assert error.value.bot_id == 42

    async def test_with_bot_with_token_creates_the_bot(self, resolver):
        async with resolver.with_bot(1, token="1:token") as bot:
            assert bot.id == 1

    async def test_temp_bot_comes_from_the_session_factory(self, resolver, bot_sessions):
        async with resolver.temp_bot(TEST_BOT_TOKEN) as bot:
            assert isinstance(bot.session, AiohttpSession)
            assert bot.session is not bot_sessions._shared_session
