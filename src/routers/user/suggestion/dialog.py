

from aiogram_dialog import Window, Dialog, ShowMode
from aiogram_dialog.widgets.kbd import SwitchTo, Row, Start
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.input import MessageInput

from ui.widgets.i18n_text import I18nText
from ui.state_groups import UserMenuSG, SuggestionSG

from .handlers import on_album_received

back_or_suggest_again = Row(
    Start(I18nText("menu_btn"), id="menu", state=UserMenuSG.main, show_mode=ShowMode.AUTO, style=Style("danger")),
    SwitchTo(
        I18nText("make_suggestion_btn"),
        id="make_suggestion",
        state=SuggestionSG.make_suggestion,
        style=Style("primary"),
    ),
)

make_suggestion_window = Window(
    I18nText("suggestion_wait_media"),
    MessageInput(on_album_received),
    Start(I18nText("menu_btn"), id="menu", state=UserMenuSG.main, show_mode=ShowMode.AUTO),
    state=SuggestionSG.make_suggestion,
)

on_moderation_window = Window(
    I18nText("suggestion_sent_to_moderation"),
    back_or_suggest_again,
    state=SuggestionSG.on_moderation,
)

suggestion_error_window = Window(
    I18nText("suggestion_error_media"),
    back_or_suggest_again,
    state=SuggestionSG.media_error,
)

dialog = Dialog(
    make_suggestion_window,
    on_moderation_window,
    suggestion_error_window,
)
