import logging

from redis.asyncio import Redis

from aiogram import Bot, Dispatcher, Router
from aiogram.utils.i18n import I18n
from aiogram.utils.i18n.middleware import ConstI18nMiddleware
from dishka import AsyncContainer

from config import Config, RuntimeConfig
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

logger = logging.getLogger("kita.startup")

async def get_runtime_config(bot: Bot, raw_config: Config):
    channel_info = await bot.get_chat(raw_config.CHANNEL_ID)
    bot_user = await bot.get_me()

    runtime_config = RuntimeConfig(
        channel_name=channel_info.full_name,
        bot_username=bot_user.username,
        bot_url=f"https://t.me/{bot_user.username}",
    )

    return runtime_config

def register_middlewares(dp: Dispatcher):
    session_middleware = SessionMiddleware()
    user_middleware = UserMiddleware()
    bancheck_middleware = BanCheckMiddleware()

    i18n = I18n(path="locales", default_locale="ru", domain="messages")
    i18n_middleware = ConstI18nMiddleware(locale="ru", i18n=i18n)

    dp.message.middleware(session_middleware)
    dp.message.middleware(user_middleware)
    dp.message.middleware(bancheck_middleware)
    dp.message.outer_middleware(i18n_middleware)

    logger.info("Middlewares successfully registered ")


def register_routers(dp: Dispatcher, redis: Redis):
    media_group_middleware = MediaGroupMiddleware(redis_client=redis)

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
    admin_middleware = AdminMiddleware()
    admin_routers.message.middleware(admin_middleware)

    dp.include_routers(user_routers, admin_routers)

    logger.info("Routers successfully registered")

async def register_all(
    container: AsyncContainer,
    dp: Dispatcher,
):
    redis = await container.get(Redis)

    register_middlewares(dp)
    register_routers(dp, redis)

    logger.info("Bot fully init")