from .dialog import dialog as userbot_registrar_dialog
from .dialog import menu_dialog as userbot_registrar_menu_dialog
from .handlers import router as userbot_registrar_router
from .userbot_menu import userbot_menu_dialog as userbot_menu_dialog

__all__ = [
    "userbot_registrar_dialog",
    "userbot_registrar_menu_dialog",
    "userbot_registrar_router",
    "userbot_menu_dialog",
]
