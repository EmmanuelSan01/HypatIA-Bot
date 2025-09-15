import redis
import os

class RedisCache:
    def __init__(self):
        self.client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            password=os.getenv("REDIS_PASSWORD", None),
            decode_responses=True
        )

    def get(self, key: str):
        return self.client.get(key)

    def set(self, key: str, value, expire_seconds: int = 3600):
        self.client.setex(key, expire_seconds, value)

    def delete(self, key: str):
        self.client.delete(key)
