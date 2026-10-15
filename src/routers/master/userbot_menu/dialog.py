from aiogram import F
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, Select, Start, SwitchTo
from aiogram_dialog.widgets.text import Format

from routers.shared_getters import get_error_text
from ui.state_groups import RegistrarMenuSG, UserBotSelectSG
from ui.widgets.i18n_text import I18nFormat, I18nText

from .getters import get_selected_userbot, owned_userbots
from .handlers import (
    on_bot_selected,
    userbot_active_toggle,
    userbot_demote_admins,
    userbot_update_channel,
    userbot_update_token,
)


def has_userbots(data: dict, widget, manager: DialogManager) -> bool:
    return bool(data.get("userbots"))


def no_userbots(data: dict, widget, manager: DialogManager) -> bool:
    return not data.get("userbots")


userbot_main_window = Window(
    I18nText("userbots_moderation_select"),
    I18nText("userbots_empty_state", when=no_userbots),
    Select(
        Format("{item.label}"),
        id="userbot_select_group",
        on_click=on_bot_selected,
        item_id_getter=lambda item: item.bot_id,
        items="userbots",
        when=has_userbots,
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
    I18nFormat("userbot_window_description"),
    Button(
        I18nText("userbot_set_inactive_btn"),
        id="userbot_set_inactive",
        on_click=userbot_active_toggle,
        when=F["selected_userbot"].active,
    ),
    Button(
        I18nText("userbot_set_active_btn"),
        id="userbot_set_active",
        on_click=userbot_active_toggle,
        when=F["selected_userbot"].active.is_(False),
    ),
    Row(
        SwitchTo(
            I18nText("userbot_update_token_btn"),
            id="userbot_update_token",
            state=UserBotSelectSG.update_token,
        ),
        SwitchTo(
            I18nText("userbot_update_channel_btn"),
            id="userbot_update_channel",
            state=UserBotSelectSG.update_channel,
        ),
    ),
    SwitchTo(
        I18nText("userbot_demote_all_admins_btn"),
        id="userbot_demote_all_admins",
        state=UserBotSelectSG.confirm_demote,
    ),
    Start(
        I18nText("menu_btn"),
        id="main_menu",
        state=RegistrarMenuSG.menu,
    ),
    state=UserBotSelectSG.moderation,
    getter=[get_selected_userbot, get_error_text],
)

confirm_demote_window = Window(
    I18nFormat("userbot_demote_confirm"),
    Row(
        SwitchTo(
            I18nText("command_cancel"),
            id="cancel",
            state=UserBotSelectSG.moderation,
        ),
        Button(
            I18nText("confirm"),
            id="confirm_demote",
            on_click=userbot_demote_admins,
        ),
    ),
    state=UserBotSelectSG.confirm_demote,
    getter=[get_selected_userbot, get_error_text],
)

update_token_window = Window(
    I18nText("userbot_update_token"),
    Format("{error}", when="error"),
    MessageInput(userbot_update_token),
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
    MessageInput(userbot_update_channel),
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
    confirm_demote_window,
    update_token_window,
    update_channel_window,
    name="userbot_menu_dialog",
)
