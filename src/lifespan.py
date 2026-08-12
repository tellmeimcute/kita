from contextlib import asynccontextmanager

from aiogram import Dispatcher
from aiogram.utils.token import extract_bot_id
from dishka import AsyncContainer
from fastapi import FastAPI
from loguru import logger

from core.config import Config
from interfaces import BotRegistryProtocol
from services.webhooks import WebhookService
from startup import setup_registrar_dp, setup_slave_dp
from task_queue.broker import broker
from web.endpoints.tg_webhook import TelegramWebhookEndpoint, UserBotRegistrarEndpoint


@asynccontextmanager
async def lifespan(app: FastAPI):
    telegram_webhook: TelegramWebhookEndpoint = app.state.telegram_webhook
    container: AsyncContainer = app.state.dishka_container
    dp: Dispatcher = app.state.dispatcher

    registrar_webhook: UserBotRegistrarEndpoint = app.state.registrar_endpoint
    registrar_dp: Dispatcher = app.state.registrar_dp

    config = await container.get(Config)
    webhooks_service = await container.get(WebhookService)

    await setup_slave_dp(container, dp)
    await setup_registrar_dp(container, registrar_dp)

    registry: BotRegistryProtocol = await container.get(BotRegistryProtocol)
    registry.allowed_updates = dp.resolve_used_update_types()

    main_bot_token = config.tg_token.get_secret_value()
    main_bot = registry.get_or_create(
        bot_id=extract_bot_id(main_bot_token),
        token=main_bot_token,
    )

    telegram_webhook.assign_registry(registry)

    registrar_webhook.assign_bot(main_bot)
    registrar_webhook.assign_registry(registry)

    await telegram_webhook.startup()
    await registrar_webhook.startup()

    await broker.startup()

    allowed_updates = registrar_dp.resolve_used_update_types()
    await webhooks_service.set_webhook(
        main_bot,
        url=config.webhook_base_url,
        allowed_updates=allowed_updates,
    )

    logger.info("FastAPI startup complete")

    yield

    await telegram_webhook.shutdown()
    await registrar_webhook.shutdown()

    await broker.shutdown()

    await container.close()
    await registry.close()

    logger.info("FastAPI shutdown complete")
