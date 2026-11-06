import contextvars
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from aiogram import Bot
from loguru import logger


class BotContext:
    """The bot this task works with, propagated through a contextvar."""

    def __init__(self):
        self._current: contextvars.ContextVar[Bot | None] = contextvars.ContextVar(
            "_current_bot", default=None
        )

    def current(self) -> Bot | None:
        return self._current.get()

    def set(self, bot: Bot) -> contextvars.Token[Bot | None]:
        logger.debug("Set current bot_id {} for this task", bot.id)
        return self._current.set(bot)

    def reset(self, token: contextvars.Token[Bot | None]) -> None:
        self._current.reset(token)

    @asynccontextmanager
    async def using(self, bot: Bot) -> AsyncGenerator[Bot]:
        token = self.set(bot)
        try:
            yield bot
        finally:
            self.reset(token)
