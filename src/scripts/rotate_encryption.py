import asyncio

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import Config
from core.cryptographer import Cryptographer

BATCH_SIZE = 100

_SELECT = text(
    "SELECT bot_id, token FROM userbot WHERE bot_id > :last_id ORDER BY bot_id LIMIT :limit"
)
_UPDATE = text("UPDATE userbot SET token = :token WHERE bot_id = :bot_id")


async def rotate(
    session_maker: async_sessionmaker[AsyncSession],
    cryptographer: Cryptographer,
    batch_size: int = BATCH_SIZE,
) -> int:
    last_id = 0
    updated = 0

    async with session_maker() as session:
        while True:
            rows = (
                await session.execute(_SELECT, {"last_id": last_id, "limit": batch_size})
            ).all()
            if not rows:
                break

            for bot_id, token in rows:
                if not cryptographer.need_rotation(token):
                    continue
                rotated = cryptographer.rotate(token)
                await session.execute(_UPDATE, {"bot_id": bot_id, "token": rotated})
                updated += 1

            await session.commit()
            last_id = rows[-1][0]
            if len(rows) < batch_size:
                break

    return updated


async def run(batch_size: int = BATCH_SIZE) -> int:
    config = Config.get()
    cryptographer = Cryptographer(config)

    engine: AsyncEngine = create_async_engine(config.database.db_url)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        return await rotate(session_maker, cryptographer, batch_size=batch_size)
    finally:
        await engine.dispose()


def main() -> None:
    updated = asyncio.run(run())
    logger.info("Rotated {} tokens", updated)


if __name__ == "__main__":
    main()
