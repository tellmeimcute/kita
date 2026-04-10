
from typing import Callable
from sqlalchemy.ext.asyncio import AsyncSession

from dishka import Provider, Scope, provide
from aiogram.fsm.context import FSMContext

from services.suggestion import SuggestionService
from services.notifier import NotifierService
from helpers.suggestion_utils import SuggestionUtils
from helpers.schemas import SuggestionViewerData
from helpers.suggestion_viewer import SuggestionViewer
from config import Config, RuntimeConfig

type viewer_factory_t = Callable[[SuggestionViewerData], SuggestionViewer]

class SuggestionViewerProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def viewer_data(self, fsm: FSMContext) -> SuggestionViewerData:
        data = await fsm.get_data()
        raw_viewer_data = data.get("viewer_data")
        if not raw_viewer_data:
            raise ValueError("No raw viewer data in state")
        
        viewer_data = SuggestionViewerData.model_validate(raw_viewer_data)
        return viewer_data
    
    @provide(scope=Scope.REQUEST)
    def viewer_factory(
        self,
        session: AsyncSession,
        suggestion_service: SuggestionService,
        notifier: NotifierService,
        config: Config,
        runtime_config: RuntimeConfig,
        suggestion_utils: SuggestionUtils,
    ) -> viewer_factory_t:
        def _factory(data: SuggestionViewerData) -> SuggestionViewer:
            return SuggestionViewer(
                data,
                session,
                suggestion_service,
                notifier,
                config,
                runtime_config,
                suggestion_utils,
            )
        return _factory

    suggestion_viewer = provide(SuggestionViewer, scope=Scope.REQUEST)