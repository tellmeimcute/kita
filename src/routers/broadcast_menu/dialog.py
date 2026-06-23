

from aiogram_dialog import Window, Dialog, ShowMode
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.kbd import Row, Button, Start
from aiogram_dialog.widgets.input import MessageInput

from ui.widgets.i18n_text import I18nText
from ui.state_groups import AdminMenuSG, BroadcastMenuSG

from .getters import get_broadcast_info
from .handlers import prepare_broadcast, execute_broadcast

wait_broadcast_window = Window(
    I18nText("broadcast_wait_message_text"),
    MessageInput(prepare_broadcast),
    Start(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main, show_mode=ShowMode.AUTO),
    state=BroadcastMenuSG.wait_broadcast_content,
)

confirm_broadcast = Window(
    I18nText("mass_message_confirm"),
    Row(
        Start(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main, show_mode=ShowMode.AUTO, style=Style("danger")),
        Button(I18nText("confirm"), id="confirm", on_click=execute_broadcast, style=Style("success")),
    ),
    state=BroadcastMenuSG.broadcast_confirm,
    getter=get_broadcast_info,
)

dialog = Dialog(
    wait_broadcast_window,
    confirm_broadcast,
)
