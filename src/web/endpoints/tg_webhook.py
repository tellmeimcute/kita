import asyncio
from logging import getLogger
from typing import Annotated

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from dishka import AsyncContainer
from fastapi import (
    Body,
    Header,
    HTTPException,
    Path,
    Response,
    status,
)
from pydantic import SecretStr

from core.config import Config
from database.dto import UserBotDTO
from interfaces import UnitOfWorkProtocol
from services import UserBotService

from .tg_webhook_base import BaseTgWebhookEndpoint

logger = getLogger("kita.fastapi")


class TelegramWebhookEndpoint(BaseTgWebhookEndpoint):

    async def _get_userbot(self, bot_id: int) -> UserBotDTO | None:
        try:
            async with self._container() as container:
                uow = await container.get(UnitOfWorkProtocol)
                userbot_service = await container.get(UserBotService)
                async with uow.transaction():
                    userbot = await userbot_service.get(bot_id)
            return userbot
        except Exception:
            logger.exception("Failed to fetch UserBot %s from DataBase", bot_id)
            return None

    async def _resolve_bot(self, bot_id: int) -> tuple[Bot, UserBotDTO]:
        userbot = await self._get_userbot(bot_id)

        if not userbot:
            logger.warning("Bot %s not found, skipping update", bot_id)
            raise HTTPException(status_code=status.HTTP_200_OK, detail="Bot is not registered")
        
        if userbot and not userbot.active:
            logger.warning("Bot %s marked inactive, skipping update", bot_id)
            raise HTTPException(status_code=status.HTTP_200_OK, detail="Bot inactive")
        
        bot = self.bot_registry.get_or_create(
            bot_id, userbot.token.get_secret_value()
        )

        if bot:
            return bot, userbot
        
        logger.warning("Bot %s not found, skipping update", bot_id)
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail="Bot not registered",
        )

    async def _handle(
        self,
        bot_id: Annotated[int, Path()],
        update: Annotated[Update, Body()],
        x_telegram_bot_api_secret_token: Annotated[str, Header()] = "",
    ):
        self.verify_secret(bot_id, x_telegram_bot_api_secret_token)
        
        bot, userbot = await self._resolve_bot(bot_id)

        task = asyncio.create_task(self._feed_update(bot, update, userbot))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

        return Response(status_code=status.HTTP_200_OK)


class UserBotRegistrarEndpoint(TelegramWebhookEndpoint):

    def __init__(
        self,
        dp: Dispatcher,
        secret_token: SecretStr,
        config: Config,
        container: AsyncContainer,
    ):
        super().__init__(dp, secret_token, config, container)
        self.bot = None

    def assign_bot(self, bot: Bot):
        self.bot = bot

    async def _handle(
        self,
        update: Annotated[Update, Body()],
        x_telegram_bot_api_secret_token: Annotated[str, Header()] = "",
    ):
        self.verify_secret(self.bot.id, x_telegram_bot_api_secret_token)

        task = asyncio.create_task(self._feed_update(self.bot, update, None))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

        return Response(status_code=status.HTTP_200_OK)
    