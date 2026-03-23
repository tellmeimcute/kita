from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from database.models.abstract_model import AbstractModel


class DatabaseManager:
    def __init__(self, db_url) -> None:
        self.engine = create_async_engine(db_url, echo=False)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def start_dev(self):
        """Лучше не использовать. Нужно использовать алембик."""
        async with self.engine.begin() as conn:
            await conn.run_sync(AbstractModel.metadata.create_all)
