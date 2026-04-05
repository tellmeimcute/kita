import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from config import config as raw_config
from database import DatabaseManager
from startup import register_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kita.main")

async def main():
    redis = Redis(
        host=raw_config.REDIS_HOST,
        port=raw_config.REDIS_PORT,
        password=raw_config.REDIS_PASSWORD,
        db=raw_config.REDIS_DB,
    )

    db = DatabaseManager(raw_config)

    bot = Bot(
        token=raw_config.TG_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=AiohttpSession(proxy=raw_config.PROXY),
    )

    dp = Dispatcher(storage=RedisStorage(redis=redis))

    config = raw_config.model_copy(update={"redis": redis})
    await register_all(
        bot=bot,
        dp=dp,
        db=db,
        config=config,
    )

    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await redis.aclose()
        await db.engine.dispose()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown...")
