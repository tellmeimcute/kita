from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeConfig(BaseModel):
    channel_name: str
    bot_username: str
    bot_url: str


class Config(BaseSettings):
    TG_TOKEN: SecretStr
    DB_URL: str

    ADMIN_ID: int
    CHANNEL_ID: int
    PROXY: str | None = None

    runtime_config: RuntimeConfig | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


config = Config()
