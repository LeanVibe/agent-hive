"""
Redis Cache Integration for RBAC and JWT Token Management

Coordinates with Infrastructure Agent's caching strategy for:
- JWT token blacklisting
- Role and permission caching
- Session management
- RBAC authorization results
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set, Union
import hashlib
import redis
from dataclasses import asdict

logger = logging.getLogger(__name__)


class RedisCacheManager:
    """Manages Redis caching for authentication and authorization."""
    
    def __init__(self, redis_client: redis.Redis, cache_prefix: str = "agent_hive"):
        self.redis_client = redis_client
        self.cache_prefix = cache_prefix
        self.default_ttl = 300  # 5 minutes
        
        # Cache key patterns
        self.patterns = {
            "jwt_blacklist": f"{cache_prefix}:jwt:blacklist",
            "user_roles": f"{cache_prefix}:user:roles",
            "role_permissions": f"{cache_prefix}:role:permissions",
            "permission_cache": f"{cache_prefix}:permission:cache",
            "session": f"{cache_prefix}:session",
            "rbac_authorization": f"{cache_prefix}:rbac:auth"
        }
    
    # JWT Token Blacklist Management
    
    def blacklist_jwt_token(self, token: str, expires_at: datetime) -> bool:
        """Add JWT token to blacklist."""
        try:
            # Calculate TTL based on token expiration
            ttl = max(int((expires_at - datetime.utcnow()).total_seconds()), 0)
            
            # Hash token for privacy
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            # Store in Redis with expiration
            key = f"{self.patterns['jwt_blacklist']}:{token_hash}"
            self.redis_client.setex(key, ttl, "blacklisted")
            
            logger.info(f"Blacklisted JWT token (hash: {token_hash[:8]}...)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to blacklist JWT token: {e}")
            return False
    
    def is_jwt_token_blacklisted(self, token: str) -> bool:
        """Check if JWT token is blacklisted."""
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            key = f"{self.patterns['jwt_blacklist']}:{token_hash}"
            return self.redis_client.exists(key)
            
        except Exception as e:
            logger.error(f"Failed to check JWT blacklist: {e}")
            return False
    
    # User Role Caching
    
    def cache_user_roles(self, user_id: str, roles: List[str], ttl: int = None) -> bool:
        """Cache user roles."""
        try:
            key = f"{self.patterns['user_roles']}:{user_id}"
            value = json.dumps(roles)
            
            ttl = ttl or self.default_ttl
            self.redis_client.setex(key, ttl, value)
            
            logger.debug(f"Cached roles for user {user_id}: {roles}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache user roles: {e}")
            return False
    
    def get_cached_user_roles(self, user_id: str) -> Optional[List[str]]:
        """Get cached user roles."""
        try:
            key = f"{self.patterns['user_roles']}:{user_id}"
            value = self.redis_client.get(key)
            
            if value:
                return json.loads(value.decode())
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached user roles: {e}")
            return None
    
    def invalidate_user_roles(self, user_id: str) -> bool:
        """Invalidate cached user roles."""
        try:
            key = f"{self.patterns['user_roles']}:{user_id}"
            self.redis_client.delete(key)
            
            logger.debug(f"Invalidated roles cache for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to invalidate user roles: {e}")
            return False
    
    # Role Permission Caching
    
    def cache_role_permissions(self, role_name: str, permissions: List[Dict[str, Any]], ttl: int = None) -> bool:
        """Cache role permissions."""
        try:
            key = f"{self.patterns['role_permissions']}:{role_name}"
            value = json.dumps(permissions)
            
            ttl = ttl or self.default_ttl
            self.redis_client.setex(key, ttl, value)
            
            logger.debug(f"Cached permissions for role {role_name}: {len(permissions)} permissions")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache role permissions: {e}")
            return False
    
    def get_cached_role_permissions(self, role_name: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached role permissions."""
        try:
            key = f"{self.patterns['role_permissions']}:{role_name}"
            value = self.redis_client.get(key)
            
            if value:
                return json.loads(value.decode())
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached role permissions: {e}")
            return None
    
    def invalidate_role_permissions(self, role_name: str) -> bool:
        """Invalidate cached role permissions."""
        try:
            key = f"{self.patterns['role_permissions']}:{role_name}"
            self.redis_client.delete(key)
            
            logger.debug(f"Invalidated permissions cache for role {role_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to invalidate role permissions: {e}")
            return False
    
    # RBAC Authorization Caching
    
    def cache_authorization_result(self, user_id: str, resource_type: str, action: str, 
                                 resource_id: Optional[str], result: bool, ttl: int = None) -> bool:
        """Cache RBAC authorization result."""
        try:
            # Generate cache key
            cache_key = self._generate_auth_cache_key(user_id, resource_type, action, resource_id)
            
            auth_data = {
                "user_id": user_id,
                "resource_type": resource_type,
                "action": action,
                "resource_id": resource_id,
                "result": result,
                "timestamp": time.time()
            }
            
            value = json.dumps(auth_data)
            ttl = ttl or self.default_ttl
            
            key = f"{self.patterns['rbac_authorization']}:{cache_key}"
            self.redis_client.setex(key, ttl, value)
            
            logger.debug(f"Cached authorization result for {user_id}: {result}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache authorization result: {e}")
            return False
    
    def get_cached_authorization_result(self, user_id: str, resource_type: str, action: str, 
                                      resource_id: Optional[str]) -> Optional[bool]:
        """Get cached RBAC authorization result."""
        try:
            cache_key = self._generate_auth_cache_key(user_id, resource_type, action, resource_id)
            key = f"{self.patterns['rbac_authorization']}:{cache_key}"
            
            value = self.redis_client.get(key)
            if value:
                auth_data = json.loads(value.decode())
                return auth_data.get("result")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached authorization result: {e}")
            return None
    
    def invalidate_user_authorization_cache(self, user_id: str) -> bool:
        """Invalidate all authorization cache for a user."""
        try:
            pattern = f"{self.patterns['rbac_authorization']}:{user_id}:*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                self.redis_client.delete(*keys)
                logger.debug(f"Invalidated {len(keys)} authorization cache entries for user {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to invalidate user authorization cache: {e}")
            return False
    
    # Session Management
    
    def create_session(self, session_id: str, user_id: str, session_data: Dict[str, Any], ttl: int = None) -> bool:
        """Create a session in Redis."""
        try:
            session_info = {
                "session_id": session_id,
                "user_id": user_id,
                "created_at": time.time(),
                "last_activity": time.time(),
                "data": session_data
            }
            
            key = f"{self.patterns['session']}:{session_id}"
            value = json.dumps(session_info)
            
            ttl = ttl or 3600  # 1 hour default for sessions
            self.redis_client.setex(key, ttl, value)
            
            logger.debug(f"Created session {session_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from Redis."""
        try:
            key = f"{self.patterns['session']}:{session_id}"
            value = self.redis_client.get(key)
            
            if value:
                return json.loads(value.decode())
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None
    
    def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp."""
        try:
            session_data = self.get_session(session_id)
            if not session_data:
                return False
            
            session_data["last_activity"] = time.time()
            
            key = f"{self.patterns['session']}:{session_id}"
            value = json.dumps(session_data)
            
            # Keep existing TTL
            ttl = self.redis_client.ttl(key)
            if ttl > 0:
                self.redis_client.setex(key, ttl, value)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session activity: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session from Redis."""
        try:
            key = f"{self.patterns['session']}:{session_id}"
            self.redis_client.delete(key)
            
            logger.debug(f"Deleted session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
    
    # Infrastructure Agent Coordination
    
    def coordinate_with_infrastructure_cache(self, infrastructure_redis_client: redis.Redis) -> bool:
        """Coordinate caching strategy with Infrastructure Agent's Redis client."""
        try:
            # Share cache namespace information
            coordination_key = f"{self.cache_prefix}:coordination:security"
            
            coordination_data = {
                "service": "security-specialist",
                "cache_patterns": self.patterns,
                "default_ttl": self.default_ttl,
                "coordination_timestamp": time.time()
            }
            
            infrastructure_redis_client.setex(
                coordination_key, 
                600,  # 10 minutes
                json.dumps(coordination_data)
            )
            
            logger.info("Coordinated cache strategy with Infrastructure Agent")
            return True
            
        except Exception as e:
            logger.error(f"Failed to coordinate with Infrastructure Agent: {e}")
            return False
    
    # Utility Methods
    
    def _generate_auth_cache_key(self, user_id: str, resource_type: str, action: str, 
                                resource_id: Optional[str]) -> str:
        """Generate a cache key for authorization results."""
        key_parts = [user_id, resource_type, action, resource_id or ""]
        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            stats = {}
            
            for pattern_name, pattern in self.patterns.items():
                keys = self.redis_client.keys(f"{pattern}:*")
                stats[pattern_name] = len(keys)
            
            # Redis info
            redis_info = self.redis_client.info()
            stats["redis_info"] = {
                "used_memory": redis_info.get("used_memory"),
                "connected_clients": redis_info.get("connected_clients"),
                "total_commands_processed": redis_info.get("total_commands_processed")
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}
    
    def clear_all_cache(self) -> bool:
        """Clear all cache entries (use with caution)."""
        try:
            for pattern in self.patterns.values():
                keys = self.redis_client.keys(f"{pattern}:*")
                if keys:
                    self.redis_client.delete(*keys)
            
            logger.warning("Cleared all cache entries")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear all cache: {e}")
            return False


# Factory function for creating Redis cache manager
def create_redis_cache_manager(redis_host: str = "localhost", redis_port: int = 6379, 
                             redis_db: int = 0, redis_password: Optional[str] = None,
                             cache_prefix: str = "agent_hive") -> RedisCacheManager:
    """Create a Redis cache manager instance."""
    try:
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=False
        )
        
        # Test connection
        redis_client.ping()
        
        cache_manager = RedisCacheManager(redis_client, cache_prefix)
        logger.info(f"Created Redis cache manager (host: {redis_host}, db: {redis_db})")
        
        return cache_manager
        
    except Exception as e:
        logger.error(f"Failed to create Redis cache manager: {e}")
        raise