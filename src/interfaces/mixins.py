from .bot import BotContextProtocol


class BotMixin:
    __slots__ = ("_bot_context",)

    def __init__(self, bot_context: BotContextProtocol):
        self._bot_context = bot_context

    @property
    def bot(self):
        return self._bot_context.get_current()
