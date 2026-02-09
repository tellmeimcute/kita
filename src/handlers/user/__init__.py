from aiogram import Router

from .start import router as user_start_router
from .suggestions import router as user_suggestion_router

user_router = Router(name="user_router")
user_router.include_routers(
    user_suggestion_router,
    user_start_router,
)

__all__ = user_router
