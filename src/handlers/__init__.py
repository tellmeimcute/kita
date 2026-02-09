from aiogram import Router

from .admin import admin_router
from .user import user_router

root_router = Router(name="root_router")
root_router.include_routers(
    user_router,
    admin_router,
)

__all__ = (root_router)
