from aiogram_dialog import Window, Dialog, LaunchMode, StartMode
from aiogram_dialog.widgets.kbd import Start
from aiogram_dialog.widgets.text import Format
from aiogram_dialog.widgets.input import MessageInput

from ui.widgets.i18n_text import I18nText
from ui.state_groups import UserBotRegisterSG, RegistrarMenuSG

from .handlers import bot_token_handler, channel_id_handler
from .getters import bot_token_window_text


menu_window = Window(
    I18nText("registrar_menu"),
    Start(
        I18nText("start_userbot_register_btn"),
        id="start_register",
        state=UserBotRegisterSG.wait_token,
    ),
    state=RegistrarMenuSG.menu,
)

get_bot_token_window = Window(
    Format("{text}"),
    MessageInput(bot_token_handler),
    Start(
        I18nText("menu_btn"),
        id="main_menu",
        mode=StartMode.RESET_STACK,
        state=RegistrarMenuSG.menu,
    ),
    state=UserBotRegisterSG.wait_token,
    getter=bot_token_window_text,
)

get_channel_id_window = Window(
    I18nText("reg_bot_wait_for_channel_id"),
    MessageInput(channel_id_handler),
    Start(
        I18nText("menu_btn"),
        id="main_menu",
        mode=StartMode.RESET_STACK,
        state=RegistrarMenuSG.menu,
    ),
    state=UserBotRegisterSG.wait_channel_id,
)

menu_dialog = Dialog(
    menu_window,
    launch_mode=LaunchMode.ROOT,
)

dialog = Dialog(
    get_bot_token_window,
    get_channel_id_window,
    launch_mode=LaunchMode.ROOT,
)