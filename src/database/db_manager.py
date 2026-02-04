from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.models.abstract_model import AbstractModel
from config import config


class DatabaseManager:
    def __init__(self) -> None:
        self.engine = create_async_engine(config.DB_URL, echo=True)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def start_dev(self):
        """Лучше не использовать. Нужно использовать алембик."""
        async with self.engine.begin() as conn:
            await conn.run_sync(AbstractModel.metadata.create_all)
