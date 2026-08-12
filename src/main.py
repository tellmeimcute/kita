import uvicorn
from aiogram import Dispatcher
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage
from dishka import AsyncContainer, make_async_container
from dishka.integrations.aiogram import AiogramProvider
from dishka.integrations.aiogram import setup_dishka as setup_dishka_aiogram
from dishka.integrations.fastapi import setup_dishka as setup_dishka_fastapi
from fastapi import FastAPI
from loguru import logger

from core.config import Config
from core.logging_config import setup_logging
from di import (
    BotProvider,
    DatabaseProvider,
    FSMProvider,
    InfraProvider,
    MiddlewareProvider,
    RedisProvider,
    UtilsProvider,
)
from web import get_app

config = Config.get()
setup_logging(config.log_level.upper())


def create_container() -> AsyncContainer:
    return make_async_container(
        InfraProvider(),
        UtilsProvider(),
        BotProvider(),
        DatabaseProvider(),
        RedisProvider(),
        FSMProvider(),
        MiddlewareProvider(),
        AiogramProvider(),
    )


def get_storage(config: Config):
    return RedisStorage.from_url(
        url=config.redis.redis_url,
        key_builder=DefaultKeyBuilder(with_destiny=True, with_bot_id=True),
    )


def get_dispatcher(storage: RedisStorage):
    dp = Dispatcher(storage=storage, name="dispatcher")
    logger.info(f"Initialized Dispatcher with {id(storage)} Redis storage")
    return dp


def application() -> FastAPI:
    container = create_container()
    storage = get_storage(config)

    registrar_dp = get_dispatcher(storage)
    setup_dishka_aiogram(container, registrar_dp, auto_inject=True)

    dp = get_dispatcher(storage)
    setup_dishka_aiogram(container, dp, auto_inject=True)

    app = get_app(config, registrar_dp, dp)
    setup_dishka_fastapi(container, app)

    return app


if __name__ == "__main__":
    uvicorn.run(
        app=application,
        host="0.0.0.0",
        port=8000,
        factory=True,
        log_config=None,
    )
