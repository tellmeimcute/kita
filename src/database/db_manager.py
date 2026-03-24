from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from database.models.abstract_model import AbstractModel


class DatabaseManager:
    def __init__(self, db_url) -> None:
        self.engine = create_async_engine(db_url, echo=False)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)