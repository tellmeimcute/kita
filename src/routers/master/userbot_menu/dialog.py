
from aiogram import F
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Start, Select, Button
from aiogram_dialog.widgets.text import Format

from ui.state_groups import UserBotSelectSG, RegistrarMenuSG
from ui.widgets.i18n_text import I18nText

from .getters import owned_userbots, get_selected_userbot
from .handlers import on_bot_selected, userbot_set_toggle

from ..getters import get_error_text

userbot_main_window = Window(
    I18nText("userbots_moderation_select"),
    Select(
        Format("{item.username}"),
        id="userbot_select_group",
        on_click=on_bot_selected,
        item_id_getter=lambda item: item.bot_id,
        items="userbots",
    ),
    Start(
        I18nText("menu_btn"),
        id="main_menu",
        state=RegistrarMenuSG.menu,
    ),
    state=UserBotSelectSG.select,
    getter=owned_userbots,
)

userbot_moderation_window = Window(
    Format("{error}", when="error"),
    Format("{selected_userbot.username}"),
    Button(
        I18nText("userbot_set_inactive"),
        id="userbot_set_inactive",
        on_click=userbot_set_toggle,
        when=F["selected_userbot"].active
    ),
    Button(
        I18nText("userbot_set_active"),
        id="userbot_set_active",
        on_click=userbot_set_toggle,
        when=~F["selected_userbot"].active
    ),
    Start(
        I18nText("menu_btn"),
        id="main_menu",
        state=RegistrarMenuSG.menu,
    ),
    state=UserBotSelectSG.moderation,
    getter=[get_selected_userbot, get_error_text],
)


dialog = Dialog(
    userbot_main_window,
    userbot_moderation_window,
)