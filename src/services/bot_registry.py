

import contextvars
from logging import getLogger
from aiogram import Bot


logger = getLogger("kita.bot_registry")

class BotRegistry:
    def __init__(self):
        self._storage: dict[int, Bot] = {}
        self._current_bot: contextvars.ContextVar[Bot | None] = contextvars.ContextVar(
            "_current_bot", default=None
        )

    def register(self, bot: Bot) -> None:
        self._storage[bot.id] = bot

        logger.info("Register bot_id %s", bot.id)

    def get(self, bot_id: int) -> Bot:
        return self._storage[bot_id]

    def get_current(self) -> Bot | None:
        return self._current_bot.get()

    def set_current(self, bot: Bot) -> contextvars.Token[Bot | None]:
        logger.debug("Set current bot_id %s for this task", bot.id)
        return self._current_bot.set(bot)

    def reset_current(self, token: contextvars.Token[Bot | None]) -> None:
        self._current_bot.reset(token)
