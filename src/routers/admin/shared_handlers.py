
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.i18n_translator import Translator
from database.dto import UserDTO
from services.suggestion_queue import SuggestionQueueManager
from ui.state_groups import SuggestionViewerSG
from ui.suggestion_renderer import SuggestionRenderer


@inject
async def enter_suggestion_viewer(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    queue_manager: FromDishka[SuggestionQueueManager],
    renderer: FromDishka[SuggestionRenderer],
    translator: FromDishka[Translator],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    state: FSMContext = manager.middleware_data.get("state")

    new_suggestion = await queue_manager.pop_next(dump_into_state=False)
    if not new_suggestion:
        text = translator.get_translated_text("suggestion_no_active")
        return await callback.answer(text)

    await manager.reset_stack()

    await state.set_state(SuggestionViewerSG.in_viewer)
    await queue_manager.dump_into_state()
    await renderer.start_review(user_dto)
    await renderer.suggestion(user_dto, new_suggestion)