import asyncio
import logging

from aiogram import Bot, Dispatcher
from dishka import make_async_container
from dishka.integrations.aiogram import AiogramProvider, setup_dishka


from core.config import RuntimeConfig
from core.logging_config import setup_logging
from di import (
    ConfigProvider,
    DatabaseProvider,
    InfraProvider,
    UtilsProvider,
    FSMProvider,
    RedisProvider,
    MiddlewareProvider,
    BotProvider,
)

from startup import register_all

logger = logging.getLogger("kita.main")

async def main():

    setup_logging()

    container = make_async_container(
        ConfigProvider(),
        UtilsProvider(),
        BotProvider(),
        DatabaseProvider(),
        RedisProvider(),
        InfraProvider(),
        FSMProvider(),
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
