from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.enums import ParseMode

from core.config import Config


class BotSessionFactory:
    """Builds Bot instances and owns the shared aiohttp session."""

    def __init__(
        self,
        config: Config,
        request_middlewares: Sequence[BaseRequestMiddleware] = (),
    ):
        self._proxy = config.proxy
        self._default = DefaultBotProperties(parse_mode=ParseMode.HTML)
        self._request_middlewares = tuple(request_middlewares)
        self._shared_session = self._make_session()

    def _make_session(self) -> AiohttpSession:
        session = AiohttpSession(proxy=self._proxy)
        for middleware in self._request_middlewares:
            session.middleware.register(middleware)
        return session

    def create(self, token: str) -> Bot:
        return Bot(token=token, session=self._shared_session, default=self._default)

    @asynccontextmanager
    async def temp_bot(self, token: str) -> AsyncGenerator[Bot]:
        bot = Bot(token=token, session=self._make_session(), default=self._default)
        try:
            yield bot
        finally:
            await bot.session.close()

    async def close(self) -> None:
        await self._shared_session.close()
