from aiogram import F
from aiogram_dialog import Dialog, LaunchMode, StartMode, Window
from aiogram_dialog.widgets.kbd import Button, Start, SwitchTo
from aiogram_dialog.widgets.style import Style

from database.enums import UserRole
from routers.admin.suggestions import enter_viewer_callback
from ui.state_groups import AdminMenuSG, SuggestionSG, UserMenuSG
from ui.widgets.i18n_text import I18nText
from ui.widgets.locale_group import LocaleGroup
from ui.widgets.protected_start import ProtectedStart

from .getters import get_menu_i18n_kwargs
from .handlers import (
    on_language_selected,
    prefer_anon_toggle,
)

WHEN_ADMIN = F["middleware_data"]["profile_dto"].role == UserRole.ADMIN

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
        on_click=enter_viewer_callback,
        style=Style("primary"),
        when=WHEN_ADMIN,
    ),
    ProtectedStart(
        I18nText("admin_menu_btn"),
        id="admin_menu",
        mode=StartMode.RESET_STACK,
        when=WHEN_ADMIN,
        state=AdminMenuSG.main,
    ),
    SwitchTo(
        I18nText("settings_menu_btn"),
        id="settings",
        state=UserMenuSG.settings,
    ),
    getter=get_menu_i18n_kwargs,
    state=UserMenuSG.main,
)

settings_window = Window(
    I18nText("settings_menu_text"),
    SwitchTo(
        I18nText("locale_settings_btn"),
        id="locale",
        state=UserMenuSG.language,
    ),
    Button(
        I18nText("prefer_anon_toggle_btn"),
        id="prefer_anon_toggle",
        on_click=prefer_anon_toggle,
    ),
    SwitchTo(
        I18nText("menu_btn"),
        id="menu",
        state=UserMenuSG.main,
    ),
    state=UserMenuSG.settings,
)

language_window = Window(
    I18nText("locale_menu_text"),
    LocaleGroup(
        width=3,
        on_click=on_language_selected,
    ),
    SwitchTo(
        I18nText("settings_menu_btn"),
        id="settings",
        state=UserMenuSG.settings,
    ),
    state=UserMenuSG.language,
)

dialog = Dialog(
    main_window,
    settings_window,
    language_window,
    launch_mode=LaunchMode.ROOT,
)
