from aiogram.fsm.context import FSMContext
from aiogram.utils.i18n import I18n
from aiogram_dialog import BgManagerFactory
from aiogram_dialog.manager.bg_manager import BgManager
from dishka import Provider, Scope, provide
from dishka.integrations.aiogram import AiogramMiddlewareData

from core.config import Config
from core.cryptographer import Cryptographer
from core.i18n_translator import Translator
from core.schemas import SuggestionViewerData
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
    MessageNotifierProtocol,
    SuggestionNotifierProtocol,
    SuggestionRepositoryProtocol,
    SuggestionServiceProtocol,
    UnitOfWorkProtocol,
    UserBotRepositoryProtocol,
    UserBotStatsRepositoryProtocol,
    UserProfileRepositoryProtocol,
    UserProfileServiceProtocol,
    UserRepositoryProtocol,
    UserServiceProtocol,
)
from services.notifier import MessageNotifier, SuggestionNotifier
from services.suggestion import SuggestionService
from services.user import UserService
from services.user_profile import UserProfileService
from services.userbots import UserBotService
from services.webhooks import WebhookService
from usecases import (
    BroadcastUseCase,
    ChangeRoleUseCase,
    MessageUserUseCase,
    ModerateSuggestionUseCase,
)
from utils.message_parser import MessageParser
from utils.suggestion_utils import SuggestionUtils
from utils.userbot_checker import UserBotChecker


class InfraProvider(Provider):
    scope = Scope.REQUEST

    cryptographer = provide(Cryptographer, scope=Scope.APP)

    webhook_service = provide(WebhookService, scope=Scope.APP)

    userbot_service = provide(UserBotService)
    msg_notifier = provide(MessageNotifier, provides=MessageNotifierProtocol)
    suggestion_notifier = provide(SuggestionNotifier, provides=SuggestionNotifierProtocol)
    user_service = provide(UserService, provides=UserServiceProtocol)
    user_profile_service = provide(UserProfileService, provides=UserProfileServiceProtocol)
    suggestion_service = provide(SuggestionService, provides=SuggestionServiceProtocol)

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

    uow = provide(UnitOfWork, provides=UnitOfWorkProtocol)

    moderate_suggestion = provide(ModerateSuggestionUseCase)
    change_role = provide(ChangeRoleUseCase)
    broadcast = provide(BroadcastUseCase)
    message_user = provide(MessageUserUseCase)

    @provide(scope=Scope.APP)
    def config(self) -> Config:
        return Config.get()


class UtilsProvider(Provider):
    scope = Scope.APP

    suggestion_utils = provide(SuggestionUtils, scope=Scope.REQUEST)
    translator = provide(Translator)
    message_parser = provide(MessageParser)
    userbot_checker = provide(UserBotChecker)

    @provide
    def i18n(self) -> I18n:
        return I18n(path="locales", default_locale="ru", domain="messages")


class FSMProvider(Provider):
    scope = Scope.REQUEST

    @provide
    async def fsm_context(self, middleware_data: AiogramMiddlewareData) -> FSMContext:
        return middleware_data["state"]

    @provide
    async def background_manager(self, middleware_data: AiogramMiddlewareData) -> BgManager:
        bg_factory: BgManagerFactory = middleware_data.get("dialog_bg_factory")
        from_user = middleware_data.get("event_from_user")
        chat = middleware_data.get("event_chat")
        bot = middleware_data.get("bot")
        return bg_factory.bg(bot, from_user.id, chat.id)

    @provide
    async def viewer_data(
        self,
        fsm: FSMContext,
        middleware_data: AiogramMiddlewareData,
    ) -> SuggestionViewerData:
        data = await fsm.get_data()
        raw_viewer_data = data.get("viewer_data")

        if not raw_viewer_data:
            user_dto = middleware_data.get("user_dto")
            return SuggestionViewerData(user_dto=user_dto)

        return SuggestionViewerData.model_validate(raw_viewer_data)
