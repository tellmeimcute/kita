
from .i18n_base import KitaException, KitaExceptionI18nKwargs


class UserImmuneError(KitaException): ...

class SQLModelNotFoundError(KitaExceptionI18nKwargs):
    def __init__(self, target_id: int | None = None, **extra):
        self.target_id = target_id
        super().__init__(**extra)

class SQLSuggestionNotFoundError(SQLModelNotFoundError): ...

class SQLUserNotFoundError(SQLModelNotFoundError): ...