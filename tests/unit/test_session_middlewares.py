from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import Bot
from aiogram.client.session.middlewares.manager import RequestMiddlewareManager
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.methods import GetMe, SendMediaGroup, SendMessage
from aiogram.types import InputMediaPhoto

from core.rate_limiters.session_middlewares import (
    MIN_RETRY_DELAY,
    LogApiErrors,
    PaceRequests,
    RetryFloodControl,
)

BOT_ID = 666
CHAT_ID = 4242


@pytest.fixture
def bot() -> MagicMock:
    bot = MagicMock(spec=Bot)
    bot.id = BOT_ID
    return bot


@pytest.fixture
def limiter() -> MagicMock:
    limiter = MagicMock()
    limiter.reserve = AsyncMock(return_value=0.0)
    return limiter


@pytest.fixture
def sleep_mock():
    with patch(
        "core.rate_limiters.session_middlewares.asyncio.sleep", new_callable=AsyncMock
    ) as sleep:
        yield sleep


def flood(seconds: int, method=None) -> TelegramRetryAfter:
    method = method or SendMessage(chat_id=CHAT_ID, text="x")
    return TelegramRetryAfter(method=method, message="Too Many Requests", retry_after=seconds)


class TestPaceRequests:
    async def test_non_message_call_bypasses_the_limiter(
        self, limiter: MagicMock, bot: MagicMock, sleep_mock
    ):
        middleware = PaceRequests(limiter)
        make_request = AsyncMock(return_value="ok")
        method = GetMe()

        result = await middleware(make_request, bot, method)

        assert result == "ok"
        make_request.assert_awaited_once_with(bot, method)
        limiter.reserve.assert_not_awaited()
        sleep_mock.assert_not_awaited()

    async def test_message_is_sent_after_the_reserved_wait(
        self, limiter: MagicMock, bot: MagicMock, sleep_mock
    ):
        limiter.reserve.return_value = 0.25
        events: list[str] = []

        async def fake_sleep(delay: float) -> None:
            events.append(f"sleep:{delay}")

        async def fake_send(b, m):
            events.append("send")
            return "ok"

        sleep_mock.side_effect = fake_sleep
        middleware = PaceRequests(limiter)
        method = SendMessage(chat_id=CHAT_ID, text="hi")

        result = await middleware(fake_send, bot, method)

        assert result == "ok"
        assert events == ["sleep:0.25", "send"]

    async def test_zero_wait_does_not_sleep(self, limiter: MagicMock, bot: MagicMock, sleep_mock):
        middleware = PaceRequests(limiter)
        make_request = AsyncMock(return_value="ok")

        await middleware(make_request, bot, SendMessage(chat_id=CHAT_ID, text="hi"))

        sleep_mock.assert_not_awaited()
        make_request.assert_awaited_once()

    async def test_reserve_receives_bot_cost_and_chat(self, limiter: MagicMock, bot: MagicMock):
        middleware = PaceRequests(limiter)

        await middleware(AsyncMock(), bot, SendMessage(chat_id=CHAT_ID, text="hi"))

        limiter.reserve.assert_awaited_once_with(BOT_ID, cost=1, chat_id=CHAT_ID)

    async def test_media_group_is_charged_per_item(self, limiter: MagicMock, bot: MagicMock):
        middleware = PaceRequests(limiter)
        method = SendMediaGroup(
            chat_id=CHAT_ID,
            media=[
                InputMediaPhoto(media="a"),
                InputMediaPhoto(media="b"),
                InputMediaPhoto(media="c"),
            ],
        )

        await middleware(AsyncMock(), bot, method)

        limiter.reserve.assert_awaited_once_with(BOT_ID, cost=3, chat_id=CHAT_ID)


class TestRetryFloodControl:
    async def test_success_on_first_attempt_does_not_sleep(self, bot: MagicMock, sleep_mock):
        middleware = RetryFloodControl(max_retries=3)
        make_request = AsyncMock(return_value="ok")

        result = await middleware(make_request, bot, SendMessage(chat_id=CHAT_ID, text="x"))

        assert result == "ok"
        make_request.assert_awaited_once()
        sleep_mock.assert_not_awaited()

    async def test_retries_after_telegram_retry_after_without_a_cap(
        self, bot: MagicMock, sleep_mock
    ):
        middleware = RetryFloodControl(max_retries=3)
        make_request = AsyncMock(side_effect=[flood(30), "ok"])

        result = await middleware(make_request, bot, SendMessage(chat_id=CHAT_ID, text="x"))

        assert result == "ok"
        assert make_request.await_count == 2
        sleep_mock.assert_awaited_once_with(30.0)

    async def test_retry_after_below_one_second_waits_one_second(self, bot: MagicMock, sleep_mock):
        middleware = RetryFloodControl(max_retries=1)
        make_request = AsyncMock(side_effect=[flood(0), "ok"])

        await middleware(make_request, bot, SendMessage(chat_id=CHAT_ID, text="x"))

        sleep_mock.assert_awaited_once_with(MIN_RETRY_DELAY)

    async def test_gives_up_after_max_retries_and_raises(self, bot: MagicMock, sleep_mock):
        middleware = RetryFloodControl(max_retries=2)
        make_request = AsyncMock(side_effect=flood(5))

        with pytest.raises(TelegramRetryAfter):
            await middleware(make_request, bot, SendMessage(chat_id=CHAT_ID, text="x"))

        assert make_request.await_count == 3
        assert sleep_mock.await_count == 2

    async def test_zero_retries_makes_a_single_attempt(self, bot: MagicMock, sleep_mock):
        middleware = RetryFloodControl(max_retries=0)
        make_request = AsyncMock(side_effect=flood(5))

        with pytest.raises(TelegramRetryAfter):
            await middleware(make_request, bot, SendMessage(chat_id=CHAT_ID, text="x"))

        make_request.assert_awaited_once()
        sleep_mock.assert_not_awaited()

    async def test_other_api_errors_are_not_retried(self, bot: MagicMock, sleep_mock):
        middleware = RetryFloodControl(max_retries=3)
        method = SendMessage(chat_id=CHAT_ID, text="x")
        make_request = AsyncMock(
            side_effect=TelegramAPIError(method=method, message="Bad Request")
        )

        with pytest.raises(TelegramAPIError):
            await middleware(make_request, bot, method)

        make_request.assert_awaited_once()
        sleep_mock.assert_not_awaited()


class TestLogApiErrors:
    async def test_success_passes_through(self, bot: MagicMock):
        middleware = LogApiErrors()
        make_request = AsyncMock(return_value="ok")

        result = await middleware(make_request, bot, SendMessage(chat_id=CHAT_ID, text="x"))

        assert result == "ok"

    async def test_api_error_is_logged_and_reraised(self, bot: MagicMock):
        middleware = LogApiErrors()
        method = SendMessage(chat_id=CHAT_ID, text="x")
        make_request = AsyncMock(
            side_effect=TelegramAPIError(method=method, message="Bad Request")
        )

        with (
            patch("core.rate_limiters.session_middlewares.logger") as logger_mock,
            pytest.raises(TelegramAPIError),
        ):
            await middleware(make_request, bot, method)

        logger_mock.exception.assert_called_once()

    async def test_flood_control_is_left_to_the_retry_middleware(self, bot: MagicMock):
        middleware = LogApiErrors()
        method = SendMessage(chat_id=CHAT_ID, text="x")
        make_request = AsyncMock(side_effect=flood(5, method))

        with (
            patch("core.rate_limiters.session_middlewares.logger") as logger_mock,
            pytest.raises(TelegramRetryAfter),
        ):
            await middleware(make_request, bot, method)

        logger_mock.exception.assert_not_called()


class TestChainOrder:
    """The first registered middleware is the outermost one (aiogram wraps reversed)."""

    def make_manager(self, limiter: MagicMock, max_retries: int = 1) -> RequestMiddlewareManager:
        manager = RequestMiddlewareManager()
        manager.register(RetryFloodControl(max_retries=max_retries))
        manager.register(PaceRequests(limiter))
        return manager

    async def test_retry_wraps_pacing_so_a_429_reserves_again(
        self, limiter: MagicMock, bot: MagicMock, sleep_mock
    ):
        manager = self.make_manager(limiter)
        method = SendMessage(chat_id=CHAT_ID, text="x")
        make_request = AsyncMock(side_effect=[flood(3), "ok"])
        wrapped = manager.wrap_middlewares(make_request)

        result = await wrapped(bot, method)

        assert result == "ok"
        assert limiter.reserve.await_count == 2, "the retried attempt must re-reserve"
        sleep_mock.assert_awaited_once_with(3.0)

    async def test_give_up_error_is_logged_once_as_error(
        self, limiter: MagicMock, bot: MagicMock, sleep_mock
    ):
        manager = RequestMiddlewareManager()
        manager.register(LogApiErrors())
        manager.register(RetryFloodControl(max_retries=1))
        manager.register(PaceRequests(limiter))

        method = SendMessage(chat_id=CHAT_ID, text="x")
        make_request = AsyncMock(side_effect=flood(2, method))
        wrapped = manager.wrap_middlewares(make_request)

        with (
            patch("core.rate_limiters.session_middlewares.logger") as logger_mock,
            pytest.raises(TelegramRetryAfter),
        ):
            await wrapped(bot, method)

        logger_mock.error.assert_called_once()
        logger_mock.exception.assert_not_called()
