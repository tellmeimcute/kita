import pytest

from core.rate_limiters.token_bucket import TokenBucketLimiter, TokenBucketResult

REMAINING_AFTER_ATTEMPT = 4


@pytest.fixture
def limiter(mock_redis, mock_bot_registry, mock_config):
    return TokenBucketLimiter(
        redis=mock_redis,
        bot_registry=mock_bot_registry,
        **mock_config.rate_limit.model_dump(),
    )


class TestTokenBucketLimiter:
    async def test_attempt_allowed(self, limiter, mock_redis, test_user_dto):
        mock_redis.eval.return_value = [1, REMAINING_AFTER_ATTEMPT]

        result = await limiter.attempt(test_user_dto)

        assert isinstance(result, TokenBucketResult)
        assert result.allowed == 1
        assert result.remains == REMAINING_AFTER_ATTEMPT

    async def test_attempt_denied(self, limiter, mock_redis, test_user_dto):
        mock_redis.eval.return_value = [0, 0]

        result = await limiter.attempt(test_user_dto)

        assert result.allowed == 0
        assert result.remains == 0

    async def test_attempt_calls_redis_with_correct_args(self, limiter, mock_redis, test_user_dto):
        mock_redis.eval.return_value = [1, 4]

        await limiter.attempt(test_user_dto)

        mock_redis.eval.assert_called_once()
        args = mock_redis.eval.call_args.args
        assert args[0] == limiter._script
        assert args[1] == 1
        assert args[3] == limiter._max_tokens
        assert args[4] == limiter._refill_rate

    async def test_mark_warned(self, limiter, mock_redis, test_user_dto):
        await limiter.mark_warned(test_user_dto)

        mock_redis.sadd.assert_called_once()
        mock_redis.expire.assert_called_once()

    async def test_unmark_warned(self, limiter, mock_redis, test_user_dto):
        await limiter.unmark_warned(test_user_dto)

        mock_redis.srem.assert_called_once()

    async def test_is_warned_true(self, limiter, mock_redis, test_user_dto):
        mock_redis.sismember.return_value = True

        result = await limiter.is_warned(test_user_dto)

        assert result is True

    async def test_is_warned_false(self, limiter, mock_redis, test_user_dto):
        mock_redis.sismember.return_value = False

        result = await limiter.is_warned(test_user_dto)

        assert result is False
