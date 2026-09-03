from aiogram import F
from aiogram_dialog import Dialog, ShowMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, Start
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.text import Format

from routers.shared_getters import get_error_text
from ui.state_groups import AdminMenuSG, BannerMenuSG
from ui.widgets.i18n_text import I18nFormat, I18nText

from .handlers import execute_banner, get_banner_text

prepare_banner_window = Window(
    I18nFormat("banner_wait_for_text", when=~F["error"]),
    Format("{error}", when="error"),
    MessageInput(get_banner_text),
    Start(
        I18nText("back_admin_menu_btn"),
        id="admin_menu",
        state=AdminMenuSG.main,
        show_mode=ShowMode.AUTO,
    ),
    state=BannerMenuSG.prepare_banner,
    getter=get_error_text,
)

confirm_banner_window = Window(
    I18nText("banner_confirm"),
    Row(
        Start(
            I18nText("back_admin_menu_btn"),
            id="admin_menu",
            state=AdminMenuSG.main,
            show_mode=ShowMode.AUTO,
        ),
        Button(
            I18nText("confirm"),
            id="confirm",
            on_click=execute_banner,
            style=Style("success"),
        ),
    ),
    state=BannerMenuSG.confirm_banner,
)

dialog = Dialog(prepare_banner_window, confirm_banner_window)
