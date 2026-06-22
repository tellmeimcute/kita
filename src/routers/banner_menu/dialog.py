from aiogram_dialog import Window, Dialog, ShowMode
from aiogram_dialog.widgets.kbd import Start
from aiogram_dialog.widgets.input import MessageInput

from ui.widgets.i18n_text import I18nText
from ui.state_groups import AdminMenuSG, BannerMenuSG

from .handlers import get_banner_text

get_banner_text_window = Window(
    I18nText("banner_wait_for_text"),
    MessageInput(get_banner_text),
    Start(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main, show_mode=ShowMode.AUTO),
    state=BannerMenuSG.prepare_banner,
)

get_banner_text_again_window = Window(
    I18nText("banner_wait_for_text_again"),
    MessageInput(get_banner_text),
    Start(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main, show_mode=ShowMode.AUTO),
    state=BannerMenuSG.something_wrong,
)

dialog = Dialog(
    get_banner_text_window,
    get_banner_text_again_window,
)