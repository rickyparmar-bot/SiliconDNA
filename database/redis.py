"""SiliconDNA Database Module - Redis Transient Caching"""

import logging
import json
import asyncio
from typing import Optional, Any, List
import redis.asyncio as aioredis
from datetime import timedelta


logger = logging.getLogger("silicon_dna.redis")


class RedisManager:
    """
    Async Redis connection manager for hyper-fast transient caching.
    Handles session states, rate limiting, and configuration caching.
    """

    def __init__(
        self,
        host: str,
        port: int = 6379,
        db: int = 0,
        decode_responses: bool = True,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        max_connections: int = 50,
    ):
        self.host = host
        self.port = port
        self.db = db
        self.decode_responses = decode_responses
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.max_connections = max_connections
        self.client: Optional[aioredis.Redis] = None
        self._connected = False
        self._lock = asyncio.Lock()

    async def connect(self) -> bool:
        """Establish async Redis connection."""
        async with self._lock:
            if self._connected and self.client:
                return True

            try:
                self.client = aioredis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    decode_responses=self.decode_responses,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_connect_timeout,
                    max_connections=self.max_connections,
                )
                await self.client.ping()
                self._connected = True
                logger.info(f"Connected to Redis: {self.host}:{self.port}")
                return True
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                self._connected = False
                raise

    async def disconnect(self):
        """Close Redis connection gracefully."""
        async with self._lock:
            if self.client:
                await self.client.close()
                self._connected = False
                logger.info("Redis disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connected and self.client is not None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        nx: bool = False,
    ):
        """
        Set a key with optional TTL (in seconds).

        Args:
            key: Redis key
            value: Value to store
            ttl: Time to live in seconds (default: 1 hour)
            nx: Only set if key doesn't exist
        """
        if not self.is_connected:
            logger.warning("Redis not connected, skipping set operation")
            return False

        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, str):
                value = str(value)

            if nx:
                result = await self.client.set(key, value, ex=ttl, nx=True)
                return result is not None
            else:
                await self.client.set(key, value, ex=ttl)
                return True
        except Exception as e:
            logger.error(f"Redis set failed for key {key}: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get a key's value."""
        if not self.is_connected:
            return None

        try:
            value = await self.client.get(key)
            if value:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return None
        except Exception as e:
            logger.error(f"Redis get failed for key {key}: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key."""
        if not self.is_connected:
            return False

        try:
            result = await self.client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete failed for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.is_connected:
            return False

        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists check failed for key {key}: {e}")
            return False

    async def incr(self, key: str) -> int:
        """Increment a counter."""
        if not self.is_connected:
            return 0

        try:
            return await self.client.incr(key)
        except Exception as e:
            logger.error(f"Redis incr failed for key {key}: {e}")
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on existing key."""
        if not self.is_connected:
            return False

        try:
            return await self.client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis expire failed for key {key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """Get remaining TTL for a key."""
        if not self.is_connected:
            return -2

        try:
            return await self.client.ttl(key)
        except Exception as e:
            logger.error(f"Redis ttl failed for key {key}: {e}")
            return -2

    async def get_many(self, keys: List[str]) -> dict:
        """Get multiple keys at once."""
        if not self.is_connected:
            return {}

        try:
            values = await self.client.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value:
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        result[key] = value
            return result
        except Exception as e:
            logger.error(f"Redis mget failed: {e}")
            return {}

    async def set_session(
        self,
        session_id: str,
        data: dict,
        ttl: int = 3600,
    ) -> bool:
        """Store session data with structured key."""
        key = f"session:{session_id}"
        return await self.set(key, data, ttl)

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve session data."""
        key = f"session:{session_id}"
        return await self.get(key)

    async def delete_session(self, session_id: str) -> bool:
        """Delete session data."""
        key = f"session:{session_id}"
        return await self.delete(key)

    async def rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int]:
        """
        Check and update rate limit.

        Returns:
            (allowed: bool, remaining: int)
        """
        if not self.is_connected:
            return True, limit

        try:
            current = await self.client.incr(key)
            if current == 1:
                await self.client.expire(key, window_seconds)

            remaining = max(0, limit - current)
            allowed = current <= limit
            return allowed, remaining
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True, limit

    async def cache_config(
        self,
        config_key: str,
        config_value: Any,
        ttl: int = 86400,
    ) -> bool:
        """Cache configuration with longer TTL."""
        key = f"config:{config_key}"
        return await self.set(key, config_value, ttl)

    async def get_cached_config(self, config_key: str) -> Optional[Any]:
        """Retrieve cached configuration."""
        key = f"config:{config_key}"
        return await self.get(key)

    async def flush_db(self):
        """Flush current database (use with caution!)."""
        if not self.is_connected:
            return

        try:
            await self.client.flushdb()
            logger.warning("Redis database flushed")
        except Exception as e:
            logger.error(f"Redis flush failed: {e}")
