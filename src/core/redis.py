"""Redis connection and pub/sub utilities for real-time updates."""

import os
import redis
from typing import Optional


class RedisClient:
    """Singleton Redis client for pub/sub operations."""

    _instance: Optional[redis.Redis] = None
    _pubsub: Optional[redis.client.PubSub] = None

    @classmethod
    def get_client(cls) -> redis.Redis:
        """Get or create Redis client instance."""
        if cls._instance is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            cls._instance = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
        return cls._instance

    @classmethod
    def get_pubsub(cls) -> redis.client.PubSub:
        """Get or create Redis pub/sub instance."""
        if cls._pubsub is None:
            client = cls.get_client()
            cls._pubsub = client.pubsub()
        return cls._pubsub

    @classmethod
    def close(cls):
        """Close Redis connections."""
        if cls._pubsub:
            cls._pubsub.close()
            cls._pubsub = None
        if cls._instance:
            cls._instance.close()
            cls._instance = None


def get_redis_client() -> redis.Redis:
    """FastAPI dependency for Redis client."""
    return RedisClient.get_client()
