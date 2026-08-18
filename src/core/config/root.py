from functools import lru_cache

from pydantic import Field, SecretStr

from .base import BaseConfig
from .database import DatabaseConfig
from .rate_limit import RateLimitConfig
from .redis import RedisConfig
from .webhook import WebhookConfig


class Config(BaseConfig):
    log_level: str = "INFO"

    redis: RedisConfig = Field(default_factory=RedisConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    webhook: WebhookConfig = Field(default_factory=WebhookConfig)

    max_userbots_per_user: int = 1

    tg_token: SecretStr
    webhook_secret: SecretStr
    encryption_key: SecretStr

    proxy: str | None = None

    @property
    def webhook_base_url(self) -> str:
        return f"https://{self.webhook.domain.get_secret_value()}:{self.webhook.port}{self.webhook.path}"

    @classmethod
    @lru_cache
    def get(cls):
        return cls()
