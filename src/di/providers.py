
from dishka import Provider, Scope, provide
from dishka.integrations.aiogram import AiogramMiddlewareData

from aiogram.fsm.context import FSMContext
from aiogram.utils.i18n import I18n

from services.user import UserService
from services.suggestion import SuggestionService
from services.notifier import NotifierService

from core.i18n_translator import Translator
from helpers.suggestion_utils import SuggestionUtils


class ServicesProvider(Provider):
    user_service = provide(UserService, scope=Scope.REQUEST)
    suggestion_service = provide(SuggestionService, scope=Scope.REQUEST)
    notifier_service = provide(NotifierService, scope=Scope.APP)

class UtilsProvider(Provider):
    translator = provide(Translator, scope=Scope.APP)
    suggestion_utils = provide(SuggestionUtils, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def i18n(self) -> I18n:
        return I18n(path="locales", default_locale="ru", domain="messages")

class FSMProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def fsm_context(self, middleware_data: AiogramMiddlewareData) -> FSMContext:
        return middleware_data["state"]
    