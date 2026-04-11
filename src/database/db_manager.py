from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from core.config import Config

class DatabaseManager:
    def __init__(self, config: Config) -> None:
        self.engine = create_async_engine(
            config.database.db_url,
            pool_timeout=30,
            pool_recycle=1800,
            echo=False,
        )

        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)