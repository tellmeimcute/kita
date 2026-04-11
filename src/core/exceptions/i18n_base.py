from .base import KitaException


class KitaExceptionI18nKwargs(KitaException):
    """Base Kita Exception with optional i18n_kwargs"""
    def __init__(
        self,
        i18n_kwargs: dict | None = None,
        **extra,
    ):
        self.i18n_kwargs = i18n_kwargs
        super().__init__(**extra)