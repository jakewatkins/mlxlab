"""
Response caching for MCP Host.

Implements TTL-based caching with LRU eviction for resource and prompt responses.
"""

import asyncio
import time
from collections import OrderedDict
from typing import Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Cache:
    """TTL-based cache with LRU eviction."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize the cache.
        
        Args:
            max_size: Maximum number of cache entries
            default_ttl: Default TTL in seconds (default: 5 minutes)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def start_cleanup(self) -> None:
        """Start periodic cleanup of expired entries."""
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self) -> None:
        """Periodically clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self.cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
    
    def stop_cleanup(self) -> None:
        """Stop the cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # Check if expired
        age = time.time() - entry["created_at"]
        if age > entry["ttl"]:
            # Expired - remove it
            del self._cache[key]
            logger.debug(f"Cache entry expired: {key}")
            return None
        
        # Move to end (LRU)
        self._cache.move_to_end(key)
        
        logger.debug(f"Cache hit: {key}")
        return entry["value"]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if not specified)
        """
        if ttl is None:
            ttl = self.default_ttl
        
        # Check size limit and evict if needed
        if len(self._cache) >= self.max_size and key not in self._cache:
            # Remove oldest entry (LRU)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.debug(f"Cache eviction (LRU): {oldest_key}")
        
        # Add/update entry
        self._cache[key] = {
            "value": value,
            "created_at": time.time(),
            "ttl": ttl
        }
        
        # Move to end
        self._cache.move_to_end(key)
        
        logger.debug(f"Cache set: {key} (ttl={ttl}s)")
    
    def invalidate(self, key: str) -> None:
        """
        Invalidate a specific cache entry.
        
        Args:
            key: Cache key to invalidate
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache invalidated: {key}")
    
    def invalidate_server(self, server_name: str) -> None:
        """
        Invalidate all cache entries for a server.
        
        Args:
            server_name: Server name
        """
        # Find all keys for this server
        keys_to_remove = [
            key for key in self._cache.keys()
            if key.startswith(f"prompt:{server_name}.") or
               key.startswith(f"resource:{server_name}:")
        ]
        
        for key in keys_to_remove:
            del self._cache[key]
        
        if keys_to_remove:
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries for server '{server_name}'")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared ({count} entries)")
    
    async def cleanup_expired(self) -> None:
        """Remove expired cache entries."""
        async with self._lock:
            current_time = time.time()
            expired_keys = []
            
            for key, entry in self._cache.items():
                age = current_time - entry["created_at"]
                if age > entry["ttl"]:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)
    
    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "default_ttl": self.default_ttl
        }
