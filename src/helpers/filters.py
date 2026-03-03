

from aiogram.filters import Filter
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _
from pydantic import BaseModel

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
    

class TextArgsFilter(Filter):
    def __init__(self, i18n_key: str, schema: type[BaseModel], **return_data):
        self.i18n_key = i18n_key
        self.schema = schema
        self.return_data = return_data

    async def __call__(self, message: Message) -> bool | dict[str, str]:
        if not message.text:
            return False
        
        try:
            expected = _(self.i18n_key).strip().lower()
            raw_text = message.text.lower().strip()
            
            args = raw_text[len(expected):].strip().split()
            command_text = raw_text[:len(expected)]
        except:
            return False

        if command_text != expected:
            return False

        try:
            field_names = self.schema.model_fields.keys()
            data = dict(zip(field_names, args))
            cmd_data = self.schema(**data)
        except:
            return False
        
        self.return_data.update({"command": cmd_data})
        return self.return_data