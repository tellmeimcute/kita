from unittest.mock import AsyncMock, Mock

import pytest

from database.dto import UserDTO
from database.dto.suggestion import SuggestionFullDTO
from database.enums import UserRole, SuggestionStatus


@pytest.fixture
def admin_dto():
    return UserDTO(
        user_id=1,
        role=UserRole.ADMIN,
        name="Admin",
        username="admin",
        language_code="ru",
        prefer_anonymous=False,
        is_bot_blocked=False,
    )


@pytest.fixture
def user_dto():
    return UserDTO(
        user_id=2,
        role=UserRole.USER,
        name="User",
        username="user",
        language_code="en",
        prefer_anonymous=False,
        is_bot_blocked=False,
    )


@pytest.fixture
def suggestion_dto(admin_dto):
    return SuggestionFullDTO(
        id=1,
        author_id=2,
        author=admin_dto,
        media=[],
        caption="test suggestion",
        media_group_id=None,
        forwarded_from=None,
        status=SuggestionStatus.PENDING,
    )


@pytest.fixture
def config_mock():
    return Mock(ADMIN_ID=1)


@pytest.fixture
def user_service_mock():
    return Mock(
        get=AsyncMock(),
        update=AsyncMock(),
        decline_suggestion=AsyncMock(),
        spec=["get", "update", "decline_suggestion"],
    )


@pytest.fixture
def suggestion_service_mock():
    return Mock(
        update=AsyncMock(),
        spec=["update"],
    )


@pytest.fixture
def notifier_mock():
    return Mock(
        send=AsyncMock(),
        send_strategy_factory=Mock(),
        notify_user_i18n=AsyncMock(),
    )


@pytest.fixture
def utils_mock():
    return Mock(
        payload_factory=Mock(),
        get_i18n_kwargs=Mock(return_value={}),
    )


@pytest.fixture
def suggestion_repo_mock():
    return AsyncMock(
        get_by_id=AsyncMock(),
    )
