import time
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import threading

class APICache:
    """Simple in-memory cache for API responses"""
    
    def __init__(self, ttl_minutes: int = 10, max_entries: int = 100):
        """
        Initialize cache
        
        Args:
            ttl_minutes: Time to live in minutes
            max_entries: Maximum number of cached entries
        """
        self.ttl_seconds = ttl_minutes * 60
        self.max_entries = max_entries
        self.cache = {}
        self.access_times = {}
        self.lock = threading.Lock()
        
        print(f"💾 APICache initialized (TTL: {ttl_minutes}min, Max: {max_entries} entries)")
    
    def _generate_key(self, msisdn: str, start_time: str, end_time: str) -> str:
        """Generate cache key from parameters"""
        key_string = f"{msisdn}_{start_time}_{end_time}"
        return hashlib.md5(key_string.encode()).hexdigest()[:16]
    
    def _is_expired(self, timestamp: float) -> bool:
        """Check if cache entry is expired"""
        return time.time() - timestamp > self.ttl_seconds
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.access_times.items()
            if current_time - timestamp > self.ttl_seconds
        ]
        
        for key in expired_keys:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
    
    def _enforce_max_entries(self):
        """Remove oldest entries if cache exceeds max size"""
        if len(self.cache) <= self.max_entries:
            return
        
        # Sort by access time (oldest first)
        sorted_keys = sorted(
            self.access_times.items(),
            key=lambda x: x[1]
        )
        
        # Remove oldest entries
        entries_to_remove = len(self.cache) - self.max_entries + 1
        for key, _ in sorted_keys[:entries_to_remove]:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
    
    def get(self, msisdn: str, start_time: str, end_time: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available and not expired"""
        with self.lock:
            key = self._generate_key(msisdn, start_time, end_time)
            
            if key not in self.cache:
                return None
            
            # Check if expired
            if self._is_expired(self.access_times.get(key, 0)):
                self.cache.pop(key, None)
                self.access_times.pop(key, None)
                return None
            
            # Update access time
            self.access_times[key] = time.time()
            
            cached_data = self.cache[key].copy()
            cached_data["from_cache"] = True
            cached_data["cached_at"] = datetime.fromtimestamp(
                self.access_times[key] - self.ttl_seconds
            ).isoformat()
            
            print(f"💾 Cache HIT for {msisdn} ({start_time} to {end_time})")
            return cached_data
    
    def set(self, msisdn: str, start_time: str, end_time: str, response: Dict[str, Any]):
        """Cache API response"""
        with self.lock:
            key = self._generate_key(msisdn, start_time, end_time)
            
            # Clean expired entries
            self._cleanup_expired()
            
            # Store response
            self.cache[key] = response.copy()
            self.access_times[key] = time.time()
            
            # Enforce max entries
            self._enforce_max_entries()
            
            print(f"💾 Cache SET for {msisdn} ({start_time} to {end_time})")
    
    def invalidate(self, msisdn: str = None):
        """Invalidate cache entries"""
        with self.lock:
            if msisdn is None:
                # Clear all cache
                self.cache.clear()
                self.access_times.clear()
                print("💾 Cache CLEARED (all entries)")
            else:
                # Clear entries for specific MSISDN
                keys_to_remove = []
                for key in self.cache.keys():
                    if key.startswith(self._generate_key(msisdn, "", "")[:8]):
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    self.cache.pop(key, None)
                    self.access_times.pop(key, None)
                
                print(f"💾 Cache INVALIDATED for {msisdn} ({len(keys_to_remove)} entries)")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            self._cleanup_expired()
            
            # Calculate hit ratio (would need to track hits/misses)
            current_time = time.time()
            valid_entries = sum(
                1 for timestamp in self.access_times.values()
                if not self._is_expired(timestamp)
            )
            
            # Calculate memory usage estimation
            total_size = 0
            for response in self.cache.values():
                total_size += len(str(response))
            
            return {
                "total_entries": len(self.cache),
                "valid_entries": valid_entries,
                "max_entries": self.max_entries,
                "ttl_seconds": self.ttl_seconds,
                "estimated_size_bytes": total_size,
                "oldest_entry_age_seconds": (
                    current_time - min(self.access_times.values())
                    if self.access_times else 0
                ),
                "cache_utilization": len(self.cache) / self.max_entries * 100
            }
    
    def get_cached_entries(self) -> List[Dict[str, Any]]:
        """Get list of cached entries for debugging"""
        with self.lock:
            current_time = time.time()
            entries = []
            
            for key, timestamp in self.access_times.items():
                age_seconds = current_time - timestamp
                is_expired = self._is_expired(timestamp)
                
                entries.append({
                    "key": key,
                    "age_seconds": age_seconds,
                    "is_expired": is_expired,
                    "cached_at": datetime.fromtimestamp(timestamp).isoformat(),
                    "response_size": len(str(self.cache.get(key, {})))
                })
            
            return sorted(entries, key=lambda x: x["age_seconds"])


class CachedAPIClient:
    """Wrapper for API client with caching"""
    
    def __init__(self, api_client, cache_ttl_minutes: int = 10):
        """
        Initialize cached API client
        
        Args:
            api_client: The actual API client instance
            cache_ttl_minutes: Cache time to live in minutes
        """
        self.api_client = api_client
        self.cache = APICache(ttl_minutes=cache_ttl_minutes)
        
        print(f"💾 CachedAPIClient initialized with {cache_ttl_minutes}min TTL")
    
    def query_user_history(self, msisdn: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Query user history with caching"""
        # Try cache first
        cached_response = self.cache.get(msisdn, start_time, end_time)
        if cached_response:
            return cached_response
        
        # Cache miss - call actual API
        print(f"💾 Cache MISS for {msisdn} - calling API...")
        response = self.api_client.query_user_history(msisdn, start_time, end_time)
        
        # Cache successful responses only
        if response.get("success", False):
            self.cache.set(msisdn, start_time, end_time, response)
        
        return response
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection (not cached)"""
        return self.api_client.test_connection()
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection info (not cached)"""
        return self.api_client.get_connection_info()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_stats()
    
    def clear_cache(self, msisdn: str = None):
        """Clear cache"""
        self.cache.invalidate(msisdn)