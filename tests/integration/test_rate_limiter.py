import asyncio
from collections.abc import AsyncIterator

import pytest
from dishka import AsyncContainer
from redis.asyncio import Redis

from core.config import Config
from core.rate_limiters.limiter import (
    BUCKET_SCRIPT,
    PAUSE_BUFFER_MS,
    LimiterResponse,
    RateLimiter,
)

LIMIT_KEY = "test:rate_limiter:bucket"
PAUSE_KEY = "test:rate_limiter:bucket:pause"

# Refill must be far slower than a test call, otherwise the bucket tops itself
# up between two attempts and the "denied" branches are never reached.
RATE = 1.0
MAX_TOKENS = 3
CONCURRENT_DENIALS = 10


@pytest.fixture
async def redis(request_container: AsyncContainer) -> Redis:
    return await request_container.get(Redis)


@pytest.fixture
def limiter(redis: Redis) -> RateLimiter:
    return RateLimiter(redis, rate=RATE, max_tokens=MAX_TOKENS)


@pytest.fixture
async def other_replica(request_container: AsyncContainer) -> AsyncIterator[Redis]:
    """A second client to the same server, i.e. a second bot replica."""
    config: Config = await request_container.get(Config)
    client = Redis.from_url(config.redis.redis_url, decode_responses=True)

    try:
        yield client
    finally:
        await client.aclose()


async def spend_all_tokens(limiter: RateLimiter) -> None:
    for _ in range(MAX_TOKENS):
        res = await limiter.attempt(LIMIT_KEY, PAUSE_KEY)
        assert res.allowed, "precondition: a fresh bucket allows MAX_TOKENS requests"


async def eval_script(redis: Redis, *, rate: float, max_tokens: int, buffer_ms: int):
    return await redis.eval(BUCKET_SCRIPT, 2, LIMIT_KEY, PAUSE_KEY, rate, max_tokens, buffer_ms)


async def test_script_returns_three_values(redis: Redis):
    reply = await eval_script(redis, rate=RATE, max_tokens=MAX_TOKENS, buffer_ms=PAUSE_BUFFER_MS)

    assert isinstance(reply, list)
    assert len(reply) == 3


async def test_limiter_parses_a_real_reply(limiter: RateLimiter):
    res = await limiter.attempt(LIMIT_KEY, PAUSE_KEY)

    assert isinstance(res, LimiterResponse)
    assert (res.allowed, res.paused, res.wait_ms) == (True, False, 0)


async def test_first_denial_writes_the_pause_itself(limiter: RateLimiter, redis: Redis):
    """Deny and pause is one atomic step: no caller-side pause call exists."""
    await spend_all_tokens(limiter)

    res = await limiter.attempt(LIMIT_KEY, PAUSE_KEY)

    assert res.allowed is False
    assert res.paused is False, "the first denial is the only caller allowed to warn"
    assert await redis.exists(PAUSE_KEY) == 1, "the script must have written the pause"


async def test_next_attempt_sees_the_pause(limiter: RateLimiter):
    await spend_all_tokens(limiter)

    first = await limiter.attempt(LIMIT_KEY, PAUSE_KEY)
    second = await limiter.attempt(LIMIT_KEY, PAUSE_KEY)

    assert first.paused is False
    assert second.paused is True
    assert second.wait_ms <= first.wait_ms


async def test_exactly_one_caller_may_warn(limiter: RateLimiter):
    await spend_all_tokens(limiter)

    results = await asyncio.gather(
        *(limiter.attempt(LIMIT_KEY, PAUSE_KEY) for _ in range(CONCURRENT_DENIALS))
    )

    assert all(not res.allowed for res in results)
    assert [res.paused for res in results].count(False) == 1


async def test_exactly_one_warner_across_replicas(limiter: RateLimiter, other_replica: Redis):
    """Two clients to one server model two replicas serving the same user."""
    await spend_all_tokens(limiter)
    elsewhere = RateLimiter(other_replica, rate=RATE, max_tokens=MAX_TOKENS)

    results = await asyncio.gather(
        limiter.attempt(LIMIT_KEY, PAUSE_KEY),
        elsewhere.attempt(LIMIT_KEY, PAUSE_KEY),
    )

    assert [res.paused for res in results].count(False) == 1


async def test_wait_ms_includes_the_pause_buffer(limiter: RateLimiter):
    await spend_all_tokens(limiter)

    res = await limiter.attempt(LIMIT_KEY, PAUSE_KEY)

    assert res.wait_ms >= PAUSE_BUFFER_MS


async def test_pause_ttl_outlives_the_pause(limiter: RateLimiter, redis: Redis):
    await spend_all_tokens(limiter)

    res = await limiter.attempt(LIMIT_KEY, PAUSE_KEY)
    ttl = await redis.ttl(PAUSE_KEY)

    assert ttl >= res.wait_ms / 1000


async def test_bucket_recovers_after_the_pause_expires(redis: Redis):
    """Uses a small buffer instead of the 1 s production default."""
    buffer_ms = 50
    rate = 1000.0

    first = await eval_script(redis, rate=rate, max_tokens=1, buffer_ms=0)
    assert first[0] == 1

    denied = await eval_script(redis, rate=rate, max_tokens=1, buffer_ms=buffer_ms)
    assert denied[0] == 0
    assert denied[2] == 0
    assert denied[1] >= buffer_ms

    await asyncio.sleep(denied[1] / 1000 + 0.05)

    recovered = await eval_script(redis, rate=rate, max_tokens=1, buffer_ms=0)
    assert recovered[0] == 1, "the bucket must refill once the pause is over"


async def test_attempt_uses_evalsha_not_eval(limiter: RateLimiter, redis: Redis):
    """The whole point of register_script: 40 bytes of SHA1, not the Lua source."""
    await limiter.attempt(LIMIT_KEY, PAUSE_KEY)  # make sure the script is cached
    await redis.config_resetstat()

    await limiter.attempt(LIMIT_KEY, PAUSE_KEY)

    stats = await redis.info("commandstats")
    assert stats["cmdstat_evalsha"]["calls"] == 1
    assert stats.get("cmdstat_eval", {}).get("calls", 0) == 0


async def test_evalsha_falls_back_after_a_script_flush(limiter: RateLimiter, redis: Redis):
    """Redis forgets the script cache on restart and after SCRIPT FLUSH."""
    await redis.script_flush()

    res = await limiter.attempt(LIMIT_KEY, PAUSE_KEY)

    assert (res.allowed, res.paused, res.wait_ms) == (True, False, 0)
