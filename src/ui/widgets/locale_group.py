

from itertools import chain
from typing import Any

from dishka import AsyncContainer

from aiogram.types import CallbackQuery
from aiogram.utils.i18n import I18n
from aiogram_dialog import DialogManager, DialogProtocol
from aiogram_dialog.api.internal import RawKeyboard
from aiogram_dialog.widgets.kbd import Button, Group, Keyboard
from aiogram_dialog.widgets.common import WhenCondition

from core.consts import DISHKA_CONTAINER_KEY
from ui.widgets.i18n_text import I18nText

class LocaleGroup(Group):
    def __init__(
        self,
        id: str | None = None,
        on_click: Any | None = None,
        width: int | None = None,
        when: WhenCondition = None,
    ):
        super().__init__(id=id, when=when)
        self.width = width
        self.on_click = on_click

    async def get_buttons(self, manager: DialogManager) -> tuple[Keyboard]:
        container: AsyncContainer = manager.middleware_data[DISHKA_CONTAINER_KEY]
        i18n: I18n = await container.get(I18n)

        locale_btns = (
            Button(I18nText(f"locale_{locale}_string"), id=locale, on_click=self.on_click)
            for locale in i18n.available_locales
        )

        return locale_btns

    async def _render_keyboard(
        self,
        data: dict,
        manager: DialogManager,
    ) -> RawKeyboard:
        kbd: RawKeyboard = []
        buttons = await self.get_buttons(manager)

        for b in buttons:
            b_kbd = await b.render_keyboard(data, manager)
            if self.width is None:
                kbd += b_kbd
            else:
                if not kbd:
                    kbd.append([])
                kbd[0].extend(chain.from_iterable(b_kbd))
        if self.width and kbd:
            kbd = self._wrap_kbd(kbd[0])
        return kbd

    async def _process_other_callback(
        self,
        callback: CallbackQuery,
        dialog: DialogProtocol,
        manager: DialogManager,
    ) -> bool:
        buttons = await self.get_buttons(manager)

        for b in buttons:
            if await b.process_callback(callback, dialog, manager):
                return True
        return False