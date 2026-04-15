import asyncio
import logging

from aiogram import Bot, Dispatcher
from dishka import make_async_container
from dishka.integrations.aiogram import AiogramProvider, setup_dishka

from di.config import ConfigProvider
from di.database import DatabaseProvider
from di.providers import ServicesProvider, UtilsProvider, FSMProvider
from di.redis import RedisProvider
from di.suggestion_viewer import SuggestionViewerProvider
from di.middleware import MiddlewareProvider
from di.bot import BotProvider

from core.config import RuntimeConfig

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
        MiddlewareProvider(),
        AiogramProvider(),
    )

    bot = await container.get(Bot)
    dp = await container.get(Dispatcher)

    await container.get(RuntimeConfig)

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
