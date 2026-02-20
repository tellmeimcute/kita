

from aiogram.filters import Filter
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

class I18nTextFilter(Filter):
    def __init__(self, i18n_key, **return_data):
        self.i18n_key = i18n_key
        self.return_data = return_data

    async def __call__(self, message: Message) -> bool | dict[str, str]:
        if not message.text:
            return False
            
        text = message.text.lower().strip()
        expected = _(self.i18n_key).strip().lower()

        if text == expected:
            return self.return_data if self.return_data else True
        return False