
from pydantic import SecretStr, Field

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

    webhook_secret: SecretStr
    webhook_path: str = "/webhook"

    PROXY: str | None = None

    @property
    def webhook_base_url(self) -> str:
        return f"https://{self.domain.get_secret_value()}{self.webhook_path}"

    @classmethod
    def get(cls):
        return cls()
    