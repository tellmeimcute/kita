from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from config import Config

class DatabaseManager:
    def __init__(self, config: Config) -> None:
        db_url = self.get_url(config)
        
        self.engine = create_async_engine(
            db_url,
            pool_timeout=30,
            pool_recycle=1800,
            echo=False,
        )

        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    def get_url(self, config: Config):
        creds_kw = (
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_DB",
            "POSTGRES_HOST",
            "POSTGRES_PORT",
        )

        creds = config.model_dump(include=creds_kw)

        url = (
            "postgresql+asyncpg://"
            "{POSTGRES_USER}:{POSTGRES_PASSWORD}"
            "@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        ).format(**creds)

        return url