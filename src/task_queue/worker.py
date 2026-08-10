from dishka import AsyncContainer
from dishka.integrations.taskiq import setup_dishka as setup_dishka_taskiq
from taskiq_redis import RedisStreamBroker

from core.config import Config
from core.logging_config import setup_logging

from .broker import broker
from .container import create_taskiq_container
from .middlewares import BotContextMiddleware

config = Config.get()
setup_logging(config.log_level)


def worker() -> RedisStreamBroker:
    container = create_taskiq_container()
    setup_dishka_taskiq(container, broker)

    broker.add_dependency_context({AsyncContainer: container})
    broker.add_middlewares(BotContextMiddleware(container))

    return broker
