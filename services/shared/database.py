"""
Database utilities for microservices
Provides database connections and utilities
"""

import redis
import logging
from typing import Optional, Dict, Any
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RedisManager:
    """Redis connection manager"""
    
    def __init__(self, host: str = "redis", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        self._client = None
    
    @property
    def client(self) -> redis.Redis:
        """Get Redis client with connection pooling"""
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
        return self._client
    
    def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        try:
            return self.client.get(key)
        except redis.RedisError as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in Redis"""
        try:
            return self.client.set(key, value, ex=ex)
        except redis.RedisError as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            return bool(self.client.delete(key))
        except redis.RedisError as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        try:
            return bool(self.client.exists(key))
        except redis.RedisError as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment value in Redis"""
        try:
            return self.client.incr(key, amount)
        except redis.RedisError as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
            return None
    
    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for key"""
        try:
            return bool(self.client.expire(key, seconds))
        except redis.RedisError as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False
    
    def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field value"""
        try:
            return self.client.hget(name, key)
        except redis.RedisError as e:
            logger.error(f"Redis HGET error for {name}:{key}: {e}")
            return None
    
    def hset(self, name: str, key: str, value: str) -> bool:
        """Set hash field value"""
        try:
            return bool(self.client.hset(name, key, value))
        except redis.RedisError as e:
            logger.error(f"Redis HSET error for {name}:{key}: {e}")
            return False
    
    def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields"""
        try:
            return self.client.hgetall(name)
        except redis.RedisError as e:
            logger.error(f"Redis HGETALL error for {name}: {e}")
            return {}
    
    def publish(self, channel: str, message: str) -> bool:
        """Publish message to Redis channel"""
        try:
            return bool(self.client.publish(channel, message))
        except redis.RedisError as e:
            logger.error(f"Redis PUBLISH error for channel {channel}: {e}")
            return False
    
    def health_check(self) -> bool:
        """Check Redis health"""
        try:
            return self.client.ping()
        except redis.RedisError as e:
            logger.error(f"Redis health check failed: {e}")
            return False

class CacheManager:
    """High-level cache management"""
    
    def __init__(self, redis_manager: RedisManager, default_ttl: int = 3600):
        self.redis = redis_manager
        self.default_ttl = default_ttl
    
    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON object from cache"""
        value = self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON for key {key}")
        return None
    
    def set_json(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set JSON object in cache"""
        if ttl is None:
            ttl = self.default_ttl
        
        try:
            json_value = json.dumps(value, default=str)
            return self.redis.set(key, json_value, ex=ttl)
        except (TypeError, json.JSONEncodeError) as e:
            logger.error(f"Failed to encode JSON for key {key}: {e}")
            return False
    
    def get_or_set(self, key: str, factory_func, ttl: Optional[int] = None) -> Any:
        """Get from cache or set using factory function"""
        value = self.get_json(key)
        if value is not None:
            return value
        
        # Generate new value
        new_value = factory_func()
        if new_value is not None:
            self.set_json(key, new_value, ttl)
        
        return new_value
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        count = 0
        try:
            for key in self.redis.client.scan_iter(match=pattern):
                if self.redis.delete(key):
                    count += 1
        except redis.RedisError as e:
            logger.error(f"Error invalidating pattern {pattern}: {e}")
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            info = self.redis.client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                )
            }
        except redis.RedisError as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate"""
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0

# Global instances (to be initialized by each service)
redis_manager = None
cache_manager = None

def init_database(redis_host: str = "redis", redis_port: int = 6379, default_ttl: int = 3600):
    """Initialize database connections"""
    global redis_manager, cache_manager
    
    redis_manager = RedisManager(host=redis_host, port=redis_port)
    cache_manager = CacheManager(redis_manager, default_ttl)
    
    logger.info("Database connections initialized")
    
    return redis_manager, cache_manager
