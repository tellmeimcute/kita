
from aiogram import Router

from .admin.suggestions import router as suggestion_admin_router
from .user.start import router as start_router
from .user.suggetions import router as suggestion_user_router

handlers_router = Router(name="handlers")
handlers_router.include_routers(
    start_router,
    suggestion_user_router, 
    suggestion_admin_router
)

__all__ = (
    handlers_router
)
