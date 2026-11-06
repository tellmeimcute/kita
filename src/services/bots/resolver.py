from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from aiogram import Bot

from core.exceptions import BotNotRegisteredError
from interfaces import BotContextProtocol, BotSessionProtocol

from .cache import BotCache


class BotResolver:
    """Bots by id: a cached instance when the token matches, otherwise a new one."""

    def __init__(self, sessions: BotSessionProtocol, cache: BotCache, context: BotContextProtocol):
        self._sessions = sessions
        self._cache = cache
        self._context = context

    def get_or_create(self, bot_id: int, token: str) -> Bot:
        cached = self._cache.get(bot_id)
        if cached and cached.token == token:
            return cached

        bot = self._sessions.create(token)
        if bot.id != bot_id:
            raise ValueError(f"Token belongs to bot {bot.id}, not to bot {bot_id}")

        self._cache.put(bot)
        return bot

    def remove(self, bot_id: int) -> None:
        self._cache.remove(bot_id)

    def temp_bot(self, token: str) -> AbstractAsyncContextManager[Bot]:
        return self._sessions.temp_bot(token)

    @asynccontextmanager
    async def with_bot(
        self, bot_or_id: Bot | int, /, *, token: str | None = None
    ) -> AsyncGenerator[Bot]:
        if isinstance(bot_or_id, Bot):
            bot = bot_or_id
        elif token is not None:
            bot = self.get_or_create(bot_or_id, token)
        else:
            bot = self._cache.get(bot_or_id)
            if bot is None:
                raise BotNotRegisteredError(bot_or_id)

        async with self._context.using(bot):
            yield bot
