from collections.abc import Callable
from datetime import UTC, datetime
from itertools import count

import pytest

from database.dto import SuggestionFullDTO, UserDTO
from database.enums import SuggestionStatus


@pytest.fixture(scope="session")
def id_generator():
    return count(start=666_777)


@pytest.fixture
def user_dto_factory(id_generator) -> Callable[..., UserDTO]:
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
def test_user_dto(user_dto_factory) -> UserDTO:
    return user_dto_factory()


@pytest.fixture
def suggestion_factory(id_generator, test_user_dto: UserDTO) -> Callable[..., SuggestionFullDTO]:
    def _create_suggestion(**kwargs) -> SuggestionFullDTO:
        suggestion_id = next(id_generator)

        default_kwargs = {
            "id": suggestion_id,
            "author_id": test_user_dto.user_id,
            "status": SuggestionStatus.PENDING,
            "caption": "test_test",
            "media_group_id": None,
            "forwarded_from": None,
            "anonymous": False,
            "author": test_user_dto,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        default_kwargs.update(kwargs)

        return SuggestionFullDTO(**default_kwargs)

    return _create_suggestion


@pytest.fixture
def test_suggestion(suggestion_factory) -> SuggestionFullDTO:
    return suggestion_factory()
