import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.utils.i18n.middleware import ConstI18nMiddleware
from dishka import AsyncContainer

from config import Config, RuntimeConfig
from helpers.consts import T_ME
from middlewares import (
    BanCheckMiddleware,
    MediaGroupMiddleware,
    SessionMiddleware,
    UserMiddleware,
    AdminMiddleware
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

async def get_runtime_config(bot: Bot, raw_config: Config):
    channel_info = await bot.get_chat(raw_config.CHANNEL_ID)
    bot_user = await bot.get_me()

    runtime_config = RuntimeConfig(
        channel_name=channel_info.full_name,
        bot_username=bot_user.username,
        bot_url=f"{T_ME}{bot_user.username}",
    )

    return runtime_config

async def register_middlewares(container: AsyncContainer, dp: Dispatcher):
    session_middleware = await container.get(SessionMiddleware)
    user_middleware = await container.get(UserMiddleware)
    bancheck_middleware = await container.get(BanCheckMiddleware)

    i18n_middleware = await container.get(ConstI18nMiddleware)
    i18n_middleware.setup(dp)

    dp.message.middleware(session_middleware)
    dp.message.middleware(user_middleware)
    dp.message.middleware(bancheck_middleware)
    dp.message.outer_middleware(i18n_middleware)

    logger.info("Middlewares successfully registered ")


async def register_routers(container: AsyncContainer, dp: Dispatcher):
    media_group_middleware = await container.get(MediaGroupMiddleware)

    user_suggestion_router.message.middleware(media_group_middleware)
    admin_mass_message_router.message.middleware(media_group_middleware)

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
    admin_routers.message.middleware(admin_middleware)

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