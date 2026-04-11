import logging

from aiogram import Dispatcher, Router
from aiogram.utils.i18n.middleware import ConstI18nMiddleware
from dishka import AsyncContainer

from middlewares import (
    BanCheckMiddleware,
    MediaGroupMiddleware,
    SessionMiddleware,
    UserMiddleware,
    AdminMiddleware,
    KitaI18nMiddleware,
)

from routers import (
    admin_ban_user_router,
    admin_general_router,
    admin_mass_message_router,
    admin_suggestion_router,
    user_start_router,
    user_suggestion_router,
)

from routers.errors import router as errors_router

logger = logging.getLogger("kita.startup")


async def register_middlewares(container: AsyncContainer, dp: Dispatcher):
    session_middleware = await container.get(SessionMiddleware)
    user_middleware = await container.get(UserMiddleware)
    bancheck_middleware = await container.get(BanCheckMiddleware)

    session_middleware.setup(dp)
    user_middleware.setup(dp)
    bancheck_middleware.setup(dp)

    i18n_middleware = await container.get(KitaI18nMiddleware)
    i18n_middleware.setup(dp)
    
    logger.info("Middlewares successfully registered ")


async def register_routers(container: AsyncContainer, dp: Dispatcher):
    media_group_middleware = await container.get(MediaGroupMiddleware)

    media_group_middleware.setup(user_suggestion_router)
    media_group_middleware.setup(admin_mass_message_router)

    # Order is important!!

    user_routers = Router()
    user_routers.include_routers(
        user_start_router,
        user_suggestion_router,
    )

    admin_routers = Router()
    admin_routers.include_routers(
        admin_suggestion_router,
        admin_general_router,
        admin_ban_user_router,
        admin_mass_message_router,
    )

    admin_middleware = await container.get(AdminMiddleware)
    admin_middleware.setup(admin_routers)

    dp.include_routers(
        errors_router,
        user_routers,
        admin_routers,
    )

    logger.info("Routers successfully registered")

async def register_all(
    container: AsyncContainer,
    dp: Dispatcher,
):
    await register_middlewares(container, dp)
    await register_routers(container, dp)
    logger.info("Bot fully init")