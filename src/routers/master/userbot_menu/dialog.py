
from aiogram import F
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Start, Select, Button, SwitchTo
from aiogram_dialog.widgets.text import Format

from ui.state_groups import UserBotSelectSG, RegistrarMenuSG
from ui.widgets.i18n_text import I18nText

from .getters import owned_userbots, get_selected_userbot
from .handlers import on_bot_selected, userbot_set_toggle, update_token, update_channel

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
        I18nText("userbot_set_inactive_btn"),
        id="userbot_set_inactive",
        on_click=userbot_set_toggle,
        when=F["selected_userbot"].active
    ),
    Button(
        I18nText("userbot_set_active_btn"),
        id="userbot_set_active",
        on_click=userbot_set_toggle,
        when=~F["selected_userbot"].active
    ),
    SwitchTo(
        I18nText("userbot_update_token_btn"),
        id="userbot_update_token",
        state=UserBotSelectSG.update_token,
    ),
    SwitchTo(
        I18nText("userbot_update_channel_btn"),
        id="userbot_update_chanell",
        state=UserBotSelectSG.update_channel,
    ),
    Start(
        I18nText("menu_btn"),
        id="main_menu",
        state=RegistrarMenuSG.menu,
    ),
    state=UserBotSelectSG.moderation,
    getter=[get_selected_userbot, get_error_text],
)

update_token_window = Window(
    I18nText("userbot_update_token"),
    Format("{error}", when="error"),
    MessageInput(update_token),
    Start(
        I18nText("menu_btn"),
        id="main_menu",
        state=RegistrarMenuSG.menu,
    ),
    state=UserBotSelectSG.update_token,
    getter=get_error_text,
)

update_channel_window = Window(
    I18nText("userbot_update_channel"),
    Format("{error}", when="error"),
    MessageInput(update_channel),
    Start(
        I18nText("menu_btn"),
        id="main_menu",
        state=RegistrarMenuSG.menu,
    ),
    state=UserBotSelectSG.update_channel,
    getter=get_error_text,
)


dialog = Dialog(
    userbot_main_window,
    userbot_moderation_window,
    update_token_window,
    update_channel_window,
)