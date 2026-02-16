

from aiogram.filters import Filter
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

class ViewerActionFilter(Filter):
    def __init__(self):
        self.mapping = {
            "viewer_accept": "accept",
            "viewer_decline": "decline",
            "viewer_accept_no_caption": "accept_no_caption",
        }

    async def __call__(
        self, 
        message: Message,
    ) -> bool | dict[str, str]:

        if not message.text:
            return False
            
        text = message.text.lower().strip()
        
        for msg_key, action_val in self.mapping.items():
            if text == _(msg_key).lower():
                return {"viewer_action": action_val}
        return False