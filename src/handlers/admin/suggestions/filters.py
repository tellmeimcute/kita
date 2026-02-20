

from aiogram.filters import Filter
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from helpers.enums import ViewerAdminAction


class ViewerActionFilter(Filter):
    def __init__(self):
        self.mapping = {
            "viewer_accept": (ViewerAdminAction.ACCEPT, True),
            "viewer_accept_no_caption": (ViewerAdminAction.ACCEPT_NO_CAPTION, True),
            "viewer_decline": (ViewerAdminAction.DECLINE, False),
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
                return {
                    "viewer_action": action_val[0],
                    "verdict": action_val[1]
                }
        return False