
from pydantic import SecretStr, Field, RedisDsn
from .base import BaseConfig


class RedisConfig(BaseConfig, env_prefix="REDIS_"):
    host: str = "localhost"
    port: int = Field(6379, ge=1, le=65535)
    db: str = "0"
    password: SecretStr | None = None

    @property
    def redis_url(self) -> str:
        return RedisDsn.build(
            scheme="redis",
            password=self.password.get_secret_value() if self.password else None,
            host=self.host,
            port=self.port,
            path=self.db,
        ).unicode_string()