
from aiogram.types import ReplyKeyboardMarkup


class KitaException(Exception):
    def __init__(
        self,
        return_kb: ReplyKeyboardMarkup | None = None,
    ):
        self.return_kb = return_kb

class KitaExceptionI18nKwargs(KitaException):
    def __init__(
        self,
        i18n_kwargs: dict | None = None,
        **extra,
    ):
        self.i18n_kwargs = i18n_kwargs
        super().__init__(**extra)

class UserImmuneError(KitaException):
    pass

class KitaValidationError(KitaExceptionI18nKwargs):
    def __init__(
        self,
        pydantic_exc: Exception,
        **extra,
    ):
        self.pydantic_exc = pydantic_exc
        super().__init__(**extra)

class SQLModelNotFoundError(KitaExceptionI18nKwargs):
    def __init__(
        self,
        target_id: int | None = None,
        **extra,
    ):
        self.target_id = target_id

        super().__init__(**extra)

class SQLSuggestionNotFoundError(SQLModelNotFoundError):
    pass

class SQLUserNotFoundError(SQLModelNotFoundError):
    pass