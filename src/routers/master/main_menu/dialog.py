from aiogram_dialog import Dialog, LaunchMode, Window
from aiogram_dialog.widgets.kbd import Button, Start

from ui.state_groups import RegistrarMenuSG, UserBotSelectSG
from ui.widgets.i18n_text import I18nText

from ..register.handlers import start_registration

menu_window = Window(
    I18nText("registrar_menu"),
    Button(
        I18nText("start_userbot_register_btn"),
        id="start_register",
        on_click=start_registration,
    ),
    Start(
        I18nText("my_userbots_selection_btn"),
        id="userbots_select",
        state=UserBotSelectSG.select,
    ),
    state=RegistrarMenuSG.menu,
)


dialog = Dialog(
    menu_window,
    launch_mode=LaunchMode.ROOT,
)
