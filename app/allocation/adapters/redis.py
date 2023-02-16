# types-redis의 Generic 타입 이슈로 인해 아래와 같이 사용
# https://github.com/python/typeshed/issues/8242

from typing import TYPE_CHECKING

from redis.asyncio.client import Redis as Redis_

from app.config import config

if TYPE_CHECKING:
    Redis = Redis_[bytes]
else:
    Redis = Redis_


__all__ = ["Redis"]

redis = Redis.from_url(config.REDIS_DSN)
