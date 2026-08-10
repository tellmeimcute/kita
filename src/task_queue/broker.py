from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from core.config import Config


def create_broker(config: Config):
    result_backend = RedisAsyncResultBackend(
        redis_url=config.redis.redis_url,
        keep_results=False,
        result_ex_time=3600,
    )

    return RedisStreamBroker(
        url=config.redis.redis_url,
        maxlen=1000,
    ).with_result_backend(result_backend)


broker = create_broker(Config.get())
