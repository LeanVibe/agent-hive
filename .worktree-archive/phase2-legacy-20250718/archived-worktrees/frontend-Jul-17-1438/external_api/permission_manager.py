"""
Permission Management System with Redis Caching

Provides comprehensive permission management with:
- High-performance Redis caching
- Bulk permission operations
- Permission queries and analytics
- Cache invalidation strategies
- Distributed permission synchronization
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import asdict
import redis
import pickle
import hashlib
from contextlib import asynccontextmanager

from .rbac_framework import (
    RBACManager, Permission, ResourceType, ActionType, 
    PermissionScope
)

logger = logging.getLogger(__name__)


class PermissionCacheManager:
    """Manages Redis-based caching for permissions with intelligent invalidation."""
    
    def __init__(self, redis_client: redis.Redis, cache_ttl: int = 300):
        self.redis = redis_client
        self.cache_ttl = cache_ttl
        self.key_prefix = "rbac:"
        
        # Cache key patterns
        self.patterns = {
            "user_permissions": f"{self.key_prefix}user_perms:{{user_id}}",
            "role_permissions": f"{self.key_prefix}role_perms:{{role_name}}",
            "permission_check": f"{self.key_prefix}check:{{cache_key}}",
            "role_hierarchy": f"{self.key_prefix}hierarchy:{{role_name}}",
            "user_roles": f"{self.key_prefix}user_roles:{{user_id}}",
            "permission_index": f"{self.key_prefix}perm_idx:{{resource_type}}:{{action}}",
            "bulk_permissions": f"{self.key_prefix}bulk:{{bulk_id}}"
        }
    
    async def get_user_permissions(self, user_id: str) -> Optional[List[Permission]]:
        """Get cached user permissions."""
        key = self.patterns["user_permissions"].format(user_id=user_id)
        
        try:
            cached_data = await self._get_from_cache(key)
            if cached_data:
                return self._deserialize_permissions(cached_data)
        except Exception as e:
            logger.error(f"Error getting user permissions from cache: {e}")
        
        return None
    
    async def set_user_permissions(self, user_id: str, permissions: List[Permission]) -> None:
        """Cache user permissions."""
        key = self.patterns["user_permissions"].format(user_id=user_id)
        
        try:
            serialized_perms = self._serialize_permissions(permissions)
            await self._set_in_cache(key, serialized_perms, self.cache_ttl)
        except Exception as e:
            logger.error(f"Error caching user permissions: {e}")
    
    async def get_permission_check(self, cache_key: str) -> Optional[bool]:
        """Get cached permission check result."""
        key = self.patterns["permission_check"].format(cache_key=cache_key)
        
        try:
            result = await self._get_from_cache(key)
            if result is not None:
                return result.get("allowed", False)
        except Exception as e:
            logger.error(f"Error getting permission check from cache: {e}")
        
        return None
    
    async def set_permission_check(self, cache_key: str, allowed: bool, ttl: int = None) -> None:
        """Cache permission check result."""
        key = self.patterns["permission_check"].format(cache_key=cache_key)
        
        try:
            cache_data = {
                "allowed": allowed,
                "timestamp": time.time()
            }
            await self._set_in_cache(key, cache_data, ttl or self.cache_ttl)
        except Exception as e:
            logger.error(f"Error caching permission check: {e}")
    
    async def get_role_hierarchy(self, role_name: str) -> Optional[Set[str]]:
        """Get cached role hierarchy."""
        key = self.patterns["role_hierarchy"].format(role_name=role_name)
        
        try:
            cached_data = await self._get_from_cache(key)
            if cached_data:
                return set(cached_data.get("hierarchy", []))
        except Exception as e:
            logger.error(f"Error getting role hierarchy from cache: {e}")
        
        return None
    
    async def set_role_hierarchy(self, role_name: str, hierarchy: Set[str]) -> None:
        """Cache role hierarchy."""
        key = self.patterns["role_hierarchy"].format(role_name=role_name)
        
        try:
            cache_data = {
                "hierarchy": list(hierarchy),
                "timestamp": time.time()
            }
            await self._set_in_cache(key, cache_data, self.cache_ttl * 2)  # Longer TTL for hierarchy
        except Exception as e:
            logger.error(f"Error caching role hierarchy: {e}")
    
    async def invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate all cache entries for a user."""
        patterns_to_invalidate = [
            self.patterns["user_permissions"].format(user_id=user_id),
            self.patterns["user_roles"].format(user_id=user_id),
            f"{self.key_prefix}check:*{user_id}*"
        ]
        
        for pattern in patterns_to_invalidate:
            try:
                if "*" in pattern:
                    keys = await self._scan_keys(pattern)
                    if keys:
                        await self._delete_keys(keys)
                else:
                    await self._delete_keys([pattern])
            except Exception as e:
                logger.error(f"Error invalidating user cache: {e}")
    
    async def invalidate_role_cache(self, role_name: str) -> None:
        """Invalidate all cache entries for a role."""
        patterns_to_invalidate = [
            self.patterns["role_permissions"].format(role_name=role_name),
            self.patterns["role_hierarchy"].format(role_name=role_name),
            f"{self.key_prefix}hierarchy:*",  # Invalidate all hierarchy caches
            f"{self.key_prefix}check:*"  # Invalidate all permission checks
        ]
        
        for pattern in patterns_to_invalidate:
            try:
                if "*" in pattern:
                    keys = await self._scan_keys(pattern)
                    if keys:
                        await self._delete_keys(keys)
                else:
                    await self._delete_keys([pattern])
            except Exception as e:
                logger.error(f"Error invalidating role cache: {e}")
    
    async def get_bulk_permissions(self, bulk_id: str) -> Optional[Dict[str, Any]]:
        """Get cached bulk permission results."""
        key = self.patterns["bulk_permissions"].format(bulk_id=bulk_id)
        
        try:
            return await self._get_from_cache(key)
        except Exception as e:
            logger.error(f"Error getting bulk permissions from cache: {e}")
        
        return None
    
    async def set_bulk_permissions(self, bulk_id: str, results: Dict[str, Any]) -> None:
        """Cache bulk permission results."""
        key = self.patterns["bulk_permissions"].format(bulk_id=bulk_id)
        
        try:
            await self._set_in_cache(key, results, self.cache_ttl)
        except Exception as e:
            logger.error(f"Error caching bulk permissions: {e}")
    
    async def _get_from_cache(self, key: str) -> Any:
        """Get value from Redis cache."""
        try:
            data = self.redis.get(key)
            if data:
                return pickle.loads(data)
        except Exception as e:
            logger.error(f"Error deserializing cache data: {e}")
        return None
    
    async def _set_in_cache(self, key: str, value: Any, ttl: int) -> None:
        """Set value in Redis cache."""
        try:
            serialized_data = pickle.dumps(value)
            self.redis.setex(key, ttl, serialized_data)
        except Exception as e:
            logger.error(f"Error serializing cache data: {e}")
    
    async def _delete_keys(self, keys: List[str]) -> None:
        """Delete keys from Redis."""
        if keys:
            self.redis.delete(*keys)
    
    async def _scan_keys(self, pattern: str) -> List[str]:
        """Scan for keys matching pattern."""
        return list(self.redis.scan_iter(match=pattern))
    
    def _serialize_permissions(self, permissions: List[Permission]) -> List[Dict[str, Any]]:
        """Serialize permissions for caching."""
        return [asdict(perm) for perm in permissions]
    
    def _deserialize_permissions(self, data: List[Dict[str, Any]]) -> List[Permission]:
        """Deserialize permissions from cache."""
        permissions = []
        for perm_data in data:
            try:
                # Convert string enums back to enum objects
                perm_data["resource_type"] = ResourceType(perm_data["resource_type"])
                perm_data["action"] = ActionType(perm_data["action"])
                perm_data["scope"] = PermissionScope(perm_data["scope"])
                
                # Convert datetime strings back to datetime objects
                if "created_at" in perm_data:
                    perm_data["created_at"] = datetime.fromisoformat(perm_data["created_at"])
                if "expires_at" in perm_data and perm_data["expires_at"]:
                    perm_data["expires_at"] = datetime.fromisoformat(perm_data["expires_at"])
                
                permissions.append(Permission(**perm_data))
            except Exception as e:
                logger.error(f"Error deserializing permission: {e}")
        
        return permissions


class PermissionManager:
    """Enhanced permission manager with Redis caching and bulk operations."""
    
    def __init__(self, rbac_manager: RBACManager, redis_client: redis.Redis):
        self.rbac = rbac_manager
        self.cache = PermissionCacheManager(redis_client)
        self.redis = redis_client
        
        # Performance metrics
        self.metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "bulk_operations": 0,
            "permission_checks": 0
        }
    
    async def check_permission(self, user_id: str, resource_type: ResourceType, 
                              action: ActionType, resource_id: Optional[str] = None,
                              context: Optional[Dict[str, Any]] = None) -> bool:
        """Check permission with caching."""
        self.metrics["permission_checks"] += 1
        
        # Generate cache key
        cache_key = self._generate_cache_key(user_id, resource_type, action, resource_id, context)
        
        # Check cache first
        cached_result = await self.cache.get_permission_check(cache_key)
        if cached_result is not None:
            self.metrics["cache_hits"] += 1
            return cached_result
        
        # Cache miss - check permission
        self.metrics["cache_misses"] += 1
        result = self.rbac.check_permission(user_id, resource_type, action, resource_id, context)
        
        # Cache the result
        await self.cache.set_permission_check(cache_key, result)
        
        return result
    
    async def bulk_check_permissions(self, requests: List[Dict[str, Any]]) -> Dict[str, bool]:
        """Check multiple permissions efficiently."""
        self.metrics["bulk_operations"] += 1
        
        # Generate bulk ID for caching
        bulk_id = self._generate_bulk_id(requests)
        
        # Check if bulk results are cached
        cached_results = await self.cache.get_bulk_permissions(bulk_id)
        if cached_results:
            self.metrics["cache_hits"] += 1
            return cached_results
        
        # Process bulk requests
        results = {}
        cache_tasks = []
        
        for i, req in enumerate(requests):
            user_id = req["user_id"]
            resource_type = ResourceType(req["resource_type"])
            action = ActionType(req["action"])
            resource_id = req.get("resource_id")
            context = req.get("context")
            
            # Generate unique key for this request
            req_key = f"req_{i}_{user_id}_{resource_type.value}_{action.value}"
            
            # Check individual permission
            result = await self.check_permission(user_id, resource_type, action, resource_id, context)
            results[req_key] = result
        
        # Cache bulk results
        await self.cache.set_bulk_permissions(bulk_id, results)
        
        return results
    
    async def get_user_permissions(self, user_id: str, use_cache: bool = True) -> List[Permission]:
        """Get all permissions for a user with caching."""
        if use_cache:
            cached_perms = await self.cache.get_user_permissions(user_id)
            if cached_perms:
                self.metrics["cache_hits"] += 1
                return cached_perms
        
        # Cache miss - get from RBAC manager
        self.metrics["cache_misses"] += 1
        permissions = self.rbac.get_user_permissions(user_id)
        
        # Cache the results
        if use_cache:
            await self.cache.set_user_permissions(user_id, permissions)
        
        return permissions
    
    async def get_effective_permissions(self, user_id: str, resource_type: Optional[ResourceType] = None,
                                       action: Optional[ActionType] = None) -> List[Permission]:
        """Get effective permissions with optional filtering."""
        all_permissions = await self.get_user_permissions(user_id)
        
        # Apply filters
        filtered_permissions = []
        for perm in all_permissions:
            if resource_type and perm.resource_type != resource_type:
                continue
            if action and perm.action != action:
                continue
            if not perm.is_valid():
                continue
            
            filtered_permissions.append(perm)
        
        return filtered_permissions
    
    async def check_batch_permissions(self, user_id: str, 
                                     permission_requests: List[Tuple[ResourceType, ActionType, Optional[str]]]) -> Dict[str, bool]:
        """Check multiple permissions for a single user."""
        results = {}
        
        for resource_type, action, resource_id in permission_requests:
            key = f"{resource_type.value}:{action.value}:{resource_id or '*'}"
            results[key] = await self.check_permission(user_id, resource_type, action, resource_id)
        
        return results
    
    async def get_users_with_permission(self, resource_type: ResourceType, action: ActionType,
                                       resource_id: Optional[str] = None) -> List[str]:
        """Get all users who have a specific permission."""
        users_with_permission = []
        
        # Check all users
        for user_id in self.rbac.users.keys():
            if await self.check_permission(user_id, resource_type, action, resource_id):
                users_with_permission.append(user_id)
        
        return users_with_permission
    
    async def get_permission_matrix(self, users: List[str], 
                                   permissions: List[Tuple[ResourceType, ActionType, Optional[str]]]) -> Dict[str, Dict[str, bool]]:
        """Generate a permission matrix for multiple users and permissions."""
        matrix = {}
        
        for user_id in users:
            user_permissions = {}
            for resource_type, action, resource_id in permissions:
                perm_key = f"{resource_type.value}:{action.value}:{resource_id or '*'}"
                user_permissions[perm_key] = await self.check_permission(user_id, resource_type, action, resource_id)
            
            matrix[user_id] = user_permissions
        
        return matrix
    
    async def grant_permission(self, user_id: str, permission: Permission) -> bool:
        """Grant a direct permission to a user."""
        user = self.rbac.get_user(user_id)
        if not user:
            return False
        
        user.add_direct_permission(permission)
        await self.cache.invalidate_user_cache(user_id)
        
        return True
    
    async def revoke_permission(self, user_id: str, permission: Permission) -> bool:
        """Revoke a direct permission from a user."""
        user = self.rbac.get_user(user_id)
        if not user:
            return False
        
        if permission in user.direct_permissions:
            user.direct_permissions.remove(permission)
            await self.cache.invalidate_user_cache(user_id)
            return True
        
        return False
    
    async def assign_role(self, user_id: str, role_name: str) -> bool:
        """Assign a role to a user."""
        user = self.rbac.get_user(user_id)
        if not user or role_name not in self.rbac.roles:
            return False
        
        user.assign_role(role_name)
        await self.cache.invalidate_user_cache(user_id)
        
        return True
    
    async def remove_role(self, user_id: str, role_name: str) -> bool:
        """Remove a role from a user."""
        user = self.rbac.get_user(user_id)
        if not user:
            return False
        
        user.remove_role(role_name)
        await self.cache.invalidate_user_cache(user_id)
        
        return True
    
    async def update_role_permissions(self, role_name: str, permissions: List[Permission]) -> bool:
        """Update permissions for a role."""
        success = self.rbac.update_role(role_name, permissions=permissions)
        if success:
            await self.cache.invalidate_role_cache(role_name)
        
        return success
    
    async def get_permission_analytics(self) -> Dict[str, Any]:
        """Get analytics about permission usage."""
        analytics = {
            "total_users": len(self.rbac.users),
            "total_roles": len(self.rbac.roles),
            "total_permissions": sum(len(user.direct_permissions) for user in self.rbac.users.values()),
            "cache_performance": {
                "hits": self.metrics["cache_hits"],
                "misses": self.metrics["cache_misses"],
                "hit_rate": self.metrics["cache_hits"] / max(1, self.metrics["cache_hits"] + self.metrics["cache_misses"])
            },
            "operation_counts": {
                "permission_checks": self.metrics["permission_checks"],
                "bulk_operations": self.metrics["bulk_operations"]
            }
        }
        
        # Add role distribution
        role_distribution = {}
        for user in self.rbac.users.values():
            for role in user.roles:
                role_distribution[role] = role_distribution.get(role, 0) + 1
        
        analytics["role_distribution"] = role_distribution
        
        # Add permission type distribution
        permission_types = {}
        for user in self.rbac.users.values():
            for perm in user.direct_permissions:
                perm_type = f"{perm.resource_type.value}:{perm.action.value}"
                permission_types[perm_type] = permission_types.get(perm_type, 0) + 1
        
        analytics["permission_types"] = permission_types
        
        return analytics
    
    def _generate_cache_key(self, user_id: str, resource_type: ResourceType, 
                           action: ActionType, resource_id: Optional[str] = None,
                           context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a cache key for permission checks."""
        key_parts = [user_id, resource_type.value, action.value, resource_id or ""]
        if context:
            context_str = json.dumps(context, sort_keys=True)
            key_parts.append(hashlib.md5(context_str.encode()).hexdigest())
        return ":".join(key_parts)
    
    def _generate_bulk_id(self, requests: List[Dict[str, Any]]) -> str:
        """Generate a unique ID for bulk permission requests."""
        requests_str = json.dumps(requests, sort_keys=True)
        return hashlib.md5(requests_str.encode()).hexdigest()
    
    async def clear_cache(self) -> None:
        """Clear all caches."""
        try:
            keys = await self.cache._scan_keys(f"{self.cache.key_prefix}*")
            if keys:
                await self.cache._delete_keys(keys)
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            all_keys = await self.cache._scan_keys(f"{self.cache.key_prefix}*")
            
            stats = {
                "total_keys": len(all_keys),
                "key_patterns": {},
                "cache_performance": {
                    "hits": self.metrics["cache_hits"],
                    "misses": self.metrics["cache_misses"],
                    "hit_rate": self.metrics["cache_hits"] / max(1, self.metrics["cache_hits"] + self.metrics["cache_misses"])
                }
            }
            
            # Analyze key patterns
            for key in all_keys:
                pattern = key.split(":")[1] if ":" in key else "unknown"
                stats["key_patterns"][pattern] = stats["key_patterns"].get(pattern, 0) + 1
            
            return stats
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for atomic permission operations."""
        # This is a simple implementation - in production, you might want
        # to use Redis transactions or other atomic operations
        try:
            yield self
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            # Rollback logic would go here
            raise
        finally:
            # Cleanup logic would go here
            pass


class PermissionQueryBuilder:
    """Builder for complex permission queries."""
    
    def __init__(self, permission_manager: PermissionManager):
        self.pm = permission_manager
        self.filters = {}
    
    def for_user(self, user_id: str):
        """Filter by user ID."""
        self.filters["user_id"] = user_id
        return self
    
    def for_resource_type(self, resource_type: ResourceType):
        """Filter by resource type."""
        self.filters["resource_type"] = resource_type
        return self
    
    def for_action(self, action: ActionType):
        """Filter by action."""
        self.filters["action"] = action
        return self
    
    def for_resource(self, resource_id: str):
        """Filter by resource ID."""
        self.filters["resource_id"] = resource_id
        return self
    
    def with_scope(self, scope: PermissionScope):
        """Filter by permission scope."""
        self.filters["scope"] = scope
        return self
    
    async def execute(self) -> List[Permission]:
        """Execute the query and return matching permissions."""
        if "user_id" not in self.filters:
            raise ValueError("User ID is required for permission queries")
        
        user_id = self.filters["user_id"]
        permissions = await self.pm.get_user_permissions(user_id)
        
        # Apply filters
        filtered_permissions = []
        for perm in permissions:
            if self._matches_filters(perm):
                filtered_permissions.append(perm)
        
        return filtered_permissions
    
    def _matches_filters(self, permission: Permission) -> bool:
        """Check if permission matches all filters."""
        for key, value in self.filters.items():
            if key == "user_id":
                continue
            
            perm_value = getattr(permission, key, None)
            if perm_value != value:
                return False
        
        return True
    
    def query(self) -> 'PermissionQueryBuilder':
        """Create a new query builder."""
        return PermissionQueryBuilder(self.pm)