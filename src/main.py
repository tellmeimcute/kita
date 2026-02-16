import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.utils.i18n import I18n
from aiogram.utils.i18n.middleware import ConstI18nMiddleware

from config import config
from database import DatabaseManager
from handlers import root_router
from middlewares import BanCheckMiddleware, SessionMiddleware, UserMiddleware
from services.notifier import Notifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kita_main")

db = DatabaseManager()

proxy_session = AiohttpSession(proxy=config.PROXY)
bot = Bot(
    config.TG_TOKEN.get_secret_value(), 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    session=proxy_session,
)

dp = Dispatcher(
    config=config,
    notifier=Notifier(bot, logger),
)
dp.include_router(root_router)

session_middleware = SessionMiddleware(db.session_maker)
user_middleware = UserMiddleware()
bancheck_middleware = BanCheckMiddleware()

i18n = I18n(path="locales", default_locale="ru", domain="messages")
i18n_middleware = ConstI18nMiddleware(locale="ru", i18n=i18n)

dp.message.middleware(session_middleware)
dp.message.middleware(user_middleware)
dp.message.middleware(bancheck_middleware)
dp.message.outer_middleware(i18n_middleware)


async def on_startup():
    try:
        channel_info = await bot.get_chat(config.CHANNEL_ID)
        config.channel_name = channel_info.full_name
        logger.info("Channel name loaded in config: %s", config.channel_name)
    except Exception as e:
        logger.error("Failed to load channel name %s", e)


async def main():
    try:
        dp.startup.register(on_startup)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Закрываюсь...")
