from unittest.mock import AsyncMock, Mock

import pytest
from aiogram.types import Message

from core.schemas.data import MassMessageData
from database.dto import UserDTO
from database.enums import UserRole
from usecases.broadcast import BroadcastUseCase


@pytest.fixture
def broadcast_usecase():
    user_service = Mock(get_active=AsyncMock())
    notifier = Mock(chunk_size=5, chunk_delay=5.0, forward_messages=AsyncMock(), copy_messages=AsyncMock())
    translator = Mock(get_translated_text=Mock(return_value="in_process"), get_i18n_text=Mock(return_value="status text"))
    return BroadcastUseCase(user_service=user_service, notifier=notifier, translator=translator)


@pytest.mark.asyncio
async def test_prepare_creates_mass_message_data(broadcast_usecase):
    users = [
        UserDTO(user_id=1, role=UserRole.USER, name="A", username="a", language_code="ru", prefer_anonymous=False, is_bot_blocked=False),
    ]
    broadcast_usecase._user_service.get_active.return_value = users

    message = Mock(spec=Message, chat=Mock(id=-100), forward_origin=None)
    message.message_id = 1
    album = (message,)

    result = await broadcast_usecase.prepare(message, album)

    assert isinstance(result, MassMessageData)
    assert result.users == users
    assert result.is_forwarded is False
    assert result.source_chat_id == -100
    assert result.source_message_ids == [1]


@pytest.mark.asyncio
async def test_estimate_time(broadcast_usecase):
    data = Mock(users_count=100)
    result = broadcast_usecase.estimate_time(data)
    assert result == (100 / 5) * 5.0
