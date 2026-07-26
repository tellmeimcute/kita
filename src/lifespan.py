
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

from web.endpoints.tg_webhook import TelegramWebhookEndpoint
from services.webhooks import WebhookService
from interfaces import BotRegistryProtocol
from startup import register_all, register_events

logger = getLogger("kita.fastapi")


@asynccontextmanager
async def lifespan(app: FastAPI):
    telegram_webhook: TelegramWebhookEndpoint = app.state.telegram_webhook
    container: AsyncContainer = app.state.dishka_container
    dp: Dispatcher = app.state.dispatcher

    event_bus = await container.get(EventBus)
    config = await container.get(Config)
    webhooks_service = await container.get(WebhookService)

    await register_all(container, dp)
    await register_events(event_bus)

    main_bot = Bot(
        token=config.tg_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=AiohttpSession(proxy=config.PROXY),
    )

    registry: BotRegistryProtocol = await container.get(BotRegistryProtocol)
    registry.register(main_bot)

    telegram_webhook.assign_registry(registry)

    await telegram_webhook.startup()
    await webhooks_service.set_webhook(main_bot)
    logger.info("FastAPI startup complete, webhooks registered")

    yield

    await telegram_webhook.shutdown()
    await registry.close()
    logger.info("FastAPI shutdown complete, webhooks removed")