
from aiogram.types import ReplyKeyboardMarkup


class KitaException(Exception):
    def __init__(
        self,
        return_kb: ReplyKeyboardMarkup | None = None,
    ):
        self.return_kb = return_kb

class UserImmuneError(KitaException):
    pass

class SQLModelNotFoundError(KitaException):
    def __init__(
        self,
        target_id: int | None = None,
        i18n_kwargs: dict | None = None,
        **extra,
    ):
        self.target_id = target_id
        self.i18n_kwargs = i18n_kwargs

        super().__init__(**extra)

class SQLSuggestionNotFoundError(SQLModelNotFoundError):
    pass

class SQLUserNotFoundError(SQLModelNotFoundError):
    pass