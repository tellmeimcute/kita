from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, Message

from core.rate_limiters.limiter import LimiterResponse
from middlewares.rate_limit import (
    RateLimitMiddleware,
    UserBotRateLimitMiddleware,
)

TEST_USER_ID = 111


def make_message() -> MagicMock:
    event = MagicMock(spec=Message)
    event.from_user = MagicMock(id=TEST_USER_ID)
    event.answer = AsyncMock()
    return event


def make_callback(data: str | None = None) -> MagicMock:
    event = MagicMock(spec=CallbackQuery)
    event.from_user = MagicMock(id=TEST_USER_ID)
    event.answer = AsyncMock()
    event.data = data
    return event


def stub_decision(
    middleware, *, allowed: bool = False, paused: bool = False, wait_ms: int = 0
) -> AsyncMock:
    """Patch the verdict on the real limiter instead of replacing the whole object."""
    attempt = AsyncMock(
        return_value=LimiterResponse(allowed=allowed, paused=paused, wait_ms=wait_ms)
    )
    middleware.limiter.attempt = attempt
    return attempt


@pytest.fixture
def middleware_kwargs(
    mock_redis, mock_config, mock_bot_registry, mock_i18n, mock_translator
) -> dict[str, Any]:
    return {
        "redis": mock_redis,
        "config": mock_config,
        "bot_registry": mock_bot_registry,
        "i18n": mock_i18n,
        "translator": mock_translator,
    }


@pytest.fixture
def middleware(middleware_kwargs) -> RateLimitMiddleware:
    return RateLimitMiddleware(**middleware_kwargs)


@pytest.fixture
def userbot_middleware(
    mock_redis, mock_bot_registry, mock_i18n, mock_translator
) -> UserBotRateLimitMiddleware:
    return UserBotRateLimitMiddleware(
        redis=mock_redis,
        bot_registry=mock_bot_registry,
        i18n=mock_i18n,
        translator=mock_translator,
    )


class TestLimiterDecision:
    async def test_allowed_event_reaches_the_handler(self, middleware, test_user_dto):
        attempt = stub_decision(middleware, allowed=True)
        handler = AsyncMock(return_value="handled")
        event = make_message()
        data = {"user_dto": test_user_dto}

        result = await middleware(handler, event, data)

        assert result == "handled", "the handler result must be passed through"
        handler.assert_awaited_once_with(event, data)
        attempt.assert_awaited_once_with(test_user_dto)
        event.answer.assert_not_awaited()

    async def test_denial_sends_one_warning_instead_of_handling(
        self, middleware, test_user_dto, mock_translator
    ):
        stub_decision(middleware, wait_ms=2000)
        handler = AsyncMock()
        event = make_message()

        await middleware(handler, event, {"user_dto": test_user_dto})

        handler.assert_not_awaited()
        event.answer.assert_awaited_once_with(mock_translator.i18n_text.return_value)

    @pytest.mark.parametrize(
        ("wait_ms", "pause_for"),
        [(0, 0), (1, 1), (999, 1), (1000, 1), (1001, 2), (2000, 2), (2001, 3)],
    )
    async def test_warning_reports_the_pause_rounded_up(
        self, middleware, test_user_dto, mock_translator, wait_ms: int, pause_for: int
    ):
        stub_decision(middleware, wait_ms=wait_ms)

        await middleware(AsyncMock(), make_message(), {"user_dto": test_user_dto})

        mock_translator.i18n_text.assert_called_once_with(
            "rate_limited_warning", {"pause_for": pause_for}
        )

    async def test_warning_is_translated_in_the_user_locale(
        self, middleware, user_dto_factory, mock_i18n
    ):
        user = user_dto_factory(language_code="en")
        stub_decision(middleware, wait_ms=2000)

        await middleware(AsyncMock(), make_message(), {"user_dto": user})

        mock_i18n.use_locale.assert_called_once_with("en")

    async def test_already_paused_message_is_swallowed_silently(
        self, middleware, test_user_dto, mock_translator
    ):
        stub_decision(middleware, paused=True, wait_ms=1500)
        handler = AsyncMock()
        event = make_message()

        await middleware(handler, event, {"user_dto": test_user_dto})

        handler.assert_not_awaited()
        event.answer.assert_not_awaited()
        mock_translator.i18n_text.assert_not_called()

    async def test_already_paused_callback_only_stops_the_spinner(
        self, middleware, test_user_dto, mock_translator
    ):
        stub_decision(middleware, paused=True, wait_ms=1500)
        handler = AsyncMock()
        event = make_callback("some_panel")

        await middleware(handler, event, {"user_dto": test_user_dto})

        event.answer.assert_awaited_once_with()
        handler.assert_not_awaited()
        mock_translator.i18n_text.assert_not_called()

    async def test_event_without_user_dto_is_dropped(self, middleware, mock_translator):
        attempt = stub_decision(middleware, allowed=True)
        handler = AsyncMock()
        event = make_message()

        await middleware(handler, event, {"user_dto": None})

        handler.assert_not_awaited()
        attempt.assert_not_awaited()
        event.answer.assert_not_awaited()
        mock_translator.i18n_text.assert_not_called()

    async def test_event_without_from_user_is_dropped(
        self, middleware, test_user_dto, mock_translator
    ):
        attempt = stub_decision(middleware, allowed=True)
        handler = AsyncMock()
        event = make_message()
        event.from_user = None

        await middleware(handler, event, {"user_dto": test_user_dto})

        handler.assert_not_awaited()
        attempt.assert_not_awaited()
        mock_translator.i18n_text.assert_not_called()


class TestWidgetBypass:
    async def test_unlimited_widget_skips_the_limiter(self, userbot_middleware, test_user_dto):
        attempt = stub_decision(userbot_middleware, paused=True)
        handler = AsyncMock()
        event = make_callback("main_menu")

        await userbot_middleware(handler, event, {"user_dto": test_user_dto})

        handler.assert_awaited_once()
        attempt.assert_not_awaited()

    async def test_widget_outside_the_allowlist_is_limited(
        self, userbot_middleware, test_user_dto
    ):
        attempt = stub_decision(userbot_middleware, paused=True)
        handler = AsyncMock()
        event = make_callback("some_panel:42")

        await userbot_middleware(handler, event, {"user_dto": test_user_dto})

        attempt.assert_awaited_once()
        handler.assert_not_awaited()

    async def test_nested_widget_takes_the_outermost_segment(
        self, userbot_middleware, test_user_dto
    ):
        attempt = stub_decision(userbot_middleware, allowed=True)
        handler = AsyncMock()
        event = make_callback("inner\x1dmain_menu")

        await userbot_middleware(handler, event, {"user_dto": test_user_dto})

        attempt.assert_not_awaited()
        handler.assert_awaited_once()


class TestScopeIsolation:
    def test_shipped_middlewares_use_distinct_scopes(self):
        assert RateLimitMiddleware._scope == "tg_update"
        assert UserBotRateLimitMiddleware._scope == "userbot_action"
