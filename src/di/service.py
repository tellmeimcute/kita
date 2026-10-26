from dishka import Provider, Scope, provide

from interfaces import (
    MessageNotifierProtocol,
    SuggestionNotifierProtocol,
    SuggestionServiceProtocol,
    SuggestionTaskDispatcherProtocol,
    UserBotServiceProtocol,
    UserProfileServiceProtocol,
    UserServiceProtocol,
    WebhookServiceProtocol,
)
from services.notifier import MessageNotifier, SuggestionNotifier
from services.suggestion import SuggestionService
from services.user import UserService
from services.user_profile import UserProfileService
from services.userbots import UserBotService
from services.webhooks import WebhookService
from task_queue.dispatcher import SuggestionTaskDispatcher


class ServiceProvider(Provider):
    scope = Scope.REQUEST

    webhook_service = provide(WebhookService, provides=WebhookServiceProtocol, scope=Scope.APP)
    suggestion_tasks = provide(
        SuggestionTaskDispatcher,
        provides=SuggestionTaskDispatcherProtocol,
        scope=Scope.APP,
    )

    userbot_service = provide(UserBotService, provides=UserBotServiceProtocol)
    msg_notifier = provide(MessageNotifier, provides=MessageNotifierProtocol)
    suggestion_notifier = provide(SuggestionNotifier, provides=SuggestionNotifierProtocol)
    user_service = provide(UserService, provides=UserServiceProtocol)
    user_profile_service = provide(UserProfileService, provides=UserProfileServiceProtocol)
    suggestion_service = provide(SuggestionService, provides=SuggestionServiceProtocol)
