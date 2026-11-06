from collections import OrderedDict

from aiogram import Bot
from loguru import logger


class BotCache:
    """LRU store of Bot instances keyed by bot id."""

    def __init__(self, max_size: int):
        self._max_size = max_size
        self._storage: OrderedDict[int, Bot] = OrderedDict()

    def get(self, bot_id: int) -> Bot | None:
        if bot_id not in self._storage:
            return None

        self._storage.move_to_end(bot_id)
        return self._storage[bot_id]

    def put(self, bot: Bot) -> None:
        self._storage[bot.id] = bot
        self._storage.move_to_end(bot.id)

        if len(self._storage) > self._max_size:
            oldest_id, _ = self._storage.popitem(last=False)
            logger.debug("Bot {} removed from cache", oldest_id)

    def remove(self, bot_id: int) -> None:
        self._storage.pop(bot_id, None)

    def all(self) -> list[Bot]:
        return list(self._storage.values())
