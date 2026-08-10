from dishka import AsyncContainer, make_async_container

from di import (
    BotProvider,
    DatabaseProvider,
    InfraProvider,
    RedisProvider,
    UtilsProvider,
)


def create_taskiq_container() -> AsyncContainer:
    return make_async_container(
        InfraProvider(),
        UtilsProvider(),
        BotProvider(),
        DatabaseProvider(),
        RedisProvider(),
    )
