
from unittest.mock import AsyncMock, Mock
import pytest

from core.exceptions import SQLSuggestionNotFoundError
from services.suggestion import SuggestionService


@pytest.mark.asyncio
async def test_get_by_id_none(suggestion_repo_mock):
    suggestion_repo_mock.get_by_id.return_value = None

    service = SuggestionService(
        session=AsyncMock(),
        redis=AsyncMock(),
        repo=suggestion_repo_mock,
        parser=Mock(),
    )

    with pytest.raises(SQLSuggestionNotFoundError):
        dto = await service.get(1)


@pytest.mark.asyncio
async def test_get_by_id_some(suggestion_repo_mock):
    something = [1, 2, 3]
    suggestion_repo_mock.get_by_id.return_value = something

    service = SuggestionService(
        session=AsyncMock(),
        redis=AsyncMock(),
        repo=suggestion_repo_mock,
        parser=Mock(),
    )

    dto = await service.get(1)
    assert dto == something