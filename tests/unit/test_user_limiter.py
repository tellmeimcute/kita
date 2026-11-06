from unittest.mock import MagicMock

import pytest

from core.rate_limiters.limiter import LimiterResponse
from core.rate_limiters.user_limiter import UserLimiter

SCOPE = "tg_update"
OTHER_SCOPE = "userbot_action"

DEFAULT_MAX_TOKENS = 5
DEFAULT_REFILL_RATE = 0.3


@pytest.fixture
def limiter(mock_redis, mock_bot_context) -> UserLimiter:
    return UserLimiter(
        redis=mock_redis,
        bot_context=mock_bot_context,
        scope=SCOPE,
        max_tokens=DEFAULT_MAX_TOKENS,
        refill_rate=DEFAULT_REFILL_RATE,
    )


class TestKeys:
    def test_keys_contain_bot_user_and_scope(self, limiter, mock_bot, test_user_dto):
        limit_key, pause_key = limiter._keys(test_user_dto)

        prefix = f"kita:{mock_bot.id}:{test_user_dto.user_id}:rate_limit"
        assert limit_key == f"{prefix}:{SCOPE}"
        assert pause_key == f"{prefix}:{SCOPE}:pause"

    def test_scopes_are_isolated(self, mock_redis, mock_bot_context, test_user_dto):
        main = UserLimiter(mock_redis, mock_bot_context, scope=SCOPE)
        userbot = UserLimiter(mock_redis, mock_bot_context, scope=OTHER_SCOPE)

        main_limit, main_pause = main._keys(test_user_dto)
        userbot_limit, userbot_pause = userbot._keys(test_user_dto)

        assert main_limit != userbot_limit
        assert main_pause != userbot_pause
        assert len({main_limit, main_pause, userbot_limit, userbot_pause}) == 4

    def test_users_are_isolated(self, limiter, test_user_dto, user_dto_factory):
        other_user = user_dto_factory()

        limit_key, pause_key = limiter._keys(test_user_dto)
        other_limit_key, other_pause_key = limiter._keys(other_user)

        assert limit_key != other_limit_key
        assert pause_key != other_pause_key

    def test_bots_are_isolated(self, mock_redis, test_user_dto):
        registry_a = MagicMock()
        registry_a.get_current.return_value = MagicMock(id=1)
        registry_b = MagicMock()
        registry_b.get_current.return_value = MagicMock(id=2)

        limiter_a = UserLimiter(mock_redis, registry_a, scope=SCOPE)
        limiter_b = UserLimiter(mock_redis, registry_b, scope=SCOPE)

        assert limiter_a._keys(test_user_dto) != limiter_b._keys(test_user_dto)


class TestDelegation:
    async def test_attempt_passes_bucket_then_pause_key(self, limiter, test_user_dto):
        limit_key, pause_key = limiter._keys(test_user_dto)

        res = await limiter.attempt(test_user_dto)

        assert isinstance(res, LimiterResponse)
        assert res.allowed is True
        assert limiter._limiter._bucket_script.await_count == 1
        assert limiter._limiter._bucket_script.await_args.kwargs["keys"] == [limit_key, pause_key]

    async def test_attempt_propagates_denial(self, limiter, test_user_dto):
        limiter._limiter._bucket_script.return_value = [0, 900, 0]

        res = await limiter.attempt(test_user_dto)

        assert res.allowed is False
        assert res.wait_ms == 900
        assert res.paused is False

    async def test_attempt_propagates_paused_flag(self, limiter, test_user_dto):
        limiter._limiter._bucket_script.return_value = [0, 900, 1]

        res = await limiter.attempt(test_user_dto)

        assert res.allowed is False
        assert res.paused is True
