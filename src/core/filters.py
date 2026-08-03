from aiogram.filters import Filter
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _
from pydantic import BaseModel


class BaseI18nFilter(Filter):
    def __init__(self, i18n_key: str, **return_data):
        self.i18n_key = i18n_key
        self.return_data = return_data

    def _get_expected(self) -> str:
        return _(self.i18n_key).strip().lower()

    def _prepare_text(self, message: Message) -> str | None:
        if not message.text:
            return None
        return message.text.lower().strip()


class I18nTextFilter(BaseI18nFilter):
    async def __call__(self, message: Message) -> bool | dict[str, str]:
        text = self._prepare_text(message)
        if not text:
            return False

        if text == self._get_expected():
            return self.return_data or True
        return False


class TextArgsFilter(BaseI18nFilter):
    def __init__(self, i18n_key: str, schema: type[BaseModel], **return_data):
        super().__init__(i18n_key, **return_data)
        self.schema = schema

    async def __call__(self, message: Message) -> bool | dict[str, str]:
        text = self._prepare_text(message)
        if not text:
            return False

        expected = self._get_expected()
        if not text.startswith(expected):
            return False

        args = text[len(expected) :].strip().split()
        field_names = self.schema.model_fields.keys()

        if len(args) != len(field_names):
            return False

        try:
            data = dict(zip(field_names, args, strict=True))
            cmd_data = self.schema(**data)
        except Exception:
            return False

        return {**self.return_data, "command": cmd_data}
