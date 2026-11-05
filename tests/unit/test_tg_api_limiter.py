from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.methods import (
    AnswerCallbackQuery,
    CopyMessage,
    EditMessageText,
    ForwardMessage,
    GetChat,
    GetMe,
    SendChatAction,
    SendMediaGroup,
    SendMessage,
    SendPhoto,
    SendSticker,
)
from aiogram.methods.base import TelegramMethod
from aiogram.types import InputMediaPhoto

from core.rate_limiters.tg_api import (
    RESERVE_SCRIPT,
    SINGLE_MESSAGE_METHODS,
    TgApiLimiter,
    chat_id_of,
    message_cost,
)

RATE = 10.0
BURST = 3
CHAT_RATE = 2.0
CHAT_BURST = 2


@pytest.fixture
def script_mock() -> AsyncMock:
    return AsyncMock(return_value=0)


@pytest.fixture
def redis_mock(script_mock: AsyncMock) -> AsyncMock:
    redis = AsyncMock()
    redis.register_script = MagicMock(return_value=script_mock)
    return redis


@pytest.fixture
def limiter(redis_mock: AsyncMock) -> TgApiLimiter:
    return TgApiLimiter(
        redis_mock, rate=RATE, burst=BURST, chat_rate=CHAT_RATE, chat_burst=CHAT_BURST
    )


class TestMessageCost:
    @pytest.mark.parametrize(
        "method",
        [
            SendMessage(chat_id=1, text="x"),
            SendPhoto(chat_id=1, photo="file_id"),
            SendSticker(chat_id=1, sticker="file_id"),
            CopyMessage(chat_id=1, from_chat_id=2, message_id=3),
            ForwardMessage(chat_id=1, from_chat_id=2, message_id=3),
            EditMessageText(chat_id=1, message_id=2, text="x"),
        ],
    )
    def test_single_message_methods_cost_one(self, method):
        assert message_cost(method) == 1

    def test_media_group_costs_one_per_item(self):
        method = SendMediaGroup(
            chat_id=1,
            media=[InputMediaPhoto(media="a"), InputMediaPhoto(media="b")],
        )

        assert message_cost(method) == 2

    @pytest.mark.parametrize(
        "method",
        [
            GetMe(),
            GetChat(chat_id=1),
            SendChatAction(chat_id=1, action="typing"),
            AnswerCallbackQuery(callback_query_id="query-id"),
        ],
    )
    def test_other_methods_are_not_message_sends(self, method):
        assert message_cost(method) == 0

    def test_every_listed_method_is_a_telegram_method(self):
        assert all(issubclass(cls, TelegramMethod) for cls in SINGLE_MESSAGE_METHODS)


class TestChatIdOf:
    def test_returns_the_chat_id_when_present(self):
        assert chat_id_of(SendMessage(chat_id=42, text="x")) == 42

    def test_returns_none_for_methods_without_a_chat(self):
        assert chat_id_of(GetMe()) is None
        assert chat_id_of(AnswerCallbackQuery(callback_query_id="query-id")) is None

    def test_returns_none_for_an_inline_edit(self):
        method = EditMessageText(inline_message_id="inline-id", text="x")

        assert chat_id_of(method) is None


class TestReserve:
    async def test_registers_the_reserve_script_once(self, limiter, redis_mock):
        redis_mock.register_script.assert_called_once_with(RESERVE_SCRIPT)

    async def test_returns_wait_in_seconds(self, limiter, script_mock):
        script_mock.return_value = 250

        wait = await limiter.reserve(666, cost=1, chat_id=42)

        assert wait == pytest.approx(0.25)

    async def test_returns_zero_when_redis_allows_immediately(self, limiter):
        wait = await limiter.reserve(666, cost=1, chat_id=42)

        assert wait == 0.0

    async def test_passes_bot_and_chat_keys(self, limiter, script_mock):
        await limiter.reserve(666, cost=1, chat_id=42)

        assert script_mock.call_args.kwargs["keys"] == [
            "kita:666:api:gcra",
            "kita:666:api:chat:42:gcra",
        ]

    async def test_passes_empty_chat_key_without_a_chat(self, limiter, script_mock):
        await limiter.reserve(666, cost=1, chat_id=None)

        keys = script_mock.call_args.kwargs["keys"]

        assert keys == ["kita:666:api:gcra", ""]

    async def test_derives_periods_and_tolerances_from_the_budget(self, limiter, script_mock):
        await limiter.reserve(666, cost=1, chat_id=42)

        period, tolerance, chat_period, chat_tolerance, _, _ = script_mock.call_args.kwargs["args"]

        assert period == pytest.approx(1 / RATE)
        assert tolerance == pytest.approx((BURST - 1) / RATE)
        assert chat_period == pytest.approx(1 / CHAT_RATE)
        assert chat_tolerance == pytest.approx((CHAT_BURST - 1) / CHAT_RATE)

    async def test_charges_the_chat_budget_only_when_a_chat_is_known(self, limiter, script_mock):
        await limiter.reserve(666, cost=1, chat_id=None)
        no_chat_args = script_mock.call_args.kwargs["args"]

        await limiter.reserve(666, cost=1, chat_id=42)
        with_chat_args = script_mock.call_args.kwargs["args"]

        assert no_chat_args[5] == 0
        assert with_chat_args[5] == 1

    async def test_lets_the_caller_override_the_chat_cost(self, limiter, script_mock):
        await limiter.reserve(666, cost=3, chat_id=42, chat_cost=2)

        args = script_mock.call_args.kwargs["args"]

        assert args[4] == 3
        assert args[5] == 2
