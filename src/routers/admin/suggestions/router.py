
from aiogram import Router

from .soloview import router as soloview_router
from .viewer import router as viewer_router

router = Router()
router.include_routers(
    soloview_router,
    viewer_router,
)