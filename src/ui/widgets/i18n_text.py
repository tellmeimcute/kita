from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import WhenCondition
from aiogram_dialog.widgets.text import Text
from dishka import AsyncContainer
from pydantic import BaseModel

from core.consts import DISHKA_CONTAINER_KEY
from core.i18n_translator import Translator
from database.dto import UserBotDTO, UserDTO, UserProfileDTO


def _normalize(v):
    if isinstance(v, BaseModel):
        to_i18n = getattr(v, "to_i18n_kwargs", None)
        return to_i18n() if callable(to_i18n) else v.model_dump(mode="json")
    return v


class Proxy:
    def __init__(self, value):
        self._v = value

    def _resolve(self, key):
        v = _normalize(self._v)
        return Proxy(v[key])

    def __getitem__(self, key):
        return self._resolve(key)

    def __getattr__(self, key):
        if key.startswith("_"):
            raise AttributeError(key)
        return self._resolve(key)

    def __format__(self, spec):
        return format(_normalize(self._v), spec)


class DataProxy(dict):
    def __getitem__(self, key):
        return Proxy(super().__getitem__(key))


class I18nText(Text):
    def __init__(self, i18n_key: str, when: WhenCondition = None):
        super().__init__(when=when)
        self.i18n_key = i18n_key

    async def _render_text(self, data: dict, manager: DialogManager) -> str:
        container: AsyncContainer = manager.middleware_data[DISHKA_CONTAINER_KEY]
        userbot_dto: UserBotDTO = manager.middleware_data.get("userbot_dto")
        user_dto: UserDTO = manager.middleware_data.get("user_dto")
        profile_dto: UserProfileDTO = manager.middleware_data.get("profile_dto")

        translator: Translator = await container.get(Translator)

        additional_data = data.copy()
        dialog_data = additional_data.pop("dialog_data")

        i18n_kwargs = {
            "user_dto": user_dto,
            "profile_dto": profile_dto,
        }

        i18n_kwargs.update(**dialog_data)
        i18n_kwargs.update(additional_data)
        if userbot_dto:
            i18n_kwargs.update(userbot_dto.to_i18n_kwargs())

        text = translator.translate(self.i18n_key)
        return text.format_map(DataProxy(i18n_kwargs))


class I18nFormat(Text):
    def __init__(self, i18n_key: str, when: WhenCondition = None):
        super().__init__(when=when)
        self.i18n_key = i18n_key

    async def _render_text(
        self,
        data: dict,
        manager: DialogManager,
    ) -> str:
        container: AsyncContainer = manager.middleware_data[DISHKA_CONTAINER_KEY]
        tl: Translator = await container.get(Translator)
        text = tl.translate(self.i18n_key)
        return text.format_map(DataProxy(data))
