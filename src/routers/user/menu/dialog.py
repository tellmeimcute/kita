

from aiogram_dialog import Window, Dialog, StartMode
from aiogram_dialog.widgets.kbd import SwitchTo, Cancel, Button, Start
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.text import Format

from ui.widgets.locale_group import LocaleGroup
from ui.widgets.i18n_text import I18nText
from ui.widgets.protected_start import ProtectedStart

from ui.state_groups import UserMenuSG, AdminMenuSG, SuggestionSG

from routers.shared_getters import is_admin
from routers.admin.shared_handlers import enter_suggestion_viewer

from .getters import(
    get_runtime_config,
    get_statistic,
)

from .handlers import (
    on_language_selected,
    prefer_anon_toggle,
)

main_window = Window(
    I18nText("start_msg"),
    Start(
        I18nText("make_suggestion_btn"),
        id="make_suggestion",
        state=SuggestionSG.make_suggestion,
        style=Style("primary"),
    ),
    Button(
        I18nText("enter_viewer_btn"),
        id="suggestion_viewer",
        on_click=enter_suggestion_viewer,
        style=Style("primary"),
        when=is_admin,
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
    Button(I18nText("prefer_anon_toggle_btn"), id="prefer_anon_toggle", on_click=prefer_anon_toggle),

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

dialog = Dialog(
    main_window,
    settings_window,
    language_window,
    statistic_window,
)
