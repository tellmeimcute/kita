from dishka import Provider, Scope, provide

from core.userbot_dispatcher import UserbotDispatcherState
from events import EventBus
from events.listeners import (
    EnqueueAdminNotifyNewSuggestion,
    EnqueueAdminNotifyNewUser,
    EnqueueNewUserbot,
    EnqueueSuggestionAccepted,
)
from interfaces import EventBusProtocol, EventListenerProtocol, UserBotServiceProtocol


class EventProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def listeners(
        self,
        userbot_dispatcher: UserbotDispatcherState,
        userbot_service: UserBotServiceProtocol,
    ) -> list[EventListenerProtocol]:
        return [
            EnqueueAdminNotifyNewSuggestion(),
            EnqueueSuggestionAccepted(),
            EnqueueAdminNotifyNewUser(userbot_service),
            EnqueueNewUserbot(userbot_dispatcher),
        ]

    @provide
    def event_bus(self, listeners: list[EventListenerProtocol]) -> EventBusProtocol:
        return EventBus(listeners)
