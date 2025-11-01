import redis
from functools import lru_cache
from app.core.config import settings

@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    # Conexión síncrona (encaja con tu código actual)
    # Decodifica automáticamente a str
    return redis.from_url(settings.REDIS_URL, decode_responses=True)
