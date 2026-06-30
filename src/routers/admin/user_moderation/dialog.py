

from aiogram_dialog import Window, Dialog, ShowMode
from aiogram_dialog.widgets.text import Format
from aiogram_dialog.widgets.kbd import SwitchTo, Button, Start
from aiogram_dialog.widgets.input import MessageInput

from database.enums import UserRole
from ui.widgets.i18n_text import I18nText
from ui.state_groups import AdminMenuSG, ModerationMenuSG

from routers.shared_getters import role_condition

from .handlers import select_user, user_change_role, message_to_user
from .getters import user_select_getter


user_select_window = Window(
    Format("{user_select_text}"),
    MessageInput(select_user),
    Start(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main, show_mode=ShowMode.AUTO),
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
        when=role_condition(UserRole.ADMIN, user_key="target_dto",),
    ),
    Button(
        I18nText("promote_admin_btn"),
        id="promote_admin",
        on_click=user_change_role,
        when=role_condition(UserRole.USER, user_key="target_dto"),
    ),
    Button(
        I18nText("ban_user_btn"),
        id="ban",
        on_click=user_change_role,
        when=role_condition(UserRole.BANNED, user_key="target_dto", mode="not"),
    ),
    Button(
        I18nText("unban_user_btn"),
        id="change_to_user",
        on_click=user_change_role,
        when=role_condition(UserRole.BANNED, user_key="target_dto"),
    ),
    Start(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main),
    state=ModerationMenuSG.user_moderation,
)

user_message_window = Window(
    I18nText("wait_message_text"),
    MessageInput(message_to_user),
    Start(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main, show_mode=ShowMode.AUTO),
    state=ModerationMenuSG.user_message,
)

dialog = Dialog(
    user_select_window,
    user_moderation_window,
    user_message_window,
)
