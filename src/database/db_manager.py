from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config import config
from database.models.abstract_model import AbstractModel


class DatabaseManager:
    def __init__(self) -> None:
        self.engine = create_async_engine(config.DB_URL, echo=False)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def start_dev(self):
        """Лучше не использовать. Нужно использовать алембик."""
        async with self.engine.begin() as conn:
            await conn.run_sync(AbstractModel.metadata.create_all)
