from dishka import Provider, Scope, provide

from database.redis import CacheJournal
from database.repository import (
    MediaRepository,
    SuggestionRepository,
    UserBotRepository,
    UserProfileRepository,
    UserRepository,
)
from database.repository.cached import (
    CachedSuggestionRepository,
    CachedUserBotRepository,
    CachedUserBotStatsRepository,
    CachedUserProfileRepository,
    CachedUserRepository,
)
from database.uow import UnitOfWork
from interfaces import (
    MediaRepositoryProtocol,
    SuggestionRepositoryProtocol,
    UnitOfWorkProtocol,
    UserBotRepositoryProtocol,
    UserBotStatsRepositoryProtocol,
    UserProfileRepositoryProtocol,
    UserRepositoryProtocol,
)


class RepositoryProvider(Provider):
    scope = Scope.REQUEST

    raw_suggestion_repo = provide(SuggestionRepository)
    suggestion_repo = provide(CachedSuggestionRepository, provides=SuggestionRepositoryProtocol)

    raw_user_repo = provide(UserRepository)
    raw_profile_repo = provide(UserProfileRepository)

    user_repo = provide(CachedUserRepository, provides=UserRepositoryProtocol)
    user_profile_repo = provide(
        CachedUserProfileRepository, provides=UserProfileRepositoryProtocol
    )

    media_repo = provide(MediaRepository, provides=MediaRepositoryProtocol)

    raw_userbot_repo = provide(UserBotRepository)
    userbot_repo = provide(CachedUserBotRepository, provides=UserBotRepositoryProtocol)
    userbot_stats = provide(CachedUserBotStatsRepository, provides=UserBotStatsRepositoryProtocol)

    journal = provide(CacheJournal)

    uow = provide(UnitOfWork, provides=UnitOfWorkProtocol)
