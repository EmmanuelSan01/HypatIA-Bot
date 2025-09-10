import redis
import os

class RedisConversationStore:
    def __init__(self):
        self.client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            password=os.getenv("REDIS_PASSWORD", None),
            decode_responses=True
        )

    def get_conversation(self, user_id: str) -> str:
        return self.client.get(f"chat:{user_id}") or ""

    def set_conversation(self, user_id: str, conversation: str, expire_seconds: int = 86400):
        self.client.setex(f"chat:{user_id}", expire_seconds, conversation)

    def clear_conversation(self, user_id: str):
        self.client.delete(f"chat:{user_id}")
