from pydantic import BaseModel, SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from redis.asyncio import Redis

class RuntimeConfig(BaseModel):
    channel_name: str
    bot_username: str
    bot_url: str


class Config(BaseSettings):
    TG_TOKEN: SecretStr
    ADMIN_ID: int
    CHANNEL_ID: int

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = Field(6379, ge=1, le=65535)
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    POSTGRES_USER: str = "postgres"
    POSTGRES_DB: str = "kita"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_PASSWORD: str

    PROXY: str | None = None

    runtime_config: RuntimeConfig | None = None
    redis: Redis | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


config = Config()
