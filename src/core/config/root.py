from functools import lru_cache

from pydantic import Field, SecretStr

from .api_rate_limit import ApiRateLimitConfig
from .base import BaseConfig
from .database import DatabaseConfig
from .redis import RedisConfig
from .user_rate_limit import UserRateLimitConfig
from .webhook import WebhookConfig


class Config(BaseConfig):
    log_level: str = "INFO"

    redis: RedisConfig = Field(default_factory=RedisConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    user_rate_limit: UserRateLimitConfig = Field(default_factory=UserRateLimitConfig)
    api_rate_limit: ApiRateLimitConfig = Field(default_factory=ApiRateLimitConfig)
    webhook: WebhookConfig = Field(default_factory=WebhookConfig)

    max_userbots_per_user: int = 1
    bot_cache_max_size: int = 50

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
