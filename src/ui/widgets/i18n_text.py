from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import WhenCondition
from aiogram_dialog.widgets.text import Text
from dishka import AsyncContainer

from core.consts import DISHKA_CONTAINER_KEY
from core.i18n_translator import Translator
from database.dto import UserBotDTO, UserDTO, UserProfileDTO


class _FormatDataStub:
    def __init__(self, name="", data=None):
        self.name = name
        self.data = data or {}

    def __getitem__(self, item):
        if item in self.data:
            return self.data[item]
        if not self.name:
            return _FormatDataStub(item)
        return _FormatDataStub(f"{self.name}[{item}]")

    def __getattr__(self, item):
        return _FormatDataStub(f"{self.name}.{item}")

    def __format__(self, format_spec):
        if format_spec:
            res = f"{self.name}:{format_spec}"
        else:
            res = self.name
        return f"{{{res}}}"


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

        additional_data.pop("middleware_data")
        additional_data.pop("start_data")
        additional_data.pop("event")

        dialog_data = additional_data.pop("dialog_data")

        i18n_kwargs = {
            "user_dto": user_dto.to_i18n_kwargs(),
            "profile_dto": profile_dto.model_dump(mode="json"),
        }

        i18n_kwargs.update(**dialog_data)
        i18n_kwargs.update(additional_data)
        if userbot_dto:
            i18n_kwargs.update(userbot_dto.model_dump(exclude={"token"}))

        return translator.i18n_text(i18n_key=self.i18n_key, i18n_kwargs=i18n_kwargs)


class I18nFormat(Text):
    def __init__(self, i18n_key: str, when: WhenCondition = None):
        super().__init__(when=when)
        self.i18n_key = i18n_key

    async def _render_text(
        self,
        data: dict,
        manager: DialogManager,
    ) -> str:
        text = Translator().translate(self.i18n_key)
        if manager.is_preview():
            return text.format_map(_FormatDataStub(data=data))
        return text.format_map(data)
