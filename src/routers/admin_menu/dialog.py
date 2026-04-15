
from aiogram_dialog import Window, Dialog, StartMode, ShowMode
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.kbd import SwitchTo, Row, Button, Start
from aiogram_dialog.widgets.input import MessageInput

from database.roles import UserRole
from ui.widgets.i18n_text import I18nText
from ui.state_groups import AdminMenuSG, UserMenuSG

from routers.shared_getters import role_condition
from .getters import get_app_stats, get_broadcast_info
from .handlers import (
    select_user,
    user_change_role,
    post_banner,
    prepare_broadcast,
    execute_broadcast,
    enter_suggestion_viewer,
)

main_window = Window(
    I18nText("admin_menu_text"),
    Button(I18nText("enter_viewer_btn"), id="suggestion_viewer", on_click=enter_suggestion_viewer),
    SwitchTo(I18nText("broadcast_btn"), id="broadcast", state=AdminMenuSG.wait_broadcast_content),
    SwitchTo(I18nText("user_moderation_btn"), id="user_select", state=AdminMenuSG.user_select),
    Row(
        SwitchTo(I18nText("app_stats_btn"), id="app_stats", state=AdminMenuSG.app_stats),
        Button(I18nText("post_banner_btn"), id="post_banner", on_click=post_banner),
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
    I18nText("state_wait_for_id"),
    MessageInput(select_user),
    SwitchTo(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main, show_mode=ShowMode.AUTO),
    state=AdminMenuSG.user_select,
)

user_moderation_window = Window(
    I18nText("admin_moderation_user_profile"),
    I18nText("choose_moderation_option"),
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

wait_broadcast_window = Window(
    I18nText("mass_message_wait_for_text"),
    MessageInput(prepare_broadcast),
    SwitchTo(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main),
    state=AdminMenuSG.wait_broadcast_content,
)

confirm_broadcast = Window(
    I18nText("mass_message_confirm"),
    Row(
        SwitchTo(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main, style=Style("danger")),
        Button(I18nText("confirm"), id="confirm", on_click=execute_broadcast, style=Style("success")),
    ),
    state=AdminMenuSG.broadcast_confirm,
    getter=get_broadcast_info,
)

dialog = Dialog(
    main_window,
    user_select_window,
    user_moderation_window,
    bot_stats_window,
    wait_broadcast_window,
    confirm_broadcast,
)