from logging import getLogger

from aiogram import Dispatcher
from dishka import AsyncContainer
from fastapi import FastAPI

from core.config import Config
from lifespan import lifespan

from .endpoints.tg_webhook import TelegramWebhookEndpoint, UserBotRegistrarEndpoint

logger = getLogger("kita.fastapi")


def get_app(
    config: Config,
    registrar_dp: Dispatcher,
    dispatcher: Dispatcher,
    container: AsyncContainer,
) -> FastAPI:
    endpoint = TelegramWebhookEndpoint(
        dp=dispatcher,
        config=config,
        container=container,
    )

    registrar_endpoint = UserBotRegistrarEndpoint(
        dp=registrar_dp,
        config=config,
        container=container,
    )

    app = FastAPI(
        lifespan=lifespan,
        title="Kita UserBots",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    app.state.telegram_webhook = endpoint
    app.state.dispatcher = dispatcher

    app.state.registrar_endpoint = registrar_endpoint
    app.state.registrar_dp = registrar_dp

    path = config.webhook_path + "/{bot_id}"
    endpoint.register(app, path=path)

    path = config.webhook_path
    registrar_endpoint.register(app, path=path)

    logger.info("FastAPI instance initialized")
    return app
