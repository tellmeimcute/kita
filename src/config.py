from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    TG_TOKEN: SecretStr
    DB_URL: str

    ADMIN_ID: int
    CHANNEL_ID: int
    
    channel_name: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


config = Config()
