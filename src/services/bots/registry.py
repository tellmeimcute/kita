import contextvars
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.client.session.middlewares.base import BaseRequestMiddleware

from core.config import Config
from core.exceptions import BotNotRegisteredError

from .cache import BotCache
from .context import BotContext
from .session import BotSessionFactory


class BotRegistry:
    
    def __init__(
        self,
        config: Config,
        request_middlewares: Sequence[BaseRequestMiddleware] = (),
    ):
        self._slaves_allowed_updates: list[str] = []
        self._sessions = BotSessionFactory(config, request_middlewares)
        self._cache = BotCache(config.bot_cache_max_size)
        self._context = BotContext()

    @asynccontextmanager
    async def temp_bot(self, token: str) -> AsyncGenerator[Bot]:
        async with self._sessions.temp_bot(token) as bot:
            yield bot

    @property
    def allowed_updates(self) -> list[str]:
        return self._slaves_allowed_updates

    @allowed_updates.setter
    def allowed_updates(self, value):
        if not isinstance(value, list):
            raise ValueError("allowed updates should be list.")
        self._slaves_allowed_updates = value

    def get_or_create(self, bot_id: int, token: str) -> Bot:
        cached = self._cache.get(bot_id)
        if cached and cached.token == token:
            return cached

        bot = self._sessions.create(token)
        self._cache.put(bot)

        return bot

    def remove(self, bot_id: int) -> None:
        self._cache.remove(bot_id)

    def get_current(self) -> Bot | None:
        return self._context.current()

    def set_current(self, bot: Bot) -> contextvars.Token[Bot | None]:
        return self._context.set(bot)

    def reset_current(self, token: contextvars.Token[Bot | None]) -> None:
        self._context.reset(token)

    @asynccontextmanager
    async def with_bot(self, bot_or_id: Bot | int, token: str | None = None):
        if isinstance(bot_or_id, Bot):
            bot = bot_or_id
        elif token is not None:
            bot = self.get_or_create(bot_or_id, token)
        else:
            bot = self._cache.get(bot_or_id)
            if bot is None:
                raise BotNotRegisteredError(bot_or_id)

        prev_token = self.set_current(bot)

        try:
            yield bot
        finally:
            self.reset_current(prev_token)

    async def close(self) -> None:
        await self._sessions.close()
