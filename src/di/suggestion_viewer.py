
from sqlalchemy.ext.asyncio import AsyncSession

from dishka import Provider, Scope, provide
from dishka.integrations.aiogram import AiogramMiddlewareData

from aiogram.fsm.context import FSMContext

from services.suggestion import SuggestionService
from services.suggestion_moderation import SuggestionModerationService

from helpers.schemas import SuggestionViewerData
from helpers.suggestion_queue import SuggestionQueueManager

from ui.suggestion_renderer import SuggestionRenderer


class SuggestionViewerProvider(Provider):
    suggestion_moderation = provide(SuggestionModerationService, scope=Scope.APP)
    suggestion_renderer = provide(SuggestionRenderer, scope=Scope.APP)

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
    
    @provide(scope=Scope.REQUEST)
    async def suggestion_queue(
        self,
        session: AsyncSession,
        suggestion_service: SuggestionService,
        state: FSMContext,
        viewer_data: SuggestionViewerData,
    ) -> SuggestionQueueManager:
        return SuggestionQueueManager(
            session=session,
            suggestion_service=suggestion_service,
            state=state,
            data=viewer_data,
        )
