"""
Cache utilities for the itinerary planning system.
Provides lightweight JSON-based caching for POIs and distance matrices.
"""
import os
import json
import time
import hashlib
from typing import Any, Optional, Dict
import aiofiles
from pathlib import Path


class JSONCache:
    """Simple JSON-based cache with TTL support."""
    
    def __init__(self, cache_dir: str = "app/cache"):
        """
        Initialize the cache.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "cache.json"
        self._cache = {}
        self._load_cache()
    
    def _load_cache(self):
        """Load existing cache from disk."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    self._cache = json.load(f)
        except (json.JSONDecodeError, IOError):
            self._cache = {}
    
    async def _save_cache(self):
        """Save cache to disk asynchronously."""
        try:
            cache_data = json.dumps(self._cache, indent=2)
            async with aiofiles.open(self.cache_file, 'w') as f:
                await f.write(cache_data)
        except IOError:
            pass  # Fail silently on cache save errors
    
    def _is_expired(self, entry: Dict) -> bool:
        """Check if cache entry is expired."""
        current_time = int(time.time())
        return current_time > (entry.get("timestamp", 0) + entry.get("ttl", 0))
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if self._is_expired(entry):
            del self._cache[key]
            await self._save_cache()
            return None
        
        return entry.get("data")
    
    async def set(self, key: str, value: Any, ttl: int = 86400):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 24 hours)
        """
        entry = {
            "data": value,
            "timestamp": int(time.time()),
            "ttl": ttl
        }
        
        self._cache[key] = entry
        await self._save_cache()
    
    async def delete(self, key: str):
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]
            await self._save_cache()
    
    async def clear(self):
        """Clear all cache entries."""
        self._cache = {}
        await self._save_cache()
    
    async def cleanup_expired(self):
        """Remove expired entries from cache."""
        expired_keys = []
        for key, entry in self._cache.items():
            if self._is_expired(entry):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            await self._save_cache()
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        total_entries = len(self._cache)
        expired_entries = sum(1 for entry in self._cache.values() if self._is_expired(entry))
        
        return {
            "total_entries": total_entries,
            "active_entries": total_entries - expired_entries,
            "expired_entries": expired_entries
        }


# Global cache instance
_cache_instance = None


def get_cache() -> JSONCache:
    """Get or create the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = JSONCache()
    return _cache_instance


async def get_cached(key: str) -> Optional[Any]:
    """
    Get value from cache using the global cache instance.
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None if not found/expired
    """
    cache = get_cache()
    return await cache.get(key)


async def set_cached(key: str, value: Any, ttl: int = 86400):
    """
    Set value in cache using the global cache instance.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds (default: 24 hours)
    """
    cache = get_cache()
    await cache.set(key, value, ttl)


async def delete_cached(key: str):
    """Delete key from cache using the global cache instance."""
    cache = get_cache()
    await cache.delete(key)


def generate_cache_key(*args, **kwargs) -> str:
    """
    Generate a cache key from arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        SHA256 hash as cache key
    """
    # Create a string representation of all arguments
    key_parts = []
    
    for arg in args:
        if hasattr(arg, '__dict__'):
            # Handle objects with attributes
            key_parts.append(str(sorted(arg.__dict__.items())))
        else:
            key_parts.append(str(arg))
    
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
    
    key_string = "|".join(key_parts)
    
    # Generate SHA256 hash
    return hashlib.sha256(key_string.encode('utf-8')).hexdigest()


def generate_poi_cache_key(city: str, date: str = None) -> str:
    """
    Generate cache key for POI data.
    
    Args:
        city: City name
        date: Optional date (for date-specific POI data)
        
    Returns:
        Cache key for POI data
    """
    parts = [f"pois_{city.lower()}"]
    if date:
        parts.append(date)
    return "_".join(parts)


def generate_distance_matrix_key(locations: list, mode: str = "driving") -> str:
    """
    Generate cache key for distance matrix data.
    
    Args:
        locations: List of location dictionaries
        mode: Transportation mode
        
    Returns:
        Cache key for distance matrix
    """
    # Sort locations to ensure consistent cache keys
    sorted_locations = sorted(locations, key=lambda x: (x['lat'], x['lng']))
    location_hash = hashlib.md5(str(sorted_locations).encode()).hexdigest()[:8]
    
    return f"distance_matrix_{mode}_{location_hash}"


async def cache_distance_matrix(locations: list, matrix_data: Any, mode: str = "driving", ttl: int = 86400):
    """
    Cache distance matrix data.
    
    Args:
        locations: List of location dictionaries
        matrix_data: Distance matrix data to cache
        mode: Transportation mode
        ttl: Time to live in seconds
    """
    key = generate_distance_matrix_key(locations, mode)
    await set_cached(key, matrix_data, ttl)


async def get_cached_distance_matrix(locations: list, mode: str = "driving") -> Optional[Any]:
    """
    Get cached distance matrix data.
    
    Args:
        locations: List of location dictionaries
        mode: Transportation mode
        
    Returns:
        Cached distance matrix data or None
    """
    key = generate_distance_matrix_key(locations, mode)
    return await get_cached(key)


async def initialize_cache_with_sample_data():
    """Initialize cache with sample data for testing."""
    from app.utils.mock_data import create_sample_cache_data
    
    sample_data = create_sample_cache_data()
    cache = get_cache()
    
    for key, entry in sample_data.items():
        await cache.set(key, entry["data"], entry["ttl"])


# Cleanup utility for maintenance
async def cleanup_cache():
    """Cleanup expired cache entries."""
    cache = get_cache()
    await cache.cleanup_expired()
    return cache.get_stats()