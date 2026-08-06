from aiogram_dialog import Dialog, LaunchMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Start
from aiogram_dialog.widgets.text import Format

from routers.shared_getters import get_error_text
from ui.state_groups import RegistrarMenuSG, UserBotRegisterSG
from ui.widgets.i18n_text import I18nText

from .handlers import bot_token_handler, channel_id_handler

get_bot_token_window = Window(
    I18nText("reg_bot_wait_for_token"),
    Format("{error}", when="error"),
    MessageInput(bot_token_handler),
    Start(
        I18nText("menu_btn"),
        id="main_menu",
        state=RegistrarMenuSG.menu,
    ),
    state=UserBotRegisterSG.wait_token,
    getter=get_error_text,
)

get_channel_id_window = Window(
    I18nText("reg_bot_wait_for_channel_id"),
    Format("{error}", when="error"),
    MessageInput(channel_id_handler),
    Start(
        I18nText("menu_btn"),
        id="main_menu",
        state=RegistrarMenuSG.menu,
    ),
    state=UserBotRegisterSG.wait_channel_id,
    getter=get_error_text,
)

dialog = Dialog(
    get_bot_token_window,
    get_channel_id_window,
    launch_mode=LaunchMode.ROOT,
)
