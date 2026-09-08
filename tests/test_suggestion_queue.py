from unittest.mock import AsyncMock, MagicMock

import pytest

from database.dto import SuggestionFullDTO
from services.suggestion_queue import SuggestionQueue

QUEUE_SIZE = 2


@pytest.fixture
def mock_suggestion_service():
    service = MagicMock()
    service.get_active = AsyncMock()
    return service


@pytest.fixture
def mock_uow():
    uow = MagicMock()
    uow.transaction = MagicMock()
    return uow


@pytest.fixture
def queue(mock_bot_registry, mock_suggestion_service, mock_uow, mock_fsm):
    return SuggestionQueue(
        bot_registry=mock_bot_registry,
        suggestion_service=mock_suggestion_service,
        uow=mock_uow,
        fsm_context=mock_fsm,
    )


class TestSuggestionQueue:
    async def test_get_queue_returns_empty_list(self, queue, mock_fsm):
        mock_fsm.get_data.return_value = {}

        result = await queue.get_queue()

        assert result == []

    async def test_get_queue_returns_existing_queue(self, queue, mock_fsm, test_suggestion):
        mock_fsm.get_data.return_value = {
            "suggestion_queue": [
                test_suggestion.model_dump(mode="json"),
                test_suggestion.model_copy(update={"id": 82184}).model_dump(mode="json"),
            ],
        }

        result = await queue.get_queue()

        assert len(result) == QUEUE_SIZE
        assert result[0]["id"] == test_suggestion.id

    async def test_seed_queue_stores_suggestions(self, queue, mock_fsm, test_suggestion):
        result = await queue.seed_queue([test_suggestion])

        assert len(result) == 1
        mock_fsm.update_data.assert_called_once()

    async def test_next_suggestion_returns_from_queue(self, queue, mock_fsm, test_suggestion):
        mock_fsm.get_data.return_value = {
            "suggestion_queue": [test_suggestion.model_dump(mode="json")]
        }

        result = await queue.next_suggestion()

        assert isinstance(result, SuggestionFullDTO)
        mock_fsm.update_data.assert_called_once()

    async def test_next_suggestion_fetches_new_when_empty(
        self, queue, mock_fsm, mock_suggestion_service, test_suggestion
    ):
        mock_fsm.get_data.return_value = {"suggestion_queue": []}
        mock_suggestion_service.get_active.return_value = [test_suggestion]

        result = await queue.next_suggestion()

        assert isinstance(result, SuggestionFullDTO)
        mock_suggestion_service.get_active.assert_called_once()

    async def test_next_suggestion_returns_none_when_no_suggestions(
        self, queue, mock_fsm, mock_suggestion_service
    ):
        mock_fsm.get_data.return_value = {"suggestion_queue": []}

        mock_suggestion_service.get_active.return_value = []

        result = await queue.next_suggestion()

        assert result is None
