

from dishka import AsyncContainer

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.text import Text
from aiogram_dialog.widgets.common import WhenCondition

from core.i18n_translator import Translator
from core.consts import DISHKA_CONTAINER_KEY
from core.config import RuntimeConfig

from database.dto import UserDTO

class I18nText(Text):
    def __init__(self, i18n_key: str, when: WhenCondition = None):
        super().__init__(when=when)
        self.i18n_key = i18n_key

    async def _render_text(self, data: dict, manager: DialogManager) -> str:
        container: AsyncContainer = manager.middleware_data[DISHKA_CONTAINER_KEY]
        translator: Translator = await container.get(Translator)
        runtime_config: RuntimeConfig = await container.get(RuntimeConfig)

        user_dto: UserDTO = manager.middleware_data.get("user_dto")

        additional_data = data.copy()
        additional_data.pop("middleware_data")
        additional_data.pop("start_data")
        additional_data.pop("event")

        dialog_data = additional_data.pop("dialog_data")
        i18n_kwargs = {"user_dto": user_dto.model_dump()}
        i18n_kwargs.update(**dialog_data)
        i18n_kwargs.update(runtime_config.model_dump())
        i18n_kwargs.update(additional_data)
        
        text = translator.get_i18n_text(i18n_key=self.i18n_key, i18n_kwargs=i18n_kwargs)
        return text
    
