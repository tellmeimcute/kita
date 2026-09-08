import asyncio
from unittest.mock import patch

import pytest
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter

from services.notifier import NotifierUtilsMixin, with_retry

MAX_RETRIES = 3
RETRY_THEN_SUCCESS_CALLS = 2
MAX_EXCEEDED_CALLS = 3
RETRY_TWICE_SUCCESS_AT = 3
EXPECTED_RETRY_SLEEPS = 2


class TestNotifierUtilsMixin:
    def test_parse_target_id_user_dto(self, test_user_dto):
        result = NotifierUtilsMixin()._parse_target_id(test_user_dto)
        assert result == test_user_dto.user_id

    def test_parse_target_id_user_profile_dto(self, test_profile_dto):
        result = NotifierUtilsMixin()._parse_target_id(test_profile_dto)
        assert result == test_profile_dto.user_id

    def test_parse_target_id_int(self):
        value = 67890
        result = NotifierUtilsMixin()._parse_target_id(value)
        assert result == value


class TestWithRetryDecorator:
    async def test_successful_call_no_retries(self):
        call_count = 0

        @with_retry(max_retries=MAX_RETRIES)
        async def succeed_once():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await succeed_once()
        assert result == "success"
        assert call_count == 1

    async def test_retry_after_then_success(self):
        call_count = 0

        async def mock_sleep(_duration):
            return None

        with patch.object(asyncio, "sleep", mock_sleep):

            @with_retry(max_retries=MAX_RETRIES)
            async def retry_then_succeed():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise TelegramRetryAfter(
                        method="sendMessage", message="Rate limit", retry_after=0.01
                    )
                return "success"

            result = await retry_then_succeed()

        assert result == "success"
        assert call_count == RETRY_THEN_SUCCESS_CALLS

    async def test_max_retries_exceeded_raises(self):
        call_count = 0

        async def mock_sleep(_duration):
            return None

        with patch.object(asyncio, "sleep", mock_sleep):

            @with_retry(max_retries=2)
            async def always_retry_after():
                nonlocal call_count
                call_count += 1
                raise TelegramRetryAfter(
                    method="sendMessage", message="Rate limit", retry_after=0.001
                )

            with pytest.raises(TelegramRetryAfter):
                await always_retry_after()

        assert call_count == MAX_EXCEEDED_CALLS

    async def test_api_error_raises_immediately(self):
        @with_retry(max_retries=MAX_RETRIES)
        async def api_error():
            raise TelegramAPIError(method="sendMessage", message="API Error")

        with pytest.raises(TelegramAPIError):
            await api_error()

    async def test_retry_sleep_duration_exact(self):
        sleeps = []

        async def mock_sleep(duration):
            sleeps.append(duration)

        with patch.object(asyncio, "sleep", mock_sleep):
            call_count = 0

            @with_retry(max_retries=2)
            async def retry_twice():
                nonlocal call_count
                call_count += 1
                if call_count < RETRY_TWICE_SUCCESS_AT:
                    raise TelegramRetryAfter(
                        method="sendMessage", message="Rate limit", retry_after=0.05
                    )
                return "success"

            await retry_twice()

        assert len(sleeps) == EXPECTED_RETRY_SLEEPS
        assert all(s == 1.0 for s in sleeps)
