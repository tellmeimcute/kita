

import contextvars
from logging import getLogger

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from core.config import Config

logger = getLogger("kita.bot_registry")

class BotRegistry:
    def __init__(self, config: Config):
        self._storage: dict[int, Bot] = {}

        self._session = AiohttpSession(proxy=config.PROXY)
        self._bot_settings = {
            "session": self._session,
            "default": DefaultBotProperties(parse_mode=ParseMode.HTML),
        }

        self._current_bot: contextvars.ContextVar[Bot | None] = contextvars.ContextVar(
            "_current_bot", default=None
        )

    def register(self, bot: Bot) -> None:
        self._storage[bot.id] = bot

        logger.info("Register bot_id %s", bot.id)

    def get(self, bot_id: int) -> Bot:
        return self._storage[bot_id]

    def get_or_create(self, bot_id: int, token: str) -> Bot:
        bot = self._storage.get(bot_id)
        if bot:
            return bot

        bot = Bot(token=token, **self._bot_settings)
        self._storage[bot.id] = bot

        return bot

    def remove(self, bot_id: int):
        self._storage.pop(bot_id, None)

    def get_all(self) -> list[Bot]:
        return list(self._storage.values())

    def get_current(self) -> Bot | None:
        return self._current_bot.get()

    def set_current(self, bot: Bot) -> contextvars.Token[Bot | None]:
        logger.debug("Set current bot_id %s for this task", bot.id)
        return self._current_bot.set(bot)

    def reset_current(self, token: contextvars.Token[Bot | None]) -> None:
        self._current_bot.reset(token)

    async def close(self):
        await self._session.close()