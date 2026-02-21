from aiogram import Router

from middlewares.admin import AdminMiddleware

from .admin_general import router as admin_stats_router
from .suggestions import router as admin_suggestion_router

admin_router = Router(name="admin_router")
admin_router.message.middleware(AdminMiddleware())

admin_router.include_routers(
    admin_suggestion_router,
    admin_stats_router,
)

__all__ = admin_router
