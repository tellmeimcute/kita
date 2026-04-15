import logging

from aiogram import Dispatcher, Router
from aiogram_dialog import setup_dialogs
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
    admin_suggestion_router,
)

from routers.errors import router as errors_router

from routers.main_menu.handlers import router as main_menu_router
from routers.main_menu.dialog import dialog as main_menu_dialog

from routers.admin_menu.dialog import dialog as admin_menu_dialog
from routers.admin_menu.handlers import router as admin_menu_router


logger = logging.getLogger("kita.startup")


async def register_middlewares(container: AsyncContainer, dp: Dispatcher):
    session_middleware = await container.get(SessionMiddleware)
    user_middleware = await container.get(UserMiddleware)
    bancheck_middleware = await container.get(BanCheckMiddleware)
    media_group_middleware = await container.get(MediaGroupMiddleware)

    session_middleware.setup(dp)
    user_middleware.setup(dp)
    bancheck_middleware.setup(dp)
    media_group_middleware.setup(dp)

    i18n_middleware = await container.get(KitaI18nMiddleware)
    i18n_middleware.setup(dp)

    logger.info("Middlewares successfully registered ")


async def register_routers(container: AsyncContainer, dp: Dispatcher):
    # Order is important!!

    user_routers = Router(name="user_root")
    main_menu_router.include_routers(main_menu_dialog)
    user_routers.include_routers(
        main_menu_router,
    )

    admin_routers = Router(name="admin_root")
    admin_menu_router.include_routers(admin_menu_dialog)
    admin_routers.include_routers(
        admin_suggestion_router,
        admin_menu_router,
    )

    admin_middleware = await container.get(AdminMiddleware)
    admin_middleware.setup(admin_routers)

    setup_dialogs(dp)
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