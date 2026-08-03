import hashlib
import hmac
import secrets

from cryptography.fernet import Fernet

from core.config import Config


class Cryptographer:
    def __init__(self, config: Config):
        self._config = config
        self._master_secret = self._config.webhook_secret.get_secret_value().encode("utf-8")

        self.fernet = Fernet(config.encryption_key.get_secret_value().encode("utf-8"))

    def generate_bot_secret(self, bot_id: int):
        msg = str(bot_id).encode("utf-8")
        token_bytes = hmac.digest(self._master_secret, msg, hashlib.sha256)
        return token_bytes.hex()

    def verify_bot_secret(self, token: str, bot_id: int):
        expected = self.generate_bot_secret(bot_id)
        return secrets.compare_digest(token, expected)

    def encrypt(self, value: str):
        return self.fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str):
        return self.fernet.decrypt(value.encode("utf-8")).decode("utf-8")
