from collections.abc import Callable, Coroutine
from typing import Any

from aiogram.filters.state import State
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import I18n
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.i18n_translator import Translator
from database.dto import UserDTO
from interfaces import UnitOfWorkProtocol, UserServiceProtocol


def language_selected(
    back_state: State,
) -> Callable[[CallbackQuery, Button, DialogManager], Coroutine[Any, Any, Any]]:
    """Build an ``on_click`` handler that persists the chosen locale and switches the
    dialog back to ``back_state``.
    """

    @inject
    async def on_language_selected(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        tl: FromDishka[Translator],
        uow: FromDishka[UnitOfWorkProtocol],
        user_service: FromDishka[UserServiceProtocol],
    ):
        user_dto: UserDTO = manager.middleware_data.get("user_dto")
        i18n: I18n = manager.middleware_data.get("i18n")

        if user_dto.language_code == button.widget_id:
            return await callback.answer(tl.translate("same_locale_warning"))

        user_dto.language_code = button.widget_id
        async with uow.transaction():
            await user_service.save(user_dto)

        i18n.ctx_locale.set(user_dto.language_code)
        await callback.answer(tl.translate("locale_changed_msg"))
        await manager.switch_to(back_state)

    return on_language_selected
