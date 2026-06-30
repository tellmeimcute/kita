from aiogram_dialog import Window, Dialog, ShowMode
from aiogram_dialog.widgets.text import Format
from aiogram_dialog.widgets.kbd import Start
from aiogram_dialog.widgets.input import MessageInput

from ui.widgets.i18n_text import I18nText
from ui.state_groups import AdminMenuSG, BannerMenuSG

from .handlers import get_banner_text
from .getters import banner_text_getter

get_banner_text_window = Window(
    Format("{banner_text}"),
    MessageInput(get_banner_text),
    Start(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main, show_mode=ShowMode.AUTO),
    state=BannerMenuSG.prepare_banner,
    getter=banner_text_getter,
)

dialog = Dialog(get_banner_text_window)
