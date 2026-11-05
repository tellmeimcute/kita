import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram import Bot
from aiogram.client.session.middlewares.manager import RequestMiddlewareManager
from aiogram.methods import GetMe, SendMessage
from dishka import AsyncContainer
from redis.asyncio import Redis

from core.rate_limiters import (
    LogApiErrors,
    PaceRequests,
    RetryFloodControl,
    TgApiLimiter,
)

BOT_ID = 666
CHAT_ID = 42

# 20 msg/s with a burst of 1: every send after the first waits about 50 ms.
RATE = 20.0
BURST = 1
PERIOD = 1 / RATE


@pytest.fixture
async def redis(request_container: AsyncContainer) -> Redis:
    return await request_container.get(Redis)


@pytest.fixture
def limiter(redis: Redis) -> TgApiLimiter:
    return TgApiLimiter(redis, rate=RATE, burst=BURST, chat_rate=RATE, chat_burst=BURST)


@pytest.fixture
def bot() -> MagicMock:
    bot = MagicMock(spec=Bot)
    bot.id = BOT_ID
    return bot


@pytest.fixture
def worker_chain(limiter: TgApiLimiter) -> RequestMiddlewareManager:
    manager = RequestMiddlewareManager()
    manager.register(LogApiErrors())
    manager.register(RetryFloodControl(max_retries=3))
    manager.register(PaceRequests(limiter))
    return manager


async def test_worker_chain_sends_after_the_reserved_wait(
    worker_chain: RequestMiddlewareManager, bot: MagicMock
):
    send = AsyncMock(return_value="ok")
    wrapped = worker_chain.wrap_middlewares(send)
    method = SendMessage(chat_id=CHAT_ID, text="x")

    started = asyncio.get_running_loop().time()
    first = await wrapped(bot, method)
    after_burst = asyncio.get_running_loop().time() - started

    second = await wrapped(bot, method)
    total = asyncio.get_running_loop().time() - started

    assert first == second == "ok"
    assert after_burst < PERIOD / 2, "the burst slot must not wait"
    assert total - after_burst >= PERIOD * 0.8, "the next slot must be paced"


async def test_non_message_method_is_not_paced(
    worker_chain: RequestMiddlewareManager, bot: MagicMock
):
    send = AsyncMock(return_value="ok")
    wrapped = worker_chain.wrap_middlewares(send)
    await wrapped(bot, SendMessage(chat_id=CHAT_ID, text="x"))

    started = asyncio.get_running_loop().time()
    await wrapped(bot, GetMe())
    elapsed = asyncio.get_running_loop().time() - started

    assert send.await_count == 2
    assert elapsed < PERIOD / 2, "a cost 0 method must not wait for a slot"
