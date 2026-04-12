

from aiogram.types import Message
from aiogram.utils.i18n import I18n
from aiogram.utils.i18n import gettext as _

from database.dto import UserDTO
from helpers.suggestion_utils import SuggestionUtils
from helpers.schemas.message_payload import MessagePayload
from services import NotifierService

from .settings_keyboards import SettingsKeyboards

class SettingsMenuRenderer:

    def __init__(
        self,
        notifier: NotifierService,
        suggestion_utils: SuggestionUtils,
    ):
        self.notifier = notifier
        self.utils = suggestion_utils

    async def new_settings_menu(self, user_dto: UserDTO):
        options_list = SettingsKeyboards.options_list()

        payload = MessagePayload(i18n_key="settings_menu", reply_markup=options_list)
        await self.notifier.notify_user(user_dto, payload)

    async def settings_menu(self, message: Message):
        options_list = SettingsKeyboards.options_list()
        await self.notifier.edit_message_text(message, text=_("settings_menu"), reply_markup=options_list)

    async def locale_menu(self, i18n: I18n, message: Message):
        locale_list = SettingsKeyboards.locale_list(i18n)
    
        #payload = MessagePayload(i18n_key="locale_menu", reply_markup=locale_list)
        await self.notifier.edit_message_text(message, text=_("locale_menu"), reply_markup=locale_list)