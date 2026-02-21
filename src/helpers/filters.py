

from aiogram.filters import Filter
from aiogram.types import Message
from helpers.schemas import IDCommand
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
    

class TargetIdFilter(Filter):
    def __init__(self, i18n_key):
        self.i18n_key = i18n_key

    async def __call__(self, message: Message) -> bool | dict[str, str]:
        if not message.text:
            return False
        
        try:
            text = message.text.lower().strip().split()
            command_text = text[0]
            id_command = IDCommand(target_id=text[-1])
            expected = _(self.i18n_key).strip().lower()
        except:
            return False

        return_data = {
            "target_id": id_command.target_id
        }

        if command_text == expected:
            return return_data
        
        return False