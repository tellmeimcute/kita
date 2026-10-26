from dishka import AsyncContainer, make_async_container

from di import (
    BotProvider,
    ConfigProvider,
    DatabaseProvider,
    RedisProvider,
    RepositoryProvider,
    ServiceProvider,
    UseCaseProvider,
    UtilsProvider,
)


def create_taskiq_container() -> AsyncContainer:
    return make_async_container(
        ConfigProvider(),
        RepositoryProvider(),
        ServiceProvider(),
        UseCaseProvider(),
        UtilsProvider(),
        BotProvider(),
        DatabaseProvider(),
        RedisProvider(),
    )
