from aiogram_dialog import Dialog, ShowMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Start, SwitchTo
from aiogram_dialog.widgets.text import Format

from database.enums import UserRole
from routers.shared_getters import role_condition
from ui.state_groups import AdminMenuSG, ModerationMenuSG
from ui.widgets.i18n_text import I18nText

from .getters import user_select_getter
from .handlers import message_to_user, select_user, user_change_role

user_select_window = Window(
    Format("{user_select_text}"),
    MessageInput(select_user),
    Start(
        I18nText("back_admin_menu_btn"),
        id="admin_menu",
        state=AdminMenuSG.main,
        show_mode=ShowMode.AUTO,
    ),
    state=ModerationMenuSG.user_select,
    getter=user_select_getter,
)

user_moderation_window = Window(
    I18nText("admin_moderation_user_profile"),
    SwitchTo(
        I18nText("message_user_btn"),
        id="message_user",
        state=ModerationMenuSG.user_message,
    ),
    Button(
        I18nText("demote_user_btn"),
        id="change_to_user",
        on_click=user_change_role,
        when=role_condition(
            UserRole.ADMIN,
            user_key="target_profile",
        ),
    ),
    Button(
        I18nText("promote_admin_btn"),
        id="promote_admin",
        on_click=user_change_role,
        when=role_condition(UserRole.USER, user_key="target_profile"),
    ),
    Button(
        I18nText("ban_user_btn"),
        id="ban",
        on_click=user_change_role,
        when=role_condition(UserRole.BANNED, user_key="target_profile", mode="not"),
    ),
    Button(
        I18nText("unban_user_btn"),
        id="change_to_user",
        on_click=user_change_role,
        when=role_condition(UserRole.BANNED, user_key="target_profile"),
    ),
    Start(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main),
    state=ModerationMenuSG.user_moderation,
)

user_message_window = Window(
    I18nText("wait_message_text"),
    MessageInput(message_to_user),
    Start(
        I18nText("back_admin_menu_btn"),
        id="admin_menu",
        state=AdminMenuSG.main,
        show_mode=ShowMode.AUTO,
    ),
    state=ModerationMenuSG.user_message,
)

dialog = Dialog(
    user_select_window,
    user_moderation_window,
    user_message_window,
)
