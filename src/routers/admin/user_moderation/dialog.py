from aiogram import F
from aiogram_dialog import Dialog, ShowMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Column, Select, Start, SwitchTo
from aiogram_dialog.widgets.text import Format

from database.enums import UserRole
from routers.shared_getters import get_error_text
from ui.state_groups import AdminMenuSG, ModerationMenuSG
from ui.widgets.i18n_text import I18nText

from .getters import get_selected_user, get_userbot_user_profiles
from .handlers import message_to_user, on_user_selected, select_user, user_change_role

user_select_window = Window(
    I18nText("wait_user_id_text"),
    Format("{error}", when="error"),
    MessageInput(select_user),
    Column(
        Select(
            Format("{item.user_id}"),
            id="user_profile_select",
            on_click=on_user_selected,
            item_id_getter=lambda item: item.user_id,
            items="profiles",
        ),
    ),
    Start(
        I18nText("back_admin_menu_btn"),
        id="admin_menu",
        state=AdminMenuSG.main,
        show_mode=ShowMode.AUTO,
    ),
    state=ModerationMenuSG.user_select,
    getter=[get_error_text, get_userbot_user_profiles],
)

user_moderation_window = Window(
    I18nText("admin_moderation_user_profile", when=F["target_profile_i18n"]),
    Format("{target_dto.name}", when=~F["target_profile_i18n"]),
    SwitchTo(
        I18nText("message_user_btn"),
        id="message_user",
        state=ModerationMenuSG.user_message,
    ),
    Button(
        I18nText("demote_user_btn"),
        id="change_to_user",
        on_click=user_change_role,
        when=F["target_profile"].role == UserRole.ADMIN,
    ),
    Button(
        I18nText("promote_admin_btn"),
        id="promote_admin",
        on_click=user_change_role,
        when=F["target_profile"].role == UserRole.USER,
    ),
    Button(
        I18nText("ban_user_btn"),
        id="ban",
        on_click=user_change_role,
        when=F["target_profile"].role != UserRole.BANNED,
    ),
    Button(
        I18nText("unban_user_btn"),
        id="change_to_user",
        on_click=user_change_role,
        when=F["target_profile"].role == UserRole.BANNED,
    ),
    Start(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main),
    state=ModerationMenuSG.user_moderation,
    getter=get_selected_user,
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
