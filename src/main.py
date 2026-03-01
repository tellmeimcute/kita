import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from config import config
from database import DatabaseManager
from handlers import root_router
from services.notifier import Notifier

from helpers.utils.startup import register_middlewares

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
    notifier=Notifier(bot, db.session_maker),
)
dp.include_router(root_router)

async def on_startup():
    try:
        channel_info = await bot.get_chat(config.CHANNEL_ID)
        config.channel_name = channel_info.full_name
        logger.info("Channel name loaded: %s", config.channel_name)
    except Exception as e:
        logger.error("Failed to load channel info %s", e)

    try:
        bot_user = await bot.get_me()
        config.bot_username = bot_user.username
        config.bot_url = f"https://t.me/{bot_user.username}"
        logger.info("Bot info loaded in config")
    except:
        logger.error("Failed to load bot info")

async def on_shutdown():
    await db.engine.dispose()

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    register_middlewares(dp, db)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown...")
