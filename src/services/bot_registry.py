import contextvars
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from loguru import logger

from core.config import Config


class BotRegistry:
    def __init__(self, config: Config):
        self._slaves_allowed_updates = []
        self._storage: dict[int, Bot] = {}

        self._session = AiohttpSession(proxy=config.proxy)
        self._bot_settings = {
            "session": self._session,
            "default": DefaultBotProperties(parse_mode=ParseMode.HTML),
        }

        self._current_bot: contextvars.ContextVar[Bot | None] = contextvars.ContextVar(
            "_current_bot", default=None
        )

    @property
    def bot_settings(self) -> dict:
        return self._bot_settings

    @property
    def allowed_updates(self) -> list[str]:
        return self._slaves_allowed_updates

    @allowed_updates.setter
    def allowed_updates(self, value):
        if not isinstance(value, list):
            raise ValueError("allowed updates should be list.")
        self._slaves_allowed_updates = value

    def register(self, bot: Bot) -> None:
        self._storage[bot.id] = bot

        logger.info("Register bot_id {}", bot.id)

    def get(self, bot_id: int) -> Bot:
        return self._storage[bot_id]

    def get_or_create(self, bot_id: int, token: str) -> Bot:
        cached = self._storage.get(bot_id)
        if cached and cached.token == token:
            return cached

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
        logger.debug("Set current bot_id {} for this task", bot.id)
        return self._current_bot.set(bot)

    def reset_current(self, token: contextvars.Token[Bot | None]) -> None:
        self._current_bot.reset(token)

    @asynccontextmanager
    async def with_bot(self, bot_or_id: Bot | int, token: str | None = None):
        if isinstance(bot_or_id, Bot):
            bot = bot_or_id
        else:
            bot = self.get(bot_or_id) if not token else self.get_or_create(bot_or_id, token)

        prev_token = self.set_current(bot)

        try:
            yield bot
        finally:
            self.reset_current(prev_token)

    async def close(self):
        await self._session.close()
