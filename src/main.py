import asyncio
import logging

from aiogram import Bot, Dispatcher
from redis.asyncio import Redis

from dishka import make_async_container
from dishka.integrations.aiogram import AiogramProvider, setup_dishka

from di.config import ConfigProvider
from di.database import DatabaseProvider, RedisProvider
from di.providers import ServicesProvider, UtilsProvider, FSMProvider
from di.suggestion_viewer import SuggestionViewerProvider
from di.bot import BotProvider

from database import DatabaseManager
from startup import register_all

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("kita.main")

async def main():

    container = make_async_container(
        ConfigProvider(),
        UtilsProvider(),
        BotProvider(),
        DatabaseProvider(),
        RedisProvider(),
        ServicesProvider(),
        FSMProvider(),
        SuggestionViewerProvider(),
        AiogramProvider(),
    )

    redis = await container.get(Redis)
    db = await container.get(DatabaseManager)
    bot = await container.get(Bot)
    dp = await container.get(Dispatcher)

    setup_dishka(
        container=container,
        router=dp,
        auto_inject=True,
    )

    await register_all(container, dp)
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot)
    finally:
        await container.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown...")
