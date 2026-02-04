from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


# class Config(BaseSettings):
#     TG_TOKEN: SecretStr = "6258307300:AAEidlYlJc92D2O0Uo5bz9at8hH5ccm98tM"
#     DB_URL: str = "sqlite+aiosqlite:///database.db"


class Config(BaseSettings):
    TG_TOKEN: SecretStr
    DB_URL: str

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )


config = Config()
