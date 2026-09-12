import itertools
from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from database.dto import SuggestionFullDTO, UserDTO
from database.enums import SuggestionStatus


@pytest.fixture(scope="session")
def id_generator():
    return itertools.count(start=666_777)


@pytest.fixture
def test_user_dto() -> UserDTO:
    return UserDTO(
        user_id=2131,
        username="test_user",
        name="testing",
        language_code="ru",
    )


@pytest.fixture
def create_user_dto(id_generator) -> Callable[..., UserDTO]:
    def _create_user(**kwargs) -> UserDTO:
        user_id = next(id_generator)

        default_kwargs = {
            "user_id": user_id,
            "username": f"test_user_{user_id}",
            "name": "testing",
            "language_code": "ru",
        }
        default_kwargs.update(kwargs)

        return UserDTO(**default_kwargs)

    return _create_user


@pytest.fixture
def test_suggestion(test_user_dto) -> SuggestionFullDTO:
    return SuggestionFullDTO(
        id=1,
        author_id=test_user_dto.user_id,
        status=SuggestionStatus.PENDING,
        caption="test_test",
        media_group_id=None,
        forwarded_from=None,
        anonymous=False,
        author=test_user_dto,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
