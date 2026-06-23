
import logging

from aiogram import Dispatcher, Router
from aiogram_dialog import setup_dialogs
from dishka import AsyncContainer

from middlewares import (
    AdminMiddleware,
    BanCheckMiddleware,
    KitaI18nMiddleware,
    MediaGroupMiddleware,
    UserMiddleware,
    RateLimitMiddleware,
)

from routers.admin import suggestion_router as admin_suggestion_router
from routers.admin import menu_dialog as admin_menu_dialog
from routers.admin import banner_dialog as admin_banner_dialog
from routers.admin import broadcast_dialog as admin_broadcast_dialog
from routers.admin import user_moderation_dialog as admin_user_moderation_dialog

from routers.user import menu_dialog as user_menu_dialog
from routers.user import menu_router as user_menu_router
from routers.user import suggestion_dialog as user_suggestion_dialog

from routers.system import chat_member_router
from routers.system import errors_router


logger = logging.getLogger("kita.startup")


async def register_middlewares(container: AsyncContainer, dp: Dispatcher):
    user_middleware = await container.get(UserMiddleware)
    bancheck_middleware = await container.get(BanCheckMiddleware)
    i18n_middleware = await container.get(KitaI18nMiddleware)
    media_group_middleware = await container.get(MediaGroupMiddleware)
    rate_limit_middleware = await container.get(RateLimitMiddleware)

    user_middleware.setup(dp)
    i18n_middleware.setup(dp)
    bancheck_middleware.setup(dp)
    media_group_middleware.setup(dp)
    rate_limit_middleware.setup(dp)

    logger.info("Dispatcher Middlewares successfully registered")


async def register_routers(container: AsyncContainer, dp: Dispatcher):
    # Order is important!!

    user_routers = Router(name="user_root")
    user_routers.include_routers(
        user_menu_router,
        user_menu_dialog,
        user_suggestion_dialog
    )

    admin_routers = Router(name="admin_root")
    admin_routers.include_routers(
        admin_suggestion_router,
        admin_menu_dialog,
        admin_banner_dialog,
        admin_broadcast_dialog,
        admin_user_moderation_dialog,
    )

    admin_middleware = await container.get(AdminMiddleware)
    admin_middleware.setup(admin_routers)

    setup_dialogs(dp)
    dp.include_routers(
        errors_router,
        chat_member_router,
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
