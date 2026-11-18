import hashlib
import hmac
import secrets

from cryptography.fernet import Fernet, InvalidToken

from core.config import Config

DEFAULT_VERSION = "v1"


class Cryptographer:
    def __init__(self, config: Config):
        self._config = config
        self._master_secret = self._config.webhook_secret.get_secret_value().encode("utf-8")

        self.version = DEFAULT_VERSION
        self.fernets: dict[str, Fernet] = {}
        for i, key in enumerate(config.encryption_keys):
            version, material = self._split_version(key.get_secret_value())
            self.fernets[version] = Fernet(material.encode("utf-8"))
            if i == 0:
                self.version = version

        if not self.fernets:
            raise ValueError("No encryption keys configured")

    @staticmethod
    def _split_version(value: str) -> tuple[str, str]:
        parts = value.split(":", 1)
        if len(parts) > 1 and parts[0].startswith("v"):
            return parts[0], parts[1]
        return DEFAULT_VERSION, value

    def _fernet(self, version: str) -> Fernet:
        fernet = self.fernets.get(version)
        if fernet is None:
            raise InvalidToken(f"No key for version {version}")
        return fernet

    def generate_bot_secret(self, bot_id: int):
        msg = str(bot_id).encode("utf-8")
        token_bytes = hmac.digest(self._master_secret, msg, hashlib.sha256)
        return token_bytes.hex()

    def verify_bot_secret(self, token: str, bot_id: int):
        expected = self.generate_bot_secret(bot_id)
        return secrets.compare_digest(token, expected)

    def encrypt(self, value: str) -> str:
        token = self._fernet(self.version).encrypt(value.encode("utf-8")).decode("utf-8")
        return f"{self.version}:{token}"

    def decrypt(self, value: str) -> str:
        version, payload = self._split_version(value)
        return self._fernet(version).decrypt(payload.encode("utf-8")).decode("utf-8")

    def need_rotation(self, value: str) -> bool:
        version, _ = self._split_version(value)
        return version != self.version

    def rotate(self, value: str) -> str:
        version, payload = self._split_version(value)
        plaintext = self._fernet(version).decrypt(payload.encode("utf-8")).decode("utf-8")
        return self.encrypt(plaintext)
