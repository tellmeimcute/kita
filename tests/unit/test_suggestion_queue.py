from unittest.mock import AsyncMock, MagicMock, call

import pytest

from ui.suggestion_queue import SuggestionQueue

QUEUE_SIZE = 2


@pytest.fixture
def mock_suggestion_service():
    service = MagicMock()
    service.get_active_ids = AsyncMock()
    service.get_active_by_id = AsyncMock()
    return service


@pytest.fixture
def mock_uow():
    uow = MagicMock()
    uow.transaction = MagicMock()
    return uow


@pytest.fixture
def queue(mock_bot_context, mock_suggestion_service, mock_uow, mock_fsm):
    return SuggestionQueue(
        bot_context=mock_bot_context,
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
        ids = [test_suggestion.id, test_suggestion.id + 1]
        mock_fsm.get_data.return_value = {"suggestion_queue": ids}

        result = await queue.get_queue()

        assert result == ids
        assert len(result) == QUEUE_SIZE

    async def test_seed_queue_stores_ids(self, queue, mock_fsm, test_suggestion):
        result = await queue.seed_queue([test_suggestion.id])

        assert result == [test_suggestion.id]
        mock_fsm.update_data.assert_awaited_once_with({"suggestion_queue": [test_suggestion.id]})

    async def test_next_suggestion_returns_from_queue(
        self, queue, mock_fsm, mock_suggestion_service, test_suggestion
    ):
        remaining_id = test_suggestion.id + 1
        mock_fsm.get_data.return_value = {"suggestion_queue": [test_suggestion.id, remaining_id]}
        mock_suggestion_service.get_active_by_id.return_value = test_suggestion

        result = await queue.next_suggestion()

        assert result is test_suggestion
        mock_suggestion_service.get_active_by_id.assert_awaited_once_with(test_suggestion.id)
        mock_suggestion_service.get_active_ids.assert_not_awaited()
        mock_fsm.update_data.assert_awaited_once_with({"suggestion_queue": [remaining_id]})

    async def test_next_suggestion_skips_missing_or_moderated(
        self, queue, mock_fsm, mock_suggestion_service, test_suggestion, suggestion_factory
    ):
        stale = suggestion_factory()
        mock_fsm.get_data.return_value = {"suggestion_queue": [stale.id, test_suggestion.id]}
        mock_suggestion_service.get_active_by_id.side_effect = [None, test_suggestion]

        # Snapshot each update: the queue list is mutated in place between pops.
        updates = []

        async def record_update(data):
            updates.append({"suggestion_queue": list(data["suggestion_queue"])})

        mock_fsm.update_data.side_effect = record_update

        result = await queue.next_suggestion()

        assert result is test_suggestion
        assert mock_suggestion_service.get_active_by_id.await_args_list == [
            call(stale.id),
            call(test_suggestion.id),
        ]
        assert updates == [
            {"suggestion_queue": [test_suggestion.id]},
            {"suggestion_queue": []},
        ]

    async def test_next_suggestion_fetches_new_ids_when_empty(
        self, queue, mock_fsm, mock_suggestion_service, test_suggestion
    ):
        mock_fsm.get_data.return_value = {"suggestion_queue": []}
        mock_suggestion_service.get_active_ids.return_value = [test_suggestion.id]
        mock_suggestion_service.get_active_by_id.return_value = test_suggestion

        result = await queue.next_suggestion()

        assert result is test_suggestion
        mock_suggestion_service.get_active_ids.assert_awaited_once()
        mock_suggestion_service.get_active_by_id.assert_awaited_once_with(test_suggestion.id)

    async def test_next_suggestion_returns_none_when_no_suggestions(
        self, queue, mock_fsm, mock_suggestion_service
    ):
        mock_fsm.get_data.return_value = {"suggestion_queue": []}
        mock_suggestion_service.get_active_ids.return_value = []

        result = await queue.next_suggestion()

        assert result is None
        mock_suggestion_service.get_active_by_id.assert_not_awaited()

    async def test_next_suggestion_refetches_when_all_queued_ids_are_stale(
        self, queue, mock_fsm, mock_suggestion_service, test_suggestion
    ):
        mock_fsm.get_data.return_value = {"suggestion_queue": [test_suggestion.id]}
        mock_suggestion_service.get_active_by_id.return_value = None
        mock_suggestion_service.get_active_ids.return_value = []

        result = await queue.next_suggestion()

        assert result is None
        mock_suggestion_service.get_active_ids.assert_awaited_once()
