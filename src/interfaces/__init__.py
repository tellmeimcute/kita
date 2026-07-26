from .repository import (
    UserRepositoryProtocol,
    UserProfileRepositoryProtocol,
    MediaRepositoryProtocol,
    SuggestionRepositoryProtocol,
    UserBotRepositoryProtocol,
)

from .services import (
    UserServiceProtocol,
    UserProfileServiceProtocol,
    SuggestionServiceProtocol,
    NotifierServiceProtocol,
)

from .uow import UnitOfWorkProtocol

from .bot_registry import BotRegistryProtocol
