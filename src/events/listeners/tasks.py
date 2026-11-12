from core.userbot_dispatcher import UserbotDispatcherState
from events.base import EventListener
from events.definitions import (
    SuggestionAccepted,
    SuggestionCreated,
    UserbotRegistered,
    UserProfileCreated,
)
from interfaces import UserBotServiceProtocol
from task_queue.tasks import (
    admin_notify_new_suggestion,
    admin_notify_new_user,
    new_userbot,
    suggestion_accepted,
)


class EnqueueAdminNotifyNewSuggestion(EventListener[SuggestionCreated]):
    event_type = SuggestionCreated

    async def handle(self, event: SuggestionCreated) -> None:
        await admin_notify_new_suggestion.kiq(
            bot_id=event.bot_id,
            suggestion_id=event.suggestion_id,
        )


class EnqueueSuggestionAccepted(EventListener[SuggestionAccepted]):
    event_type = SuggestionAccepted

    async def handle(self, event: SuggestionAccepted) -> None:
        await suggestion_accepted.kiq(
            bot_id=event.bot_id,
            suggestion_id=event.suggestion_id,
        )


class EnqueueAdminNotifyNewUser(EventListener[UserProfileCreated]):
    event_type = UserProfileCreated

    def __init__(self, userbot_service: UserBotServiceProtocol):
        self._userbot_service = userbot_service

    async def handle(self, event: UserProfileCreated) -> None:
        # the registrar bot is not a row of ``userbots``: it has no owner to notify
        if await self._userbot_service.get(event.bot_id) is None:
            return

        await admin_notify_new_user.kiq(
            bot_id=event.bot_id,
            new_user_id=event.user_id,
        )


class EnqueueNewUserbot(EventListener[UserbotRegistered]):
    event_type = UserbotRegistered

    def __init__(self, userbot_dispatcher: UserbotDispatcherState):
        self._userbot_dispatcher = userbot_dispatcher

    async def handle(self, event: UserbotRegistered) -> None:
        await new_userbot.kiq(
            bot_id=event.bot_id,
            userbot_id=event.userbot_id,
            owner_id=event.owner_id,
            allowed_updates=self._userbot_dispatcher.allowed_updates,
        )
