import asyncio
import logging

from redis.asyncio import Redis

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from dishka import make_async_container
from dishka.integrations.aiogram import AiogramProvider, setup_dishka

from core.config import Config
from core.logging_config import setup_logging
from interfaces import BotRegistryProtocol
from di import (
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
        InfraProvider(),
        UtilsProvider(),
        BotProvider(),
        DatabaseProvider(),
        RedisProvider(),
        FSMProvider(),
        MiddlewareProvider(),
        AiogramProvider(),
    )

    config = await container.get(Config)
    redis = await container.get(Redis)

    bot = Bot(
        token=config.tg_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=AiohttpSession(proxy=config.PROXY),
    )

    storage = RedisStorage(redis=redis, key_builder=DefaultKeyBuilder(with_destiny=True, with_bot_id=True))
    dp = Dispatcher(storage=storage, name="dispatcher")

    setup_dishka(
        container=container,
        router=dp,
        auto_inject=True,
    )

    registry: BotRegistryProtocol = await container.get(BotRegistryProtocol)
    registry.register(bot)

    await register_all(container, dp)
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot)
    finally:
        await container.close()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown...")
