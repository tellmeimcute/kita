from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Start, Select
from aiogram_dialog.widgets.text import Format

from ui.state_groups import UserBotSelectSG, RegistrarMenuSG
from ui.widgets.i18n_text import I18nText

from .getters import owned_userbots, get_selected_userbot
from .handlers import on_bot_selected

userbot_main_window = Window(
    I18nText("userbots_moderation_select"),
    Select(
        Format("{item.username}"),
        id="userbot_select_group",
        on_click=on_bot_selected,
        item_id_getter=lambda item: item.bot_id,
        items="userbots",
    ),
    Start(
        I18nText("menu_btn"),
        id="main_menu",
        state=RegistrarMenuSG.menu,
    ),
    state=UserBotSelectSG.select,
    getter=owned_userbots,
)

userbot_moderation_window = Window(
    Format("{selected_userbot.username}"),
    Start(
        I18nText("menu_btn"),
        id="main_menu",
        state=RegistrarMenuSG.menu,
    ),
    state=UserBotSelectSG.moderation,
    getter=get_selected_userbot,
)


dialog = Dialog(
    userbot_main_window,
    userbot_moderation_window,
)