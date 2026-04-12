from .start import router as user_start_router
from .suggestions import router as user_suggestion_router
from .settings_menu import router as user_locale_rouer

__all__ = (
    "user_start_router",
    "user_suggestion_router",
    "user_locale_rouer",
)
