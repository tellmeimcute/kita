from aiogram import Dispatcher, Router
from aiogram_dialog import setup_dialogs
from dishka import AsyncContainer
from loguru import logger

from middlewares import (
    AdminMiddleware,
    BanCheckMiddleware,
    KitaI18nMiddleware,
    MediaGroupMiddleware,
    RateLimitMiddleware,
    UserBotRateLimitMiddleware,
    UserMiddleware,
)
from routers.admin import banner_dialog as admin_banner_dialog
from routers.admin import broadcast_dialog as admin_broadcast_dialog
from routers.admin import menu_dialog as admin_menu_dialog
from routers.admin import suggestion_router as admin_suggestion_router
from routers.admin import user_moderation_dialog as admin_user_moderation_dialog
from routers.master import (
    master_menu_dialog,
    master_menu_router,
    userbot_menu_dialog,
    userbot_register_dialog,
)
from routers.system import get_error_router
from routers.user import menu_dialog as user_menu_dialog
from routers.user import menu_router as user_menu_router
from routers.user import suggestion_dialog as user_suggestion_dialog


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
    user_routers.include_routers(user_menu_router, user_menu_dialog, user_suggestion_dialog)

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
        get_error_router(),
        user_routers,
        admin_routers,
    )

    logger.info("Routers successfully registered")


async def setup_slave_dp(
    container: AsyncContainer,
    dp: Dispatcher,
):
    await register_middlewares(container, dp)
    await register_routers(container, dp)

    logger.info("Slave dp fully init")


async def setup_registrar_dp(container: AsyncContainer, dp: Dispatcher):
    user_middleware = await container.get(UserMiddleware)
    i18n_middleware = await container.get(KitaI18nMiddleware)
    rate_limit_middleware = await container.get(RateLimitMiddleware)
    userbot_limit = await container.get(UserBotRateLimitMiddleware)

    user_middleware.setup(dp)
    i18n_middleware.setup(dp)
    rate_limit_middleware.setup(dp)

    setup_dialogs(dp)

    userbot_limit.setup(userbot_menu_dialog)

    dp.include_routers(
        master_menu_router,
        master_menu_dialog,
        userbot_register_dialog,
        userbot_menu_dialog,
        get_error_router(),
    )

    logger.info("Registrar dp fully init")
