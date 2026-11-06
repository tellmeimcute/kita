from .bot import (
    BotContextProtocol,
    BotResolverProtocol,
    BotSessionProtocol,
)
from .dispatcher import SuggestionTaskDispatcherProtocol
from .notifier import MessageNotifierProtocol, SuggestionNotifierProtocol
from .repository import (
    MediaRepositoryProtocol,
    SuggestionRepositoryProtocol,
    UserBotRepositoryProtocol,
    UserBotStatsRepositoryProtocol,
    UserProfileRepositoryProtocol,
    UserRepositoryProtocol,
)
from .services import (
    SuggestionQueueProtocol,
    SuggestionServiceProtocol,
    SuggestionViewerProtocol,
    UserBotServiceProtocol,
    UserProfileServiceProtocol,
    UserServiceProtocol,
    WebhookServiceProtocol,
)
from .uow import UnitOfWorkProtocol

__all__ = (
    "BotContextProtocol",
    "BotResolverProtocol",
    "BotSessionProtocol",
    "MessageNotifierProtocol",
    "MediaRepositoryProtocol",
    "SuggestionNotifierProtocol",
    "SuggestionRepositoryProtocol",
    "UserBotRepositoryProtocol",
    "UserBotServiceProtocol",
    "UserBotStatsRepositoryProtocol",
    "UserProfileRepositoryProtocol",
    "UserRepositoryProtocol",
    "SuggestionServiceProtocol",
    "UserProfileServiceProtocol",
    "UserServiceProtocol",
    "SuggestionQueueProtocol",
    "SuggestionViewerProtocol",
    "UnitOfWorkProtocol",
    "SuggestionTaskDispatcherProtocol",
    "WebhookServiceProtocol",
)
