import contextvars
from collections import OrderedDict
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from loguru import logger

from core.config import Config
from core.exceptions import BotNotRegisteredError


class BotRegistry:
    def __init__(self, config: Config):
        self._slaves_allowed_updates = []
        self._storage: OrderedDict[int, Bot] = OrderedDict()

        self._proxy = config.proxy
        self._default = DefaultBotProperties(parse_mode=ParseMode.HTML)

        self._shared_session = AiohttpSession(proxy=self._proxy)

        self._current_bot: contextvars.ContextVar[Bot | None] = contextvars.ContextVar(
            "_current_bot", default=None
        )

        self.cache_max_size = config.bot_cache_max_size

    @asynccontextmanager
    async def temp_bot(self, token: str) -> AsyncGenerator[Bot]:
        bot = Bot(token=token, session=AiohttpSession(proxy=self._proxy), default=self._default)
        try:
            yield bot
        finally:
            await bot.session.close()

    @property
    def allowed_updates(self) -> list[str]:
        return self._slaves_allowed_updates

    @allowed_updates.setter
    def allowed_updates(self, value):
        if not isinstance(value, list):
            raise ValueError("allowed updates should be list.")
        self._slaves_allowed_updates = value

    def _upsert(self, bot: Bot) -> None:
        self._storage[bot.id] = bot
        self._storage.move_to_end(bot.id)
        if len(self._storage) > self.cache_max_size:
            oldest_id, _ = self._storage.popitem(last=False)
            logger.debug("Bot {} removed from cache", oldest_id)

    def register(self, bot: Bot) -> None:
        self._upsert(bot)
        logger.info("Cached bot {} instance", bot.id)

    def get(self, bot_id: int) -> Bot | None:
        if bot_id in self._storage:
            self._storage.move_to_end(bot_id)
            return self._storage[bot_id]

    def get_or_create(self, bot_id: int, token: str) -> Bot:
        cached = self.get(bot_id)
        if cached and cached.token == token:
            return cached

        bot = Bot(token=token, session=self._shared_session, default=self._default)
        self._upsert(bot)

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
        elif token is not None:
            bot = self.get_or_create(bot_or_id, token)
        else:
            bot = self.get(bot_or_id)
            if bot is None:
                raise BotNotRegisteredError(bot_or_id)

        prev_token = self.set_current(bot)

        try:
            yield bot
        finally:
            self.reset_current(prev_token)

    async def close(self):
        await self._shared_session.close()
