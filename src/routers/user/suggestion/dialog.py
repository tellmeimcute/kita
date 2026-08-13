from aiogram import F
from aiogram_dialog import Dialog, ShowMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Row, Start, SwitchTo
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.text import Format

from routers.shared_getters import get_error_text
from ui.state_groups import SuggestionSG, UserMenuSG
from ui.widgets.i18n_text import I18nText

from .handlers import on_album_received

make_suggestion_window = Window(
    I18nText("suggestion_wait_media", when=~F["error"]),
    Format("{error}", when="error"),
    MessageInput(on_album_received),
    Start(I18nText("menu_btn"), id="menu", state=UserMenuSG.main, show_mode=ShowMode.AUTO),
    state=SuggestionSG.make_suggestion,
    getter=get_error_text,
)


on_moderation_window = Window(
    I18nText("suggestion_sent_to_moderation"),
    Row(
        Start(
            I18nText("menu_btn"),
            id="menu",
            state=UserMenuSG.main,
            show_mode=ShowMode.AUTO,
            style=Style("danger"),
        ),
        SwitchTo(
            I18nText("make_suggestion_btn"),
            id="make_suggestion",
            state=SuggestionSG.make_suggestion,
            style=Style("primary"),
        ),
    ),
    state=SuggestionSG.on_moderation,
)


dialog = Dialog(
    make_suggestion_window,
    on_moderation_window,
)
