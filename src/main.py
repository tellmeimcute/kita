import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config
from database import DatabaseManager
from handlers import root_router
from middlewares import BanCheckMiddleware, SessionMiddleware, UserMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(f"kita_main")

db = DatabaseManager()
dp = Dispatcher(config=config)
dp.include_router(root_router)

bot = Bot(
    config.TG_TOKEN.get_secret_value(), default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

session_middleware = SessionMiddleware(db.session_maker)
user_middleware = UserMiddleware()
bancheck_middleware = BanCheckMiddleware()

dp.message.middleware(session_middleware)
dp.message.middleware(user_middleware)
dp.message.middleware(bancheck_middleware)

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
