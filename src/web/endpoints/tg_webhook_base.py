import asyncio
from abc import ABC, abstractmethod
from typing import Annotated

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from dishka.integrations.fastapi import FromDishka, inject
from fastapi import Body, Depends, FastAPI, Header, HTTPException, Path, status
from loguru import logger

from core.config import Config
from core.cryptographer import Cryptographer
from database.dto import UserBotDTO
from interfaces import BotRegistryProtocol


@inject
async def verify_secret_token(
    cryptographer: FromDishka[Cryptographer],
    bot_id: Annotated[int, Path()],
    x_telegram_bot_api_secret_token: Annotated[str, Header()] = "",
):
    if not cryptographer.verify_bot_secret(x_telegram_bot_api_secret_token, bot_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid secret token",
        )

    return True


class BaseTgWebhookEndpoint(ABC):
    def __init__(
        self,
        dp: Dispatcher,
        config: Config,
    ):
        self.bot_registry: BotRegistryProtocol = None

        self.dp = dp
        self.config = config
        self.tasks = set()

        self._semaphore = asyncio.Semaphore(config.webhook.max_concurrent_updates)

    def assign_registry(self, registry: BotRegistryProtocol):
        self.bot_registry = registry

    def register(self, app: FastAPI, path: str):
        app.add_api_route(
            path=path,
            endpoint=inject(self._handle),
            methods=["POST"],
            include_in_schema=False,
        )

        logger.info("Telegram Webhook endpoint registered on path {}", path)

    async def startup(self):
        await self.dp.emit_startup(**self.dp.workflow_data)
        logger.info("Dispatcher startup event emitted")

    async def shutdown(self):
        await self.dp.emit_shutdown(**self.dp.workflow_data)
        logger.info("Dispatcher shutdown event emitted")

        tasks: list[asyncio.Task] = list(self.tasks)

        for task in tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)

        logger.info("Dispatcher shutdown and {} tasks cleaned up", len(tasks))

    async def _feed_update(self, bot: Bot, update: Update, userbot: UserBotDTO) -> None:
        async with self._semaphore, self.bot_registry.with_bot(bot):
            try:
                await self.dp.feed_update(bot, update, userbot_dto=userbot)
            except Exception:
                logger.exception(
                    "Failed to process update '{}' for bot '{}'",
                    update.update_id,
                    bot.id,
                )

    @abstractmethod
    async def _handle(
        self,
        bot_id: Annotated[int, Path()],
        is_token_valid: Annotated[bool, Depends(verify_secret_token)],
        update: Annotated[Update, Body()],
    ):
        raise NotImplementedError
