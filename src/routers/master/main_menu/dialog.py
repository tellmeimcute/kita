from aiogram_dialog import Dialog, LaunchMode, Window
from aiogram_dialog.widgets.kbd import Button, Start, SwitchTo

from ui.state_groups import RegistrarMenuSG, UserBotSelectSG
from ui.widgets.i18n_text import I18nText
from ui.widgets.locale_group import LocaleGroup

from ..register.handlers import start_registration
from .handlers import on_language_selected

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
    SwitchTo(
        I18nText("locale_settings_btn"),
        id="locale",
        state=RegistrarMenuSG.language,
    ),
    state=RegistrarMenuSG.menu,
)


language_window = Window(
    I18nText("locale_menu_text"),
    LocaleGroup(
        width=3,
        on_click=on_language_selected,
    ),
    SwitchTo(
        I18nText("menu_btn"),
        id="menu",
        state=RegistrarMenuSG.menu,
    ),
    state=RegistrarMenuSG.language,
)


dialog = Dialog(
    menu_window,
    language_window,
    launch_mode=LaunchMode.ROOT,
)
