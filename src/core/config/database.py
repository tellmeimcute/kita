from pydantic import SecretStr, PostgresDsn
from .base import BaseConfig


class DatabaseConfig(BaseConfig, env_prefix="POSTGRES_"):
    user: str = "postgres"
    db: str = "kita"
    host: str = "localhost"
    port: int = 5432

    password: SecretStr

    @property
    def db_url(self) -> str:
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.user,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            path=self.db,
        ).unicode_string()
