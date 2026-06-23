
from aiogram_dialog import Window, Dialog, StartMode, ShowMode
from aiogram_dialog.widgets.kbd import SwitchTo, Row, Start, Button
from aiogram_dialog.widgets.input import MessageInput

from database.enums import UserRole
from ui.widgets.i18n_text import I18nText
from ui.state_groups import AdminMenuSG, UserMenuSG, BannerMenuSG, BroadcastMenuSG

from routers.shared_getters import role_condition

from .getters import get_app_stats
from .handlers import (
    select_user,
    user_change_role,
)

main_window = Window(
    I18nText("admin_menu_text"),
    Start(I18nText("broadcast_btn"), id="broadcast", state=BroadcastMenuSG.wait_broadcast_content),
    SwitchTo(I18nText("user_moderation_btn"), id="user_select", state=AdminMenuSG.user_select),
    Row(
        SwitchTo(I18nText("app_stats_btn"), id="app_stats", state=AdminMenuSG.app_stats),
        Start(I18nText("post_banner_btn"), id="post_banner", state=BannerMenuSG.prepare_banner),
    ),
    Start(
        I18nText("menu_btn"),
        id="main_menu",
        mode=StartMode.RESET_STACK,
        state=UserMenuSG.main,
    ),
    state=AdminMenuSG.main,
)

user_select_window = Window(
    I18nText("wait_user_id_text"),
    MessageInput(select_user),
    SwitchTo(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main, show_mode=ShowMode.AUTO),
    state=AdminMenuSG.user_select,
)

user_select_again_window = Window(
    I18nText("user_not_found_wait_next_id"),
    MessageInput(select_user),
    SwitchTo(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main, show_mode=ShowMode.AUTO),
    state=AdminMenuSG.user_select_again,
)

user_moderation_window = Window(
    I18nText("admin_moderation_user_profile"),
    Button(
        I18nText("ban_btn"),
        id="ban",
        on_click=user_change_role,
        when=role_condition(UserRole.BANNED, user_key="target_dto", mode="not"),
    ),
    Button(
        I18nText("unban_btn"),
        id="change_to_user",
        on_click=user_change_role,
        when=role_condition(UserRole.BANNED, user_key="target_dto"),
    ),

    Button(
        I18nText("demote_user_btn"),
        id="change_to_user",
        on_click=user_change_role,
        when=role_condition(UserRole.ADMIN, user_key="target_dto",),
    ),
    Button(
        I18nText("promote_admin_btn"),
        id="promote_admin",
        on_click=user_change_role,
        when=role_condition(UserRole.USER, user_key="target_dto"),
    ),

    SwitchTo(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main),
    state=AdminMenuSG.user_moderation,
)

bot_stats_window = Window(
    I18nText("global_stats"),
    SwitchTo(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main),
    state=AdminMenuSG.app_stats,
    getter=get_app_stats,
)

dialog = Dialog(
    main_window,
    user_select_window,
    user_select_again_window,
    user_moderation_window,
    bot_stats_window,
)