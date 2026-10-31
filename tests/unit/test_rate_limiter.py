from unittest.mock import AsyncMock, patch

import pytest

from core.rate_limiters.limiter import (
    BUCKET_SCRIPT,
    MAX_SLEEP,
    PAUSE_BUFFER_MS,
    LimiterResponse,
    RateLimiter,
)

LIMIT_KEY = "kita:666:42:rate_limit:tg_update"
PAUSE_KEY = "kita:666:42:rate_limit:tg_update:pause"

RATE = 0.5
MAX_TOKENS = 4

# What BUCKET_SCRIPT returns: {allowed, wait_ms, already_paused}
ALLOWED = [1, 0, 0]
DENIED = [0, 1500, 0]
ALREADY_PAUSED = [0, 2000, 1]


@pytest.fixture
def limiter(mock_redis) -> RateLimiter:
    return RateLimiter(mock_redis, rate=RATE, max_tokens=MAX_TOKENS)


@pytest.fixture
def sleep_mock():
    with patch(
        "core.rate_limiters.limiter.asyncio.sleep", new_callable=AsyncMock
    ) as patched_sleep:
        yield patched_sleep


class TestRegistration:
    def test_registers_the_bucket_script(self, limiter, mock_redis):
        sources = [call.args[0] for call in mock_redis.register_script.call_args_list]

        assert sources == [BUCKET_SCRIPT]


class TestAttempt:
    async def test_allowed_response(self, limiter):
        res = await limiter.attempt(LIMIT_KEY, PAUSE_KEY)

        assert isinstance(res, LimiterResponse)
        assert res.allowed is True
        assert res.paused is False
        assert res.wait_ms == 0

    async def test_denied_response_carries_wait_ms(self, limiter):
        limiter._bucket_script.return_value = DENIED

        res = await limiter.attempt(LIMIT_KEY, PAUSE_KEY)

        assert res.allowed is False
        assert res.paused is False
        assert res.wait_ms == 1500

    async def test_paused_response_is_flagged(self, limiter):
        limiter._bucket_script.return_value = ALREADY_PAUSED

        res = await limiter.attempt(LIMIT_KEY, PAUSE_KEY)

        assert res.allowed is False
        assert res.paused is True
        assert limiter._bucket_script.await_count == 1

    async def test_calls_registered_script_instead_of_raw_eval(self, limiter, mock_redis):
        await limiter.attempt(LIMIT_KEY, PAUSE_KEY)

        assert limiter._bucket_script.await_count == 1
        assert limiter._bucket_script.await_args.kwargs == {
            "keys": [LIMIT_KEY, PAUSE_KEY],
            "args": [RATE, MAX_TOKENS, PAUSE_BUFFER_MS],
        }
        mock_redis.eval.assert_not_called()


class TestAcquire:
    async def test_returns_immediately_when_allowed(self, limiter, sleep_mock):
        await limiter.acquire(LIMIT_KEY, PAUSE_KEY)

        assert limiter._bucket_script.await_count == 1
        sleep_mock.assert_not_awaited()

    async def test_retries_until_allowed(self, limiter, sleep_mock):
        limiter._bucket_script.side_effect = [[0, 400, 0], [0, 200, 0], ALLOWED]

        await limiter.acquire(LIMIT_KEY, PAUSE_KEY)

        assert limiter._bucket_script.await_count == 3
        assert [call.args[0] for call in sleep_mock.await_args_list] == pytest.approx([0.4, 0.2])

    async def test_sleep_is_clamped_to_max_sleep(self, limiter, sleep_mock):
        limiter._bucket_script.side_effect = [[0, 60_000, 0], ALLOWED]

        await limiter.acquire(LIMIT_KEY, PAUSE_KEY)

        assert sleep_mock.await_args_list[0].args[0] == MAX_SLEEP

    async def test_sleep_has_lower_bound_of_one_millisecond(self, limiter, sleep_mock):
        limiter._bucket_script.side_effect = [[0, 0, 0], ALLOWED]

        await limiter.acquire(LIMIT_KEY, PAUSE_KEY)

        assert sleep_mock.await_args_list[0].args[0] == pytest.approx(0.001)

    async def test_raises_timeout_after_max_retries(self, limiter, sleep_mock):
        limiter._bucket_script.return_value = [0, 100, 0]

        with pytest.raises(TimeoutError):
            await limiter.acquire(LIMIT_KEY, PAUSE_KEY, max_retries=2)

        assert limiter._bucket_script.await_count == 3
        assert sleep_mock.await_count == 2
