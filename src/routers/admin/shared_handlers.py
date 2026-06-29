
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.i18n_translator import Translator
from core.schemas import SuggestionViewerData
from database.dto import UserDTO
from interfaces import UnitOfWorkProtocol, SuggestionServiceProtocol
from ui.state_groups import SuggestionViewerSG
from ui.suggestion_renderer import SuggestionRenderer


@inject
async def enter_suggestion_viewer(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    suggestion_service: FromDishka[SuggestionServiceProtocol],
    viewer_data: FromDishka[SuggestionViewerData],
    renderer: FromDishka[SuggestionRenderer],
    translator: FromDishka[Translator],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    state: FSMContext = manager.middleware_data.get("state")

    async with uow.transaction():
        new_suggestions: list | None = await suggestion_service.get_active()

    if not new_suggestions:
        warning = translator.translate("suggestion_no_active")
        return await callback.answer(warning)
    
    cur_suggestion = new_suggestions.pop(0)

    viewer_data.suggestion_dtos = new_suggestions
    viewer_data.suggestion_dto = cur_suggestion

    await manager.reset_stack()
    await state.set_state(SuggestionViewerSG.in_viewer)
    await state.set_data({"viewer_data": viewer_data.model_dump(mode="json")})
    await renderer.suggestion(user_dto, cur_suggestion)
