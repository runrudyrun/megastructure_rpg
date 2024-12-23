"""Caching system for generated sectors."""
from typing import Dict, Tuple, Optional
import time
import logging
from .tilemap import TileMap

logger = logging.getLogger(__name__)

class SectorCache:
    """Cache for storing and managing generated sectors."""
    
    def __init__(self, max_size: int = 100, ttl: float = 300.0):
        """
        Initialize the sector cache.
        
        Args:
            max_size: Maximum number of sectors to keep in cache
            ttl: Time-to-live in seconds for cached sectors
        """
        self._cache: Dict[Tuple[int, int, str], Tuple[TileMap, float]] = {}
        self._max_size = max_size
        self._ttl = ttl
        
    def get(self, x: int, y: int, theme: str) -> Optional[TileMap]:
        """
        Get a sector from cache if it exists and is not expired.
        
        Args:
            x: Sector X coordinate
            y: Sector Y coordinate
            theme: Sector theme
        
        Returns:
            Cached TileMap if found and valid, None otherwise
        """
        key = (x, y, theme)
        if key in self._cache:
            tilemap, timestamp = self._cache[key]
            if time.time() - timestamp <= self._ttl:
                logger.debug(f"Cache hit for sector ({x}, {y}, {theme})")
                return tilemap
            else:
                logger.debug(f"Cache expired for sector ({x}, {y}, {theme})")
                del self._cache[key]
        return None
        
    def put(self, x: int, y: int, theme: str, tilemap: TileMap) -> None:
        """
        Store a sector in the cache.
        
        Args:
            x: Sector X coordinate
            y: Sector Y coordinate
            theme: Sector theme
            tilemap: Generated TileMap to cache
        """
        # Ensure we don't exceed max size
        if len(self._cache) >= self._max_size:
            # Remove oldest entry
            oldest_key = min(self._cache.items(), key=lambda x: x[1][1])[0]
            del self._cache[oldest_key]
            logger.debug(f"Removed oldest sector from cache: {oldest_key}")
            
        key = (x, y, theme)
        self._cache[key] = (tilemap, time.time())
        logger.debug(f"Cached sector ({x}, {y}, {theme})")
        
    def clear(self) -> None:
        """Clear all cached sectors."""
        self._cache.clear()
        logger.debug("Cleared sector cache")
        
    def remove(self, x: int, y: int, theme: str) -> None:
        """
        Remove a specific sector from cache.
        
        Args:
            x: Sector X coordinate
            y: Sector Y coordinate
            theme: Sector theme
        """
        key = (x, y, theme)
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Removed sector ({x}, {y}, {theme}) from cache")
            
    @property
    def size(self) -> int:
        """Get current number of cached sectors."""
        return len(self._cache)
