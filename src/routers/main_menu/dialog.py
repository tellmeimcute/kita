
from aiogram_dialog import Window, Dialog, StartMode
from aiogram_dialog.widgets.kbd import SwitchTo, Cancel, Row
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Format

from ui.widgets.locale_group import LocaleGroup
from ui.widgets.i18n_text import I18nText
from ui.widgets.protected_start import ProtectedStart

from ui.state_groups import UserMenuSG, AdminMenuSG

from routers.shared_getters import is_admin

from .getters import(
    get_runtime_config,
    get_statistic,
)

from .handlers import (
    on_language_selected,
    on_album_received,
)

back_or_suggest_again = Row(
    SwitchTo(I18nText("menu_btn"), id="menu", state=UserMenuSG.main, style=Style("danger")),
    SwitchTo(
        I18nText("make_suggestion_btn"),
        id="make_suggestion",
        state=UserMenuSG.make_suggestion,
        style=Style("primary"),
    ),
)

main_window = Window(
    I18nText("start_msg"),
    SwitchTo(
        I18nText("make_suggestion_btn"),
        id="make_suggestion",
        state=UserMenuSG.make_suggestion,
        style=Style("primary"),
    ),
    SwitchTo(
        I18nText("statistic_btn"),
        id="statistic",
        state=UserMenuSG.statistics,
    ),
    ProtectedStart(
        I18nText("admin_menu_btn"),
        id="admin_menu",
        mode=StartMode.RESET_STACK,
        when=is_admin,
        state=AdminMenuSG.main,
    ),
    SwitchTo(I18nText("settings_menu_btn"), id="settings", state=UserMenuSG.settings),
    Cancel(I18nText("close_btn"), when=is_admin),
    getter=get_runtime_config,
    state=UserMenuSG.main,
)

settings_window = Window(
    I18nText("settings_menu_text"),
    SwitchTo(I18nText("locale_settings_btn"), id="locale", state=UserMenuSG.language),
    SwitchTo(I18nText("menu_btn"), id="menu", state=UserMenuSG.main),
    state=UserMenuSG.settings,
)

language_window = Window(
    I18nText("locale_menu_text"),
    LocaleGroup(width=3, on_click=on_language_selected),
    SwitchTo(I18nText("settings_menu_btn"), id="settings", state=UserMenuSG.settings),
    state=UserMenuSG.language,
)

statistic_window = Window(
    Format("{stats_text}"),
    SwitchTo(I18nText("menu_btn"), id="menu", state=UserMenuSG.main),
    getter=[get_statistic],
    state=UserMenuSG.statistics,
)

make_suggestion_window = Window(
    I18nText("suggestion_wait_media"),
    MessageInput(on_album_received),
    SwitchTo(I18nText("menu_btn"), id="menu", state=UserMenuSG.main),
    state=UserMenuSG.make_suggestion,
)

on_moderation_window = Window(
    I18nText("on_moderation"),
    back_or_suggest_again,
    state=UserMenuSG.suggestion_on_moderation,
)

suggestion_error_window = Window(
    I18nText("error_media_suggestion"),
    back_or_suggest_again,
    state=UserMenuSG.suggestion_media_error,
)

dialog = Dialog(
    main_window,
    settings_window,
    language_window,
    statistic_window,
    make_suggestion_window,
    on_moderation_window,
    suggestion_error_window,
)