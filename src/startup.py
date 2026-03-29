import logging
import asyncio
from redis.asyncio import Redis
from redis.exceptions import RedisError, ConnectionError

from aiogram import Dispatcher
from aiogram.utils.i18n import I18n
from aiogram.utils.i18n.middleware import ConstI18nMiddleware

from database import DatabaseManager
from middlewares import BanCheckMiddleware, SessionMiddleware, UserMiddleware, MediaGroupMiddleware
from config import Config

from routers import (
    admin_ban_user_router,
    admin_general_router,
    admin_mass_message_router,
    admin_suggestion_router,
    user_start_router,
    user_suggestion_router,
)

logger = logging.getLogger("kita.startup")

async def check_redis(redis: Redis, timeout: float = 5.0):
    try:
        pong = await asyncio.wait_for(redis.ping(), timeout=timeout)
        if pong:
            logger.info("Redis client successfully connected")
            return True
        raise RedisError("Unexpected ping response")
    except asyncio.TimeoutError:
        logger.error("Redis timeout")
        raise
    except (ConnectionError, RedisError, Exception) as e:
        logger.error("Error Redis ping: %s", e)
        raise

def register_middlewares(dp: Dispatcher, db: DatabaseManager):
    session_middleware = SessionMiddleware(db.session_maker)
    user_middleware = UserMiddleware()
    bancheck_middleware = BanCheckMiddleware()

    i18n = I18n(path="locales", default_locale="ru", domain="messages")
    i18n_middleware = ConstI18nMiddleware(locale="ru", i18n=i18n)

    dp.message.middleware(session_middleware)
    dp.message.middleware(user_middleware)
    dp.message.middleware(bancheck_middleware)
    dp.message.outer_middleware(i18n_middleware)

    logger.info("Middlewares successfully registered ")


def register_routers(dp: Dispatcher, config: Config):
    media_group_middleware = MediaGroupMiddleware(redis_client=config.redis)

    user_suggestion_router.message.middleware(media_group_middleware)
    admin_mass_message_router.message.middleware(media_group_middleware)

    dp.include_routers(
        user_start_router,
        user_suggestion_router,
        admin_suggestion_router,
        admin_general_router,
        admin_ban_user_router,
        admin_mass_message_router,
    )

    logger.info("Routers successfully registered")

