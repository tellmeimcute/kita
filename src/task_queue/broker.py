from functools import cache

from taskiq.serializers import ORJSONSerializer
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from core.config.redis import RedisConfig


def create_broker(redis_url: str) -> RedisStreamBroker:
    result_backend = RedisAsyncResultBackend(
        redis_url=redis_url,
        keep_results=False,
        result_ex_time=3600,
        serializer=ORJSONSerializer(),
    )

    return RedisStreamBroker(
        url=redis_url,
        maxlen=1000,
    ).with_result_backend(result_backend)


@cache
def get_broker() -> RedisStreamBroker:
    return create_broker(RedisConfig().redis_url)
