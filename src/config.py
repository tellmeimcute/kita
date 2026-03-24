from pydantic import BaseModel, SecretStr, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from redis.asyncio import Redis

class RuntimeConfig(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    channel_name: str
    bot_username: str
    bot_url: str


class Config(BaseSettings):
    TG_TOKEN: SecretStr
    DB_URL: str

    ADMIN_ID: int
    CHANNEL_ID: int
    PROXY: str | None = None

    # REDIS SETTINGS
    REDIS_HOST: str
    REDIS_PORT: int = Field(6379, ge=1, le=65535)
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    runtime_config: RuntimeConfig | None = None

    redis: Redis | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


config = Config()
