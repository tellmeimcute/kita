

from dishka import AsyncContainer

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.text import Text
from aiogram_dialog.widgets.common import WhenCondition


from core.i18n_translator import Translator
from core.consts import DISHKA_CONTAINER_KEY

class I18nText(Text):
    def __init__(self, i18n_key: str, when: WhenCondition = None):
        super().__init__(when=when)
        self.i18n_key = i18n_key

    async def _render_text(self, data: dict, manager: DialogManager) -> str:
        container: AsyncContainer = manager.middleware_data[DISHKA_CONTAINER_KEY]
        translator: Translator = await container.get(Translator)

        dialog_data: dict = data.get("dialog_data")

        i18n_kwargs = data.copy()
        i18n_kwargs.update(dialog_data)

        text = translator.get_i18n_text(i18n_key=self.i18n_key, i18n_kwargs=i18n_kwargs)
        return text
    
