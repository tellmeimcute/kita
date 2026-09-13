from aiogram import F
from aiogram_dialog import Dialog, ShowMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Start
from aiogram_dialog.widgets.text import Format

from routers.shared_getters import get_additional_text, get_error_text
from ui.state_groups import SuggestionSG, UserMenuSG
from ui.widgets.i18n_text import I18nText

from .handlers import on_album_received

make_suggestion_window = Window(
    Format("{additional_text}\n", when="additional_text"),
    I18nText("suggestion_wait_media", when=~F["error"]),
    Format("{error}", when="error"),
    MessageInput(on_album_received),
    Start(I18nText("menu_btn"), id="menu", state=UserMenuSG.main, show_mode=ShowMode.AUTO),
    state=SuggestionSG.make_suggestion,
    getter=[get_error_text, get_additional_text],
)


dialog = Dialog(make_suggestion_window)
