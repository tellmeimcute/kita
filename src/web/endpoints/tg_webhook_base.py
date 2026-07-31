import asyncio
import secrets
from abc import ABC, abstractmethod
from logging import getLogger
from typing import Annotated

from aiogram import Bot, Dispatcher
from aiogram.methods import TelegramMethod
from aiogram.types import Update
from dishka import AsyncContainer
from fastapi import Body, FastAPI, Header, HTTPException, Path, status
from pydantic import SecretStr

from core.config import Config
from database.dto import UserBotDTO
from interfaces import BotRegistryProtocol

logger = getLogger("kita.fastapi")


class BaseTgWebhookEndpoint(ABC):

    def __init__(
        self,
        dp: Dispatcher,
        secret_token: SecretStr,
        config: Config,
        container: AsyncContainer,
    ):
        self.bot_registry: BotRegistryProtocol = None

        self.dp = dp
        self.secret_token = secret_token
        self.config = config
        self._container = container
        self.tasks = set()

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

        if self.tasks:
            for task in self.tasks:
                task.cancel()
            await asyncio.gather(*self.tasks, return_exceptions=True)

        logger.info(
            "Dispatcher shutdown and %s tasks cleaned up", len(self.tasks)
        )

    def _verify_secret(self, token: str) -> bool:
        return secrets.compare_digest(token, self.secret_token.get_secret_value())

    def verify_secret(self, bot_id: int, token: str) -> bool:
        if not token:
            logger.warning("Missing secret token header for bot %s", bot_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token header is missing",
            )

        is_valid_token = self._verify_secret(token)
        if not is_valid_token:
            logger.warning("Invalid secret token for bot %s", bot_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid secret token",
            )

        return is_valid_token

    async def _feed_update(self, bot: Bot, update: Update, userbot: UserBotDTO) -> None:
        token = None
        try:
            token = self.bot_registry.set_current(bot)
            result = await self.dp.feed_update(bot, update, userbot_dto=userbot)
            if isinstance(result, TelegramMethod):
                await result.as_(bot)
        except Exception as e:
            logger.exception(
                "Failed to process update '%s' for bot '%s': %s",
                update.update_id, bot.id, e,
            )
        finally:
            if token is not None:
                self.bot_registry.reset_current(token)

    @abstractmethod
    async def _handle(
        self,
        bot_id: Annotated[int, Path()],
        update: Annotated[Update, Body()],
        x_telegram_bot_api_secret_token: Annotated[str, Header()] = "",
    ):
        raise NotImplementedError
    