
from pydantic import SecretStr, Field
from functools import lru_cache

from .base import BaseConfig
from .database import DatabaseConfig
from .redis import RedisConfig
from .rate_limit import RateLimitConfig

class Config(BaseConfig):
    tg_token: SecretStr
    admin_id: int

    log_level: str = "INFO"

    redis: RedisConfig = Field(default_factory=RedisConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)

    domain: SecretStr
    webhook_port: int = 443
    webhook_secret: SecretStr
    webhook_path: str = "/webhook"

    encryption_key: SecretStr

    PROXY: str | None = None

    @property
    def webhook_base_url(self) -> str:
        return f"https://{self.domain.get_secret_value()}:{self.webhook_port}{self.webhook_path}"

    @classmethod
    @lru_cache
    def get(cls):
        return cls()
    