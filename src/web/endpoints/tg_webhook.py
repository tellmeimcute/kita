import asyncio
import secrets
from typing import Annotated

from logging import getLogger
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.methods import TelegramMethod
from aiogram.types import Update

from fastapi import (
    FastAPI, HTTPException, Response, status,
    Header, Body, Path
)

from dishka import AsyncContainer

from core.config import Config
from services import UserBotService
from interfaces import BotRegistryProtocol, UnitOfWorkProtocol

logger = getLogger("kita.fastapi")


class TelegramWebhookEndpoint:

    def __init__(
        self,
        dp: Dispatcher,
        secret_token: str,
        config: Config,
        container: AsyncContainer,
    ):
        self.bot_registry = None

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
            "Dispatcher shutdown and %s tasks cleaned up",
            len(self.tasks)
        )

    def _verify_secret(self, token: str) -> bool:
        return secrets.compare_digest(token, self.secret_token)

    async def _lazy_register(self, bot_id: int) -> Bot | None:
        try:
            async with self._container() as container:
                uow = await container.get(UnitOfWorkProtocol)
                userbot_service = await container.get(UserBotService)
                async with uow.transaction():
                    userbot = await userbot_service.get(bot_id)

            if not userbot:
                return None
            
            bot = Bot(
                token=userbot.token.get_secret_value(),
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
                session=AiohttpSession(proxy=self.config.PROXY),
            )
            self.bot_registry.register(bot)
            logger.info("Lazy registered bot %s from DB", bot_id)
            return bot
        except Exception:
            logger.exception("Failed to lazy-register bot %s", bot_id)
            return None

    async def _resolve_bot(self, bot_id: int):
        try:
            bot = self.bot_registry.get(bot_id)
        except KeyError:
            bot = await self._lazy_register(bot_id)
        return bot

    async def _feed_update(self, bot: Bot, update: Update) -> None:
        token = None
        try:
            token = self.bot_registry.set_current(bot)
            result = await self.dp.feed_update(bot, update)
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

    async def _handle(
        self,
        bot_id: Annotated[int, Path()],
        update: Annotated[Update, Body()],
        x_telegram_bot_api_secret_token: Annotated[str, Header()] = "",
    ):
        if not x_telegram_bot_api_secret_token:
            logger.warning("Missing secret token header for bot %s", bot_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token header is missing",
            )

        if not self._verify_secret(x_telegram_bot_api_secret_token):
            logger.warning("Invalid secret token for bot %s", bot_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid secret token",
            )

        bot = await self._resolve_bot(bot_id)
        if not bot:
            logger.warning("Bot %s not found, skipping update", bot_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bot not registered",
            )

        task = asyncio.create_task(self._feed_update(bot, update))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

        return Response(status_code=status.HTTP_200_OK)
