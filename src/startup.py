
import logging
from aiogram import Dispatcher
from aiogram.utils.i18n import I18n
from aiogram.utils.i18n.middleware import ConstI18nMiddleware

from database import DatabaseManager
from middlewares import BanCheckMiddleware, SessionMiddleware, UserMiddleware

from handlers import (
    user_start_router,
    user_suggestion_router,
    admin_suggestion_router,
    admin_general_router,
    admin_ban_user_router,
    admin_mass_message_router,
)

logger = logging.getLogger("kita.startup")

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

    logger.info("Successfully registered middlewares")


def register_routers(dp: Dispatcher):
    dp.include_routers(
        user_start_router,
        user_suggestion_router,
        admin_suggestion_router,
        admin_general_router,
        admin_ban_user_router,
        admin_mass_message_router,
    )

    logger.info("Successfully registered routers")
