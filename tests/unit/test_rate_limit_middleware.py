from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Message

from core.rate_limiters.token_bucket import TokenBucketResult
from middlewares.rate_limit import RateLimitMiddleware

# Constants
TEST_USER_ID = 111


@pytest.fixture
def middleware(mock_redis, mock_config, mock_bot_registry, mock_i18n, mock_translator):
    return RateLimitMiddleware(
        redis=mock_redis,
        config=mock_config,
        bot_registry=mock_bot_registry,
        i18n=mock_i18n,
        translator=mock_translator,
    )


class TestRateLimitMiddleware:
    async def test_allows_request_when_allowed(self, middleware, test_user_dto):
        middleware.limiter = MagicMock()
        middleware.limiter.attempt = AsyncMock(
            return_value=TokenBucketResult(allowed=1, remains=4)
        )
        middleware.limiter.unmark_warned = AsyncMock()

        handler = AsyncMock()
        event = MagicMock(spec=Message)
        event.from_user = MagicMock(id=TEST_USER_ID)
        data = {
            "user_dto": test_user_dto,
        }

        await middleware(handler, event, data)

        handler.assert_called_once_with(event, data)
        middleware.limiter.unmark_warned.assert_called_once()

    async def test_rate_limited_no_warning(self, middleware, test_user_dto):
        middleware.limiter = MagicMock()
        middleware.limiter.attempt = AsyncMock(
            return_value=TokenBucketResult(allowed=0, remains=0)
        )
        middleware.limiter.is_warned = AsyncMock(return_value=False)
        middleware.limiter.mark_warned = AsyncMock()

        handler = AsyncMock()
        event = MagicMock(spec=Message)
        event.from_user = MagicMock(id=TEST_USER_ID)
        event.answer = AsyncMock()
        data = {
            "user_dto": test_user_dto,
        }

        with patch.object(middleware.i18n, "use_locale"):
            await middleware(handler, event, data)

        middleware.limiter.mark_warned.assert_called_once()
        event.answer.assert_called_once()
        handler.assert_not_called()

    async def test_rate_limited_callback_answer_only(self, middleware, test_user_dto):
        middleware.limiter = MagicMock()
        middleware.limiter.attempt = AsyncMock(
            return_value=TokenBucketResult(allowed=0, remains=0)
        )
        middleware.limiter.is_warned = AsyncMock(return_value=True)

        handler = AsyncMock()
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = MagicMock(id=TEST_USER_ID)
        callback.answer = AsyncMock()
        data = {"user_dto": test_user_dto}

        await middleware(handler, callback, data)

        callback.answer.assert_called_once()
        handler.assert_not_called()
