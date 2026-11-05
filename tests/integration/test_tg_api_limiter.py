import asyncio

import pytest
from dishka import AsyncContainer
from redis.asyncio import Redis

from core.rate_limiters.tg_api import TgApiLimiter

BOT_ID = 666
CHAT_ID = 42
OTHER_CHAT_ID = 43
OTHER_BOT_ID = 999

BOT_KEY = "kita:666:api:gcra"
CHAT_KEY = "kita:666:api:chat:42:gcra"

# 10 msg/s, 3 messages back to back; per chat 2 msg/s, 2 messages back to back.
RATE = 10.0
BURST = 3
CHAT_RATE = 2.0
CHAT_BURST = 2

PERIOD = 1 / RATE
CHAT_PERIOD = 1 / CHAT_RATE


@pytest.fixture
async def redis(request_container: AsyncContainer) -> Redis:
    return await request_container.get(Redis)


@pytest.fixture
def limiter(redis: Redis) -> TgApiLimiter:
    return TgApiLimiter(redis, rate=RATE, burst=BURST, chat_rate=CHAT_RATE, chat_burst=CHAT_BURST)


async def test_bot_burst_is_immediate(limiter: TgApiLimiter):
    waits = [await limiter.reserve(BOT_ID, cost=1, chat_id=None) for _ in range(BURST)]

    assert waits == [0.0, 0.0, 0.0]


async def test_call_after_the_bot_burst_waits_one_period(limiter: TgApiLimiter):
    for _ in range(BURST):
        await limiter.reserve(BOT_ID, cost=1, chat_id=None)

    wait = await limiter.reserve(BOT_ID, cost=1, chat_id=None)

    assert 0.05 < wait <= PERIOD


async def test_bot_waits_grow_by_one_period(limiter: TgApiLimiter):
    for _ in range(BURST):
        await limiter.reserve(BOT_ID, cost=1, chat_id=None)

    first = await limiter.reserve(BOT_ID, cost=1, chat_id=None)
    second = await limiter.reserve(BOT_ID, cost=1, chat_id=None)

    assert first > 0
    assert second - first == pytest.approx(PERIOD, abs=0.02)


async def test_sustained_pacing_after_sleeping_the_wait(limiter: TgApiLimiter):
    for _ in range(BURST):
        await limiter.reserve(BOT_ID, cost=1, chat_id=None)
    first = await limiter.reserve(BOT_ID, cost=1, chat_id=None)

    await asyncio.sleep(first)
    second = await limiter.reserve(BOT_ID, cost=1, chat_id=None)

    assert first == pytest.approx(PERIOD, abs=0.02)
    assert second == pytest.approx(PERIOD, abs=0.03), "sustained rate must hold"


async def test_chat_burst_is_immediate(limiter: TgApiLimiter):
    waits = [await limiter.reserve(BOT_ID, cost=1, chat_id=CHAT_ID) for _ in range(CHAT_BURST)]

    assert waits == [0.0, 0.0]


async def test_call_after_the_chat_burst_waits_one_chat_period(limiter: TgApiLimiter):
    for _ in range(CHAT_BURST):
        await limiter.reserve(BOT_ID, cost=1, chat_id=CHAT_ID)

    wait = await limiter.reserve(BOT_ID, cost=1, chat_id=CHAT_ID)

    assert wait >= CHAT_PERIOD - 0.1


async def test_chat_budget_is_independent_per_chat(limiter: TgApiLimiter):
    for _ in range(CHAT_BURST):
        await limiter.reserve(BOT_ID, cost=1, chat_id=CHAT_ID)

    fresh_chat = await limiter.reserve(BOT_ID, cost=1, chat_id=OTHER_CHAT_ID)
    same_chat = await limiter.reserve(BOT_ID, cost=1, chat_id=CHAT_ID)

    assert fresh_chat == 0.0, "another chat must not inherit this chat's budget"
    assert same_chat > 0.4, "the exhausted chat must wait for its period"


async def test_no_chat_charges_only_the_bot_budget(limiter: TgApiLimiter, redis: Redis):
    await limiter.reserve(BOT_ID, cost=1, chat_id=None)

    chat_keys = await redis.keys("kita:666:api:chat:*")

    assert chat_keys == []
    assert await redis.exists(BOT_KEY) == 1


async def test_media_group_cost_is_charged_per_item(redis: Redis):
    limiter = TgApiLimiter(redis, rate=RATE, burst=1, chat_rate=CHAT_RATE, chat_burst=1)

    first = await limiter.reserve(777, cost=5, chat_id=None)
    second = await limiter.reserve(777, cost=1, chat_id=None)

    assert first == 0.0
    assert second >= 5 * PERIOD - 0.05


async def test_ttl_covers_the_budget_window(limiter: TgApiLimiter, redis: Redis):
    await limiter.reserve(BOT_ID, cost=1, chat_id=CHAT_ID)

    assert await redis.pttl(BOT_KEY) > 0
    assert await redis.pttl(CHAT_KEY) > 0


async def test_concurrent_reservations_are_spread_out(redis: Redis):
    limiter = TgApiLimiter(redis, rate=RATE, burst=1, chat_rate=CHAT_RATE, chat_burst=1)

    waits = await asyncio.gather(*(limiter.reserve(888, cost=1, chat_id=None) for _ in range(5)))
    ordered = sorted(waits)

    assert ordered[0] == 0.0
    assert ordered[-1] >= 4 * PERIOD - 0.05
    for earlier, later in zip(ordered[:-1], ordered[1:], strict=True):
        assert later > earlier, "each concurrent caller must get its own slot"


async def test_bots_are_isolated(limiter: TgApiLimiter):
    for _ in range(BURST):
        await limiter.reserve(BOT_ID, cost=1, chat_id=CHAT_ID)

    assert await limiter.reserve(OTHER_BOT_ID, cost=1, chat_id=CHAT_ID) == 0.0
