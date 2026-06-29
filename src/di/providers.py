
from dishka import Provider, Scope, provide
from dishka.integrations.aiogram import AiogramMiddlewareData

from aiogram.fsm.context import FSMContext
from aiogram.utils.i18n import I18n
from aiogram_dialog import BgManagerFactory
from aiogram_dialog.manager.bg_manager import BgManager

from core.schemas import SuggestionViewerData
from core.i18n_translator import Translator
from core.events import EventBus

from services.user import UserService
from services.suggestion import SuggestionService
from services.notifier import NotifierService
from services.message_parser import MessageParser

from database.uow import UnitOfWork
from database.repository import (
    SuggestionRepository,
    UserRepository,
    MediaRepository
)

from usecases import (
    BroadcastUseCase,
    ChangeRoleUseCase,
    ModerateSuggestionUseCase,
)

from interfaces import (
    UserRepositoryProtocol,
    SuggestionRepositoryProtocol,
    MediaRepositoryProtocol,
    UnitOfWorkProtocol,
    UserServiceProtocol,
    SuggestionServiceProtocol,
)

from ui.suggestion_utils import SuggestionUtils
from ui.suggestion_renderer import SuggestionRenderer

class InfraProvider(Provider):
    event_bus = provide(EventBus, scope=Scope.APP)

    notifier_service = provide(NotifierService, scope=Scope.APP)
    user_service = provide(source=UserService, provides=UserServiceProtocol, scope=Scope.REQUEST)
    suggestion_service = provide(source=SuggestionService, provides=SuggestionServiceProtocol, scope=Scope.REQUEST)
    
    suggestion_repo = provide(source=SuggestionRepository, provides=SuggestionRepositoryProtocol, scope=Scope.REQUEST)
    user_repo = provide(source=UserRepository, provides=UserRepositoryProtocol, scope=Scope.REQUEST)
    media_repo = provide(source=MediaRepository, provides=MediaRepositoryProtocol, scope=Scope.REQUEST)

    uow = provide(source=UnitOfWork, provides=UnitOfWorkProtocol, scope=Scope.REQUEST)

    moderate_suggestion = provide(ModerateSuggestionUseCase, scope=Scope.REQUEST)
    change_role = provide(ChangeRoleUseCase, scope=Scope.REQUEST)
    broadcast = provide(BroadcastUseCase, scope=Scope.REQUEST)


class UtilsProvider(Provider):
    translator = provide(Translator, scope=Scope.APP)
    suggestion_utils = provide(SuggestionUtils, scope=Scope.APP)
    suggestion_renderer = provide(SuggestionRenderer, scope=Scope.APP)
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