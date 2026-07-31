
from collections.abc import AsyncIterable
from logging import getLogger

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import Config

logger = getLogger("kita.providers")


class DatabaseProvider(Provider):

    @provide(scope=Scope.APP)
    async def get_async_engine(self, config: Config) -> AsyncIterable[AsyncEngine]:
        logger.info("Initializing AsyncEngine instance")
        engine = create_async_engine(
            config.database.db_url,
            pool_size=config.database.pool_size,
            max_overflow=config.database.max_overflow,
            pool_timeout=config.database.pool_timeout,
            pool_recycle=config.database.pool_recycle,
            echo=config.database.echo,
        )

        yield engine

        logger.debug("Disposing AsyncEngine")
        await engine.dispose()

    @provide(scope=Scope.APP)
    def get_session_maker(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        logger.info("Initializing async_sessionmaker instance")
        return async_sessionmaker(engine, expire_on_commit=False)

    @provide(scope=Scope.REQUEST)
    async def get_session(self, session_maker: async_sessionmaker[AsyncSession]) -> AsyncIterable[AsyncSession]:
        logger.debug("Initializing AsyncSession instance")
        async with session_maker() as session:
            yield session


