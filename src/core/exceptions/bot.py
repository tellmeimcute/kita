from .base import KitaException


class BotNotRegisteredError(KitaException):
    def __init__(self, bot_id: int):
        self.bot_id = bot_id
        super().__init__(f"Bot {bot_id} is not registered in registry")
