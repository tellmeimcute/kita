
from contextlib import asynccontextmanager
from logging import getLogger

from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from dishka import AsyncContainer
from fastapi import FastAPI

from core.config import Config
from core.events import EventBus

from web.endpoints.tg_webhook import TelegramWebhookEndpoint, UserBotRegistrarEndpoint
from services.webhooks import WebhookService
from interfaces import BotRegistryProtocol
from startup import register_all, register_events, setup_registrar_dp

logger = getLogger("kita.fastapi")


@asynccontextmanager
async def lifespan(app: FastAPI):
    telegram_webhook: TelegramWebhookEndpoint = app.state.telegram_webhook
    container: AsyncContainer = app.state.dishka_container
    dp: Dispatcher = app.state.dispatcher

    registrar_webhook: UserBotRegistrarEndpoint = app.state.registrar_endpoint
    registrar_dp: Dispatcher = app.state.registrar_dp

    event_bus = await container.get(EventBus)
    config = await container.get(Config)
    webhooks_service = await container.get(WebhookService)

    await register_all(container, dp)
    await register_events(event_bus)

    await setup_registrar_dp(container, registrar_dp)

    main_bot = Bot(
        token=config.tg_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=AiohttpSession(proxy=config.PROXY),
    )

    registry: BotRegistryProtocol = await container.get(BotRegistryProtocol)
    registry.register(main_bot)

    telegram_webhook.assign_registry(registry)

    registrar_webhook.assign_bot(main_bot)
    registrar_webhook.assign_registry(registry)

    await telegram_webhook.startup()
    await registrar_webhook.startup()

    await webhooks_service.set_webhook(main_bot, url=config.webhook_base_url)

    logger.info("FastAPI startup complete, webhooks registered")

    yield

    await telegram_webhook.shutdown()
    await registrar_webhook.shutdown()

    await registry.close()
    logger.info("FastAPI shutdown complete, webhooks removed")