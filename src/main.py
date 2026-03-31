import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from config import RuntimeConfig, config
from database import DatabaseManager
from services.notifier import NotifierService
from startup import register_middlewares, register_routers, check_redis

from redis.asyncio import Redis
from aiogram.fsm.storage.redis import RedisStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kita.main")

redis = Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    password=config.REDIS_PASSWORD,
    db=config.REDIS_DB
)

config = config.model_copy(update={"redis": redis})

db = DatabaseManager(config)

bot = Bot(
    token=config.TG_TOKEN.get_secret_value(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    session=AiohttpSession(proxy=config.PROXY),
)

dp = Dispatcher(
    notifier=NotifierService(bot, db.session_maker),
    storage=RedisStorage(redis=redis),
)


async def on_startup():
    try:
        channel_info = await bot.get_chat(config.CHANNEL_ID)
        bot_user = await bot.get_me()

        runtime_config = RuntimeConfig(
            channel_name=channel_info.full_name,
            bot_username=bot_user.username,
            bot_url=f"https://t.me/{bot_user.username}",
        )

        dp.workflow_data["config"] = config.model_copy(update={"runtime_config": runtime_config})

        logger.info("Runtime config loaded")
    except Exception as e:
        logger.error("Failed to load runtime config: %s", e)

async def on_shutdown():
    await db.engine.dispose()


async def main():
    await check_redis(redis)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    register_middlewares(dp, db)
    register_routers(dp, config)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown...")
