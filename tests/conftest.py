from datetime import UTC, datetime
import pytest
from database.dto import SuggestionFullDTO, UserDTO, UserProfileDTO
from database.enums import SuggestionStatus


@pytest.fixture
def test_user_dto() -> UserDTO:
    return UserDTO(
        user_id=2131,
        username="test_user",
        name="testing",
        language_code="ru",
    )


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