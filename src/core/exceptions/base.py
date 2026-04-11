from aiogram.types import ReplyKeyboardMarkup


class KitaException(Exception):
    """Base Kita Exception"""
    def __init__(
        self,
        return_kb: ReplyKeyboardMarkup | None = None,
    ):
        self.return_kb = return_kb