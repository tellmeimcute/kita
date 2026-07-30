from sqlalchemy import TypeDecorator, String
from cryptography.fernet import Fernet
from core.config import Config


class EncryptedString(TypeDecorator):

    impl = String 
    cache_ok = True

    def __init__(self, length: int = 255, *args, **kwargs):
        super().__init__(length, *args, **kwargs)
        self._fernet: Fernet | None = None

    @property
    def fernet(self) -> Fernet:
        if self._fernet is None:
            key_bytes = Config.get().encryption_key.get_secret_value().encode("utf-8")
            self._fernet = Fernet(key_bytes)
        return self._fernet

    def process_bind_param(self, value: str, dialect):
        if value is None:
            return value
        return self.fernet.encrypt(value.encode("utf-8")).decode("utf-8")
    
    def process_result_value(self, value: str, dialect):
        if value is None:
            return value
        return self.fernet.decrypt(value.encode("utf-8")).decode("utf-8")
