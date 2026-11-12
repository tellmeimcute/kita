from dishka import AsyncContainer, Provider, Scope, provide

from events import EventBus, ListenerRegistry
from events.listeners import (
    EnqueueAdminNotifyNewSuggestion,
    EnqueueAdminNotifyNewUser,
    EnqueueNewUserbot,
    EnqueueSuggestionAccepted,
)
from interfaces import EventBusProtocol, EventListenerProtocol

APPLICATION_LISTENERS: tuple[type[EventListenerProtocol], ...] = (
    EnqueueAdminNotifyNewSuggestion,
    EnqueueSuggestionAccepted,
    EnqueueAdminNotifyNewUser,
    EnqueueNewUserbot,
)


def register_listeners(registry: ListenerRegistry) -> None:
    for listener_type in APPLICATION_LISTENERS:
        registry.add(listener_type)


class EventProvider(Provider):
    scope = Scope.REQUEST

    notify_new_suggestion = provide(EnqueueAdminNotifyNewSuggestion)
    suggestion_accepted = provide(EnqueueSuggestionAccepted)
    notify_new_user = provide(EnqueueAdminNotifyNewUser)
    new_userbot = provide(EnqueueNewUserbot)

    @provide(scope=Scope.APP)
    def listener_registry(self) -> ListenerRegistry:
        """Filled by ``register_listeners`` at startup."""

        return ListenerRegistry()

    @provide
    def event_bus(
        self,
        registry: ListenerRegistry,
        container: AsyncContainer,
    ) -> EventBusProtocol:
        return EventBus(registry, container)
