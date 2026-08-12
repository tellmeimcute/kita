import asyncio
from typing import Annotated

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from dishka import AsyncContainer
from dishka.integrations.fastapi import FromDishka
from fastapi import (
    Body,
    Depends,
    Header,
    HTTPException,
    Path,
    Response,
    status,
)
from loguru import logger

from core.config import Config
from core.cryptographer import Cryptographer
from interfaces import UnitOfWorkProtocol
from services import UserBotService

from .tg_webhook_base import BaseTgWebhookEndpoint, verify_secret_token


class TelegramWebhookEndpoint(BaseTgWebhookEndpoint):
    async def _handle(
        self,
        bot_id: Annotated[int, Path()],
        is_token_valid: Annotated[bool, Depends(verify_secret_token)],
        update: Annotated[Update, Body()],
        uow: FromDishka[UnitOfWorkProtocol],
        userbot_service: FromDishka[UserBotService],
    ):
        async with uow.transaction():
            userbot = await userbot_service.get(bot_id)

        if not userbot or not userbot.active:
            logger.warning("Bot {} not exists or inactive, skipping update", bot_id)
            raise HTTPException(
                status_code=status.HTTP_200_OK, detail="Bot not exists or inactive"
            )

        bot = self.bot_registry.get_or_create(bot_id, userbot.token.get_secret_value())

        task = asyncio.create_task(self._feed_update(bot, update, userbot))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

        return Response(status_code=status.HTTP_200_OK)


class UserBotRegistrarEndpoint(TelegramWebhookEndpoint):
    def __init__(
        self,
        dp: Dispatcher,
        config: Config,
        container: AsyncContainer,
    ):
        super().__init__(dp, config, container)
        self.bot = None

    def assign_bot(self, bot: Bot):
        self.bot = bot

    async def _handle(
        self,
        update: Annotated[Update, Body()],
        crypto: FromDishka[Cryptographer],
        x_telegram_bot_api_secret_token: Annotated[str, Header()] = "",
    ):
        if not crypto.verify_bot_secret(x_telegram_bot_api_secret_token, self.bot.id):
            logger.warning("Invalid secret token for bot {}", self.bot.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid secret token",
            )

        task = asyncio.create_task(self._feed_update(self.bot, update, None))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

        return Response(status_code=status.HTTP_200_OK)
