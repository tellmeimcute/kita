from abc import ABC

from aiogram import Bot
from database.redis import RedisKey, KitaKeyBuilder
from interfaces import BotRegistryProtocol

class BaseService(ABC):
    REDIS_KEY_PART = "base_key"

    __slots__ = (
        "_bot_registry",
        "_key_builder",
        "_bot",
    )

    def __init__(
        self,
        bot_registry: BotRegistryProtocol,
        key_builder: KitaKeyBuilder | None = None
    ):
        self._bot_registry = bot_registry
        self._bot = None

        if key_builder:
            self._key_builder = key_builder
        else:
            self._key_builder = KitaKeyBuilder()

    @property
    def bot(self):
        if self._bot:
            return self._bot
        return self._bot_registry.get_current()

    def assign_bot(self, bot: Bot):
        self._bot = bot

    def _get_key(self, user_id: int):
        redis_key = RedisKey(bot_id=self.bot.id, user_id=user_id)
        return self._key_builder.build(redis_key, self.REDIS_KEY_PART)
    