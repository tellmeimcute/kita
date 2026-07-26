from logging import getLogger

from aiogram import Dispatcher
from dishka import AsyncContainer
from fastapi import FastAPI

from core.config import Config
from interfaces import BotRegistryProtocol
from lifespan import lifespan

from .endpoints.tg_webhook import TelegramWebhookEndpoint


logger = getLogger("kita.fastapi")


def get_app(
    config: Config,
    dispatcher: Dispatcher,
    container: AsyncContainer,
) -> FastAPI:
    endpoint = TelegramWebhookEndpoint(
        dp=dispatcher,
        secret_token=config.webhook_secret,
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

    path = config.webhook_path + "/{bot_id}"
    endpoint.register(app, path=path)

    logger.info("FastAPI instance initialized")
    return app
