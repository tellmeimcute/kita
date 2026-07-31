from pydantic import PostgresDsn, SecretStr

from .base import BaseConfig


class DatabaseConfig(BaseConfig, env_prefix="POSTGRES_"):
    user: str = "postgres"
    db: str = "kita"
    host: str = "localhost"
    port: int = 5432

    password: SecretStr

    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800

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
