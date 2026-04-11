
from pydantic import SecretStr, Field

from .base import BaseConfig
from .database import DatabaseConfig
from .redis import RedisConfig


class Config(BaseConfig):
    TG_TOKEN: SecretStr
    ADMIN_ID: int
    CHANNEL_ID: int

    redis: RedisConfig = Field(default_factory=RedisConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)

    PROXY: str | None = None