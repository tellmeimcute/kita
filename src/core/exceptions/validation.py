
from .i18n_base import KitaExceptionI18nKwargs

class KitaValidationError(KitaExceptionI18nKwargs):
    def __init__(self, pydantic_exc: Exception, **extra):
        self.pydantic_exc = pydantic_exc
        super().__init__(**extra)