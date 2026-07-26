
from dishka import Provider, Scope, provide
from dishka.integrations.aiogram import AiogramMiddlewareData

from aiogram.fsm.context import FSMContext
from aiogram.utils.i18n import I18n
from aiogram_dialog import BgManagerFactory
from aiogram_dialog.manager.bg_manager import BgManager

from core.config import Config
from core.schemas import SuggestionViewerData
from core.i18n_translator import Translator
from core.events import EventBus

from services.user import UserService
from services.user_profile import UserProfileService
from services.suggestion import SuggestionService
from services.notifier import NotifierService
from services.message_parser import MessageParser
from services.webhooks import WebhookService
from services.userbots import UserBotService

from database.uow import UnitOfWork
from database.repository import (
    SuggestionRepository,
    UserRepository,
    UserProfileRepository,
    MediaRepository,
    UserBotRepository,
)

from usecases import (
    BroadcastUseCase,
    ChangeRoleUseCase,
    ModerateSuggestionUseCase,
)

from interfaces import (
    UserRepositoryProtocol,
    UserProfileRepositoryProtocol,
    SuggestionRepositoryProtocol,
    MediaRepositoryProtocol,
    UnitOfWorkProtocol,
    UserServiceProtocol,
    UserProfileServiceProtocol,
    SuggestionServiceProtocol,
    NotifierServiceProtocol,
    UserBotRepositoryProtocol,
)

from ui.suggestion_utils import SuggestionUtils

class InfraProvider(Provider):
    event_bus = provide(EventBus, scope=Scope.APP)

    webhook_service = provide(WebhookService, scope=Scope.APP)
    userbot_service = provide(UserBotService, scope=Scope.REQUEST)

    notifier_service = provide(source=NotifierService, provides=NotifierServiceProtocol, scope=Scope.REQUEST)
    user_service = provide(source=UserService, provides=UserServiceProtocol, scope=Scope.REQUEST)
    user_profile_service = provide(source=UserProfileService, provides=UserProfileServiceProtocol, scope=Scope.REQUEST)
    suggestion_service = provide(source=SuggestionService, provides=SuggestionServiceProtocol, scope=Scope.REQUEST)

    suggestion_repo = provide(source=SuggestionRepository, provides=SuggestionRepositoryProtocol, scope=Scope.REQUEST)
    user_repo = provide(source=UserRepository, provides=UserRepositoryProtocol, scope=Scope.REQUEST)
    user_profile_repo = provide(source=UserProfileRepository, provides=UserProfileRepositoryProtocol, scope=Scope.REQUEST)
    media_repo = provide(source=MediaRepository, provides=MediaRepositoryProtocol, scope=Scope.REQUEST)
    userbot_repo = provide(source=UserBotRepository, provides=UserBotRepositoryProtocol, scope=Scope.REQUEST)

    uow = provide(source=UnitOfWork, provides=UnitOfWorkProtocol, scope=Scope.REQUEST)

    moderate_suggestion = provide(ModerateSuggestionUseCase, scope=Scope.REQUEST)
    change_role = provide(ChangeRoleUseCase, scope=Scope.REQUEST)
    broadcast = provide(BroadcastUseCase, scope=Scope.REQUEST)

    @provide(scope=Scope.APP)
    def config(self) -> Config:
        return Config()


class UtilsProvider(Provider):
    translator = provide(Translator, scope=Scope.APP)
    suggestion_utils = provide(SuggestionUtils, scope=Scope.REQUEST)
    message_parser = provide(MessageParser, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def i18n(self) -> I18n:
        return I18n(path="locales", default_locale="ru", domain="messages")


class FSMProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def fsm_context(self, middleware_data: AiogramMiddlewareData) -> FSMContext:
        return middleware_data["state"]

    @provide(scope=Scope.REQUEST)
    async def background_manager(self, middleware_data: AiogramMiddlewareData) -> BgManager:
        bg_factory: BgManagerFactory = middleware_data.get("dialog_bg_factory")
        from_user = middleware_data.get("event_from_user")
        chat = middleware_data.get("event_chat")
        bot = middleware_data.get("bot")
        return bg_factory.bg(bot, from_user.id, chat.id)

    @provide(scope=Scope.REQUEST)
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
