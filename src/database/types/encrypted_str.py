from sqlalchemy import String, TypeDecorator

from core.config import Config
from core.cryptographer import Cryptographer


class EncryptedString(TypeDecorator):
    impl = String
    cache_ok = True

    def __init__(self, length: int = 255, *args, **kwargs):
        super().__init__(length, *args, **kwargs)
        self._crypto: Cryptographer | None = None

    @property
    def crypto(self) -> Cryptographer:
        if self._crypto is None:
            self._crypto = Cryptographer(Config.get())
        return self._crypto

    def process_bind_param(self, value: str, dialect):
        if value is None:
            return value
        return self.crypto.encrypt(value)

    def process_result_value(self, value: str, dialect):
        if value is None:
            return value
        return self.crypto.decrypt(value)
