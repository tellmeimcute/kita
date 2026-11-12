from unittest.mock import AsyncMock, MagicMock

from events import UserProfileCreated
from events.listeners import EnqueueAdminNotifyNewUser
from task_queue.tasks import admin_notify_new_user

EVENT = UserProfileCreated(bot_id=100, user_id=555)


async def test_new_profile_of_a_registered_bot_notifies_the_owner(monkeypatch):
    kiq = AsyncMock()
    monkeypatch.setattr(admin_notify_new_user, "kiq", kiq)
    userbot_service = MagicMock(get=AsyncMock(return_value=MagicMock()))

    await EnqueueAdminNotifyNewUser(userbot_service).handle(EVENT)

    userbot_service.get.assert_awaited_once_with(100)
    kiq.assert_awaited_once_with(bot_id=100, new_user_id=555)


async def test_new_profile_of_a_bot_without_owner_is_skipped(monkeypatch):
    kiq = AsyncMock()
    monkeypatch.setattr(admin_notify_new_user, "kiq", kiq)
    userbot_service = MagicMock(get=AsyncMock(return_value=None))

    await EnqueueAdminNotifyNewUser(userbot_service).handle(EVENT)

    kiq.assert_not_awaited()
