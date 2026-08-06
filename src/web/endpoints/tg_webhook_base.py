import asyncio
from abc import ABC, abstractmethod
from logging import getLogger
from typing import Annotated

from aiogram import Bot, Dispatcher
from aiogram.methods import TelegramMethod
from aiogram.types import Update
from dishka import AsyncContainer
from dishka.integrations.fastapi import FromDishka, inject
from fastapi import Body, Depends, FastAPI, Header, HTTPException, Path, status

from core.config import Config
from core.cryptographer import Cryptographer
from database.dto import UserBotDTO
from interfaces import BotRegistryProtocol

logger = getLogger("kita.fastapi")


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
        container: AsyncContainer,
    ):
        self.bot_registry: BotRegistryProtocol = None

        self.dp = dp
        self.config = config
        self.tasks = set()

        self._container = container
        self._semaphore = asyncio.Semaphore(config.max_concurrent_updates)

    def assign_registry(self, registry: BotRegistryProtocol):
        self.bot_registry = registry

    def register(self, app: FastAPI, path: str):
        app.add_api_route(
            path=path,
            endpoint=self._handle,
            methods=["POST"],
            include_in_schema=False,
        )

        logger.info("Telegram Webhook endpoint registered on path %s", path)

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

        logger.info("Dispatcher shutdown and %s tasks cleaned up", len(tasks))

    async def _feed_update(self, bot: Bot, update: Update, userbot: UserBotDTO) -> None:
        async with self._semaphore:
            token = None
            try:
                token = self.bot_registry.set_current(bot)
                result = await self.dp.feed_update(bot, update, userbot_dto=userbot)
                if isinstance(result, TelegramMethod):
                    await result.as_(bot)
            except Exception as e:
                logger.exception(
                    "Failed to process update '%s' for bot '%s': %s",
                    update.update_id,
                    bot.id,
                    e,
                )
            finally:
                if token is not None:
                    self.bot_registry.reset_current(token)

    @abstractmethod
    async def _handle(
        self,
        bot_id: Annotated[int, Path()],
        is_token_valid: Annotated[bool, Depends(verify_secret_token)],
        update: Annotated[Update, Body()],
    ):
        raise NotImplementedError
