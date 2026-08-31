from interfaces import BotRegistryProtocol


class BaseService:
    REDIS_KEY_PART = "base_key"

    __slots__ = ("_bot_registry",)

    def __init__(self, bot_registry: BotRegistryProtocol):
        self._bot_registry = bot_registry

    @property
    def bot(self):
        return self._bot_registry.get_current()
