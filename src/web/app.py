from aiogram import Dispatcher
from fastapi import FastAPI
from loguru import logger

from core.config import Config
from lifespan import lifespan

from .endpoints.health import health
from .endpoints.tg_webhook import TelegramWebhookEndpoint, UserBotRegistrarEndpoint


def get_app(
    config: Config,
    registrar_dp: Dispatcher,
    dispatcher: Dispatcher,
) -> FastAPI:
    endpoint = TelegramWebhookEndpoint(
        dp=dispatcher,
        config=config,
    )

    registrar_endpoint = UserBotRegistrarEndpoint(
        dp=registrar_dp,
        config=config,
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

    app.add_api_route("/health", health, methods=["GET"], include_in_schema=False)

    path = config.webhook.path + "/{bot_id}"
    endpoint.register(app, path=path)

    path = config.webhook.path
    registrar_endpoint.register(app, path=path)

    logger.info("FastAPI instance initialized")
    return app
