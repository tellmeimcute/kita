import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

RACE_WINDOW = 0.05


async def run_in_parallel(
    session_maker: async_sessionmaker[AsyncSession],
    service_factory: Callable[[AsyncSession], Any],
    action: Callable[[Any], Awaitable[Any]],
) -> list[Any]:
    first_session = session_maker()
    second_session = session_maker()

    first_written = asyncio.Event()
    second_inserting = asyncio.Event()

    async def first_request():
        async with first_session.begin():
            try:
                await action(service_factory(first_session))
            finally:
                first_written.set()

            await second_inserting.wait()
            await asyncio.sleep(RACE_WINDOW)

    async def second_request():
        await first_written.wait()
        second_inserting.set()

        async with second_session.begin():
            return await action(service_factory(second_session))

    try:
        return await asyncio.gather(first_request(), second_request(), return_exceptions=True)
    finally:
        await first_session.close()
        await second_session.close()
