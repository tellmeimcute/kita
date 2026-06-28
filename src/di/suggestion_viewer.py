
from dishka import Provider, Scope, provide
from dishka.integrations.aiogram import AiogramMiddlewareData
from aiogram.fsm.context import FSMContext

from core.schemas import SuggestionViewerData
from services.suggestion_queue import SuggestionQueueManager
from ui.suggestion_renderer import SuggestionRenderer

class SuggestionViewerProvider(Provider):
    suggestion_renderer = provide(SuggestionRenderer, scope=Scope.APP)
    suggestion_queue = provide(SuggestionQueueManager, scope=Scope.REQUEST)

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
        
        viewer_data = SuggestionViewerData.model_validate(raw_viewer_data)
        return viewer_data