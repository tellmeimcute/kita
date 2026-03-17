from .admin_general import router as admin_general_router
from .ban_user import router as admin_ban_user_handler
from .suggestions import router as admin_suggestion_router
from .mass_message import router as admin_mass_message_router


__all__ = (
    "admin_suggestion_router",
    "admin_general_router",
    "admin_ban_user_handler",
    "admin_mass_message_router",
)
