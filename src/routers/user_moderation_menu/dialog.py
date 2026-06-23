

from aiogram_dialog import Window, Dialog, ShowMode
from aiogram_dialog.widgets.kbd import SwitchTo, Button, Start
from aiogram_dialog.widgets.input import MessageInput

from database.enums import UserRole
from ui.widgets.i18n_text import I18nText
from ui.state_groups import AdminMenuSG, ModerationMenuSG

from routers.shared_getters import role_condition

from .handlers import select_user, user_change_role

user_select_window = Window(
    I18nText("wait_user_id_text"),
    MessageInput(select_user),
    Start(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main, show_mode=ShowMode.AUTO),
    state=ModerationMenuSG.user_select,
)

user_select_again_window = Window(
    I18nText("user_not_found_wait_next_id"),
    MessageInput(select_user),
    Start(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main, show_mode=ShowMode.AUTO),
    state=ModerationMenuSG.user_select_again,
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

    Start(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main),
    state=ModerationMenuSG.user_moderation,
)

dialog = Dialog(
    user_select_window,
    user_select_again_window,
    user_moderation_window,
)
