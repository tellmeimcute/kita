from aiogram.fsm.context import FSMContext
from aiogram.utils.i18n import I18n
from aiogram_dialog import BgManagerFactory
from aiogram_dialog.manager.bg_manager import BgManager
from dishka import Provider, Scope, provide
from dishka.integrations.aiogram import AiogramMiddlewareData

from core.i18n_translator import Translator
from interfaces import SuggestionQueueProtocol, SuggestionViewerProtocol
from ui.suggestion_queue import SuggestionQueue
from ui.suggestion_viewer import SuggestionViewer
from utils.message_parser import MessageParser
from utils.suggestion_utils import SuggestionUtils


class ViewerProvider(Provider):
    scope = Scope.REQUEST

    suggestion_queue = provide(SuggestionQueue, provides=SuggestionQueueProtocol)
    suggestion_viewer = provide(SuggestionViewer, provides=SuggestionViewerProtocol)


class UtilsProvider(Provider):
    scope = Scope.APP

    suggestion_utils = provide(SuggestionUtils, scope=Scope.REQUEST)
    translator = provide(Translator)
    message_parser = provide(MessageParser)

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
