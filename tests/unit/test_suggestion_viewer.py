from unittest.mock import AsyncMock, MagicMock

import pytest

from database.dto import SuggestionFullDTO
from services.suggestion_viewer import SuggestionViewer


@pytest.fixture
def mock_suggestion_queue():
    queue = MagicMock()
    queue.next_suggestion = AsyncMock()
    return queue


@pytest.fixture
def mock_suggestion_notifier():
    notifier = MagicMock()
    notifier.send_to_admin = AsyncMock()
    return notifier


@pytest.fixture
def mock_msg_notifier():
    notifier = MagicMock()
    notifier.send_text = AsyncMock()
    return notifier


@pytest.fixture
def mock_suggestion_utils():
    return MagicMock()


@pytest.fixture
def viewer(
    mock_bot_registry,
    mock_suggestion_queue,
    mock_suggestion_notifier,
    mock_msg_notifier,
    mock_suggestion_utils,
    mock_fsm,
):
    return SuggestionViewer(
        bot_registry=mock_bot_registry,
        suggestion_queue=mock_suggestion_queue,
        suggestion_notifier=mock_suggestion_notifier,
        suggestion_utils=mock_suggestion_utils,
        notifier=mock_msg_notifier,
        fsm_context=mock_fsm,
    )


class TestSuggestionViewer:
    async def test_advance_with_suggestion(
        self,
        viewer,
        mock_suggestion_queue,
        mock_suggestion_notifier,
        mock_fsm,
        test_user_dto,
        test_suggestion,
    ):
        mock_suggestion_queue.next_suggestion.return_value = test_suggestion

        result = await viewer.advance(test_user_dto)

        assert result is True
        mock_suggestion_notifier.send_to_admin.assert_called_once()
        mock_fsm.update_data.assert_called_once()

    async def test_advance_without_suggestion(self, viewer, mock_suggestion_queue, test_user_dto):
        mock_suggestion_queue.next_suggestion.return_value = None

        result = await viewer.advance(test_user_dto)

        assert result is False

    async def test_get_current_returns_suggestion(self, viewer, mock_fsm, test_suggestion):
        mock_fsm.get_data.return_value = {
            "current_suggestion": test_suggestion.model_dump(mode="json")
        }

        result = await viewer.get_current()

        assert isinstance(result, SuggestionFullDTO)

    async def test_get_current_returns_none_when_empty(self, viewer, mock_fsm):
        mock_fsm.get_data.return_value = {}

        result = await viewer.get_current()

        assert result is None

    async def test_return_to_menu(
        self,
        viewer,
        mock_fsm,
        mock_msg_notifier,
        test_user_dto,
    ):
        mock_manager = MagicMock()
        mock_manager.start = AsyncMock()

        await viewer.return_to_menu(mock_manager, test_user_dto)

        mock_fsm.clear.assert_called_once()
        mock_msg_notifier.send_text.assert_called_once()
        mock_manager.start.assert_called_once()
