#!/usr/bin/env python3
"""
Permission Enforcement Middleware

Advanced middleware for enforcing role-based permissions on API endpoints
with context-aware evaluation, performance optimization, and comprehensive logging.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Set, Tuple
from functools import wraps
from dataclasses import dataclass
import uuid

from config.auth_models import Permission, AuthResult
from security.rbac_manager import RBACManager, PermissionType, PermissionCheck
from security.auth_service import AuthenticationService


logger = logging.getLogger(__name__)


@dataclass
class EndpointPermission:
    """Endpoint permission requirement definition."""
    endpoint: str
    method: str
    required_permissions: List[PermissionType]
    optional_permissions: List[PermissionType] = None
    context_required: bool = False
    bypass_conditions: List[str] = None
    description: str = ""
    
    def __post_init__(self):
        if self.optional_permissions is None:
            self.optional_permissions = []
        if self.bypass_conditions is None:
            self.bypass_conditions = []


@dataclass
class PermissionContext:
    """Context for permission evaluation."""
    user_id: str
    endpoint: str
    method: str
    client_ip: str
    user_agent: str
    request_data: Dict[str, Any] = None
    headers: Dict[str, str] = None
    query_params: Dict[str, str] = None
    
    def __post_init__(self):
        if self.request_data is None:
            self.request_data = {}
        if self.headers is None:
            self.headers = {}
        if self.query_params is None:
            self.query_params = {}


@dataclass
class PermissionResult:
    """Result of permission enforcement check."""
    allowed: bool
    user_id: str
    endpoint: str
    method: str
    permissions_checked: List[PermissionType]
    permissions_granted: List[PermissionType]
    permissions_denied: List[PermissionType]
    reason: str
    response_time_ms: float
    cached: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PermissionMiddleware:
    """
    Advanced permission enforcement middleware.
    
    Features:
    - Endpoint-specific permission requirements
    - Context-aware permission evaluation
    - Performance-optimized with caching
    - Flexible bypass conditions
    - Comprehensive audit logging
    - Rate limiting integration
    """
    
    def __init__(self, rbac_manager: RBACManager, auth_service: AuthenticationService, 
                 config: Optional[Dict[str, Any]] = None):
        """Initialize permission middleware."""
        self.rbac_manager = rbac_manager
        self.auth_service = auth_service
        self.config = config or {}
        
        # Endpoint permission registry
        self.endpoint_permissions: Dict[str, EndpointPermission] = {}
        self.global_permissions: List[PermissionType] = []
        
        # Performance monitoring
        self.permission_checks: List[PermissionResult] = []
        self.performance_stats = {
            "total_checks": 0,
            "cache_hits": 0,
            "average_response_time_ms": 0.0,
            "denied_requests": 0
        }
        
        # Cache settings
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.cache_ttl = self.config.get("cache_ttl_seconds", 60)
        self.permission_cache: Dict[str, Tuple[PermissionResult, datetime]] = {}
        
        # Initialize default endpoint permissions
        self._initialize_default_permissions()
        
        logger.info("PermissionMiddleware initialized with RBAC integration")
    
    def _initialize_default_permissions(self) -> None:
        """Initialize default endpoint permission requirements."""
        default_endpoints = [
            # System Administration
            EndpointPermission(
                endpoint="/api/v1/system/config",
                method="POST",
                required_permissions=[PermissionType.SYSTEM_ADMIN],
                description="System configuration changes"
            ),
            EndpointPermission(
                endpoint="/api/v1/system/monitoring",
                method="GET",
                required_permissions=[PermissionType.SYSTEM_MONITORING],
                description="System monitoring access"
            ),
            
            # User Management
            EndpointPermission(
                endpoint="/api/v1/users",
                method="POST",
                required_permissions=[PermissionType.USER_CREATE],
                description="Create new user"
            ),
            EndpointPermission(
                endpoint="/api/v1/users",
                method="GET",
                required_permissions=[PermissionType.USER_READ],
                description="List users"
            ),
            EndpointPermission(
                endpoint="/api/v1/users/{user_id}",
                method="PUT",
                required_permissions=[PermissionType.USER_UPDATE],
                description="Update user"
            ),
            EndpointPermission(
                endpoint="/api/v1/users/{user_id}",
                method="DELETE",
                required_permissions=[PermissionType.USER_DELETE],
                description="Delete user"
            ),
            
            # Agent Management
            EndpointPermission(
                endpoint="/api/v1/agents",
                method="POST",
                required_permissions=[PermissionType.AGENT_SPAWN],
                description="Spawn new agent"
            ),
            EndpointPermission(
                endpoint="/api/v1/agents/{agent_id}/control",
                method="POST",
                required_permissions=[PermissionType.AGENT_CONTROL],
                description="Control agent"
            ),
            EndpointPermission(
                endpoint="/api/v1/agents",
                method="GET",
                required_permissions=[PermissionType.AGENT_MONITOR],
                description="Monitor agents"
            ),
            
            # Task Execution
            EndpointPermission(
                endpoint="/api/v1/tasks",
                method="POST",
                required_permissions=[PermissionType.TASK_CREATE],
                description="Create task"
            ),
            EndpointPermission(
                endpoint="/api/v1/tasks/{task_id}/execute",
                method="POST",
                required_permissions=[PermissionType.TASK_EXECUTION],
                description="Execute task"
            ),
            
            # API Gateway
            EndpointPermission(
                endpoint="/api/v1/gateway/admin",
                method="GET",
                required_permissions=[PermissionType.API_ADMIN],
                description="API Gateway administration"
            ),
            
            # RBAC Management
            EndpointPermission(
                endpoint="/api/v1/rbac/roles",
                method="POST",
                required_permissions=[PermissionType.USER_MANAGEMENT],
                description="Create role"
            ),
            EndpointPermission(
                endpoint="/api/v1/rbac/roles/{role_id}/assign",
                method="POST",
                required_permissions=[PermissionType.USER_MANAGEMENT],
                description="Assign role to user"
            ),
            
            # Public endpoints (no authentication required)
            EndpointPermission(
                endpoint="/api/v1/health",
                method="GET",
                required_permissions=[PermissionType.PUBLIC_ACCESS],
                description="Health check"
            ),
            EndpointPermission(
                endpoint="/api/v1/status",
                method="GET",
                required_permissions=[PermissionType.PUBLIC_ACCESS],
                description="System status"
            )
        ]
        
        # Register default endpoints
        for endpoint_perm in default_endpoints:
            self.register_endpoint_permission(endpoint_perm)
        
        logger.info(f"Registered {len(default_endpoints)} default endpoint permissions")
    
    def register_endpoint_permission(self, endpoint_permission: EndpointPermission) -> bool:
        """Register permission requirements for an endpoint."""
        try:
            key = f"{endpoint_permission.method}:{endpoint_permission.endpoint}"
            self.endpoint_permissions[key] = endpoint_permission
            logger.debug(f"Registered permission for {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to register endpoint permission: {e}")
            return False
    
    def set_global_permissions(self, permissions: List[PermissionType]) -> None:
        """Set global permissions required for all endpoints."""
        self.global_permissions = permissions
        logger.info(f"Set {len(permissions)} global permissions")
    
    async def enforce_permissions(self, context: PermissionContext, 
                                 access_token: str) -> PermissionResult:
        """
        Main method to enforce permissions for a request.
        
        Args:
            context: Permission context with request details
            access_token: User's access token
            
        Returns:
            PermissionResult with enforcement decision
        """
        start_time = time.time()
        
        try:
            # Check cache first
            if self.cache_enabled:
                cached_result = await self._check_permission_cache(context, access_token)
                if cached_result:
                    cached_result.cached = True
                    self._update_performance_stats(cached_result)
                    return cached_result
            
            # Validate user session
            auth_result = await self.auth_service.validate_session(
                access_token, 
                context.client_ip
            )
            
            if not auth_result.success:
                result = PermissionResult(
                    allowed=False,
                    user_id="unknown",
                    endpoint=context.endpoint,
                    method=context.method,
                    permissions_checked=[],
                    permissions_granted=[],
                    permissions_denied=[],
                    reason=f"Authentication failed: {auth_result.error}",
                    response_time_ms=(time.time() - start_time) * 1000
                )
                self._update_performance_stats(result)
                return result
            
            # Get endpoint permission requirements
            endpoint_key = f"{context.method}:{context.endpoint}"
            endpoint_perm = self.endpoint_permissions.get(endpoint_key)
            
            if not endpoint_perm:
                # Check for pattern matches (e.g., /api/v1/users/{user_id})
                endpoint_perm = await self._find_matching_endpoint_permission(context)
            
            # Determine required permissions
            required_permissions = []
            if endpoint_perm:
                required_permissions.extend(endpoint_perm.required_permissions)
            required_permissions.extend(self.global_permissions)
            
            # If no specific permissions required, allow with basic auth
            if not required_permissions:
                result = PermissionResult(
                    allowed=True,
                    user_id=auth_result.user_id,
                    endpoint=context.endpoint,
                    method=context.method,
                    permissions_checked=[],
                    permissions_granted=[],
                    permissions_denied=[],
                    reason="no_specific_permissions_required",
                    response_time_ms=(time.time() - start_time) * 1000,
                    metadata={"authenticated": True}
                )
                await self._cache_permission_result(context, access_token, result)
                self._update_performance_stats(result)
                return result
            
            # Check each required permission
            permissions_granted = []
            permissions_denied = []
            
            for permission in required_permissions:
                check_result = await self.rbac_manager.check_permission(
                    auth_result.user_id, 
                    permission,
                    context=context.__dict__
                )
                
                if check_result.granted:
                    permissions_granted.append(permission)
                else:
                    permissions_denied.append(permission)
            
            # Determine if access is allowed
            allowed = len(permissions_denied) == 0
            
            # Check bypass conditions
            if not allowed and endpoint_perm and endpoint_perm.bypass_conditions:
                bypass_allowed = await self._check_bypass_conditions(
                    endpoint_perm.bypass_conditions, 
                    context, 
                    auth_result
                )
                if bypass_allowed:
                    allowed = True
            
            # Create result
            result = PermissionResult(
                allowed=allowed,
                user_id=auth_result.user_id,
                endpoint=context.endpoint,
                method=context.method,
                permissions_checked=required_permissions,
                permissions_granted=permissions_granted,
                permissions_denied=permissions_denied,
                reason="permission_check_completed" if allowed else "insufficient_permissions",
                response_time_ms=(time.time() - start_time) * 1000,
                metadata={
                    "authenticated": True,
                    "endpoint_specific": endpoint_perm is not None,
                    "bypass_checked": endpoint_perm and endpoint_perm.bypass_conditions
                }
            )
            
            # Cache result
            if self.cache_enabled:
                await self._cache_permission_result(context, access_token, result)
            
            # Log permission enforcement
            await self._log_permission_enforcement(result, context)
            
            # Update performance stats
            self._update_performance_stats(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Permission enforcement error: {e}")
            result = PermissionResult(
                allowed=False,
                user_id="unknown",
                endpoint=context.endpoint,
                method=context.method,
                permissions_checked=[],
                permissions_granted=[],
                permissions_denied=[],
                reason=f"enforcement_error: {e}",
                response_time_ms=(time.time() - start_time) * 1000,
                metadata={"error": str(e)}
            )
            self._update_performance_stats(result)
            return result
    
    def require_permissions(self, *permissions: PermissionType):
        """Decorator for protecting functions with permission requirements."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract context and token from function arguments
                # This would need to be customized based on your framework
                context = kwargs.get('context')
                access_token = kwargs.get('access_token')
                
                if not context or not access_token:
                    raise ValueError("Permission decorator requires context and access_token")
                
                # Check permissions
                result = await self.enforce_permissions(context, access_token)
                
                if not result.allowed:
                    raise PermissionError(f"Access denied: {result.reason}")
                
                # Add permission result to kwargs for function use
                kwargs['permission_result'] = result
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    async def check_bulk_permissions(self, user_id: str, 
                                   permissions: List[PermissionType]) -> Dict[PermissionType, bool]:
        """Check multiple permissions for a user efficiently."""
        results = {}
        
        for permission in permissions:
            check_result = await self.rbac_manager.check_permission(user_id, permission)
            results[permission] = check_result.granted
        
        return results
    
    async def get_user_accessible_endpoints(self, user_id: str) -> List[EndpointPermission]:
        """Get list of endpoints accessible to a user."""
        accessible_endpoints = []
        
        for endpoint_perm in self.endpoint_permissions.values():
            # Check if user has all required permissions
            has_access = True
            for permission in endpoint_perm.required_permissions:
                check_result = await self.rbac_manager.check_permission(user_id, permission)
                if not check_result.granted:
                    has_access = False
                    break
            
            if has_access:
                accessible_endpoints.append(endpoint_perm)
        
        return accessible_endpoints
    
    async def get_permission_analytics(self) -> Dict[str, Any]:
        """Get comprehensive permission enforcement analytics."""
        total_checks = len(self.permission_checks)
        if total_checks == 0:
            return {"status": "no_data"}
        
        recent_checks = self.permission_checks[-1000:]  # Last 1000 checks
        
        allowed_count = sum(1 for check in recent_checks if check.allowed)
        denied_count = len(recent_checks) - allowed_count
        
        # Response time statistics
        response_times = [check.response_time_ms for check in recent_checks]
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        
        # Most accessed endpoints
        endpoint_counts = {}
        for check in recent_checks:
            key = f"{check.method}:{check.endpoint}"
            endpoint_counts[key] = endpoint_counts.get(key, 0) + 1
        
        # Most denied permissions
        denied_permissions = {}
        for check in recent_checks:
            if not check.allowed:
                for permission in check.permissions_denied:
                    denied_permissions[permission.value] = denied_permissions.get(permission.value, 0) + 1
        
        return {
            "total_checks": total_checks,
            "recent_checks": len(recent_checks),
            "access_stats": {
                "allowed": allowed_count,
                "denied": denied_count,
                "success_rate": (allowed_count / len(recent_checks)) * 100
            },
            "performance": {
                "average_response_time_ms": round(avg_response_time, 2),
                "max_response_time_ms": round(max_response_time, 2),
                "min_response_time_ms": round(min_response_time, 2),
                "cache_hit_rate": (self.performance_stats["cache_hits"] / self.performance_stats["total_checks"]) * 100 if self.performance_stats["total_checks"] > 0 else 0
            },
            "endpoints": {
                "total_registered": len(self.endpoint_permissions),
                "most_accessed": sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            },
            "permissions": {
                "most_denied": sorted(denied_permissions.items(), key=lambda x: x[1], reverse=True)[:10]
            }
        }
    
    # Private helper methods
    
    async def _find_matching_endpoint_permission(self, context: PermissionContext) -> Optional[EndpointPermission]:
        """Find endpoint permission using pattern matching."""
        for endpoint_perm in self.endpoint_permissions.values():
            if self._endpoint_matches_pattern(context.endpoint, context.method, endpoint_perm):
                return endpoint_perm
        return None
    
    def _endpoint_matches_pattern(self, endpoint: str, method: str, endpoint_perm: EndpointPermission) -> bool:
        """Check if endpoint matches permission pattern (e.g., /users/{id})."""
        if endpoint_perm.method != method:
            return False
        
        # Simple pattern matching - can be enhanced
        pattern_parts = endpoint_perm.endpoint.split('/')
        endpoint_parts = endpoint.split('/')
        
        if len(pattern_parts) != len(endpoint_parts):
            return False
        
        for pattern_part, endpoint_part in zip(pattern_parts, endpoint_parts):
            if pattern_part.startswith('{') and pattern_part.endswith('}'):
                continue  # Wildcard match
            if pattern_part != endpoint_part:
                return False
        
        return True
    
    async def _check_bypass_conditions(self, bypass_conditions: List[str], 
                                     context: PermissionContext, 
                                     auth_result: AuthResult) -> bool:
        """Check if any bypass conditions are met."""
        for condition in bypass_conditions:
            if condition == "admin_override" and "admin" in [role.value for role in auth_result.metadata.get("roles", [])]:
                return True
            elif condition == "same_user" and context.request_data.get("user_id") == auth_result.user_id:
                return True
            elif condition == "system_internal" and context.client_ip in ["127.0.0.1", "localhost"]:
                return True
        
        return False
    
    async def _check_permission_cache(self, context: PermissionContext, 
                                    access_token: str) -> Optional[PermissionResult]:
        """Check if permission result is cached."""
        cache_key = f"{access_token}:{context.method}:{context.endpoint}"
        
        if cache_key in self.permission_cache:
            result, cached_at = self.permission_cache[cache_key]
            
            # Check if cache is still valid
            if (datetime.utcnow() - cached_at).total_seconds() < self.cache_ttl:
                self.performance_stats["cache_hits"] += 1
                return result
            else:
                # Remove expired cache entry
                del self.permission_cache[cache_key]
        
        return None
    
    async def _cache_permission_result(self, context: PermissionContext, 
                                     access_token: str, result: PermissionResult) -> None:
        """Cache permission result."""
        cache_key = f"{access_token}:{context.method}:{context.endpoint}"
        self.permission_cache[cache_key] = (result, datetime.utcnow())
        
        # Clean up old cache entries
        if len(self.permission_cache) > 10000:
            # Remove oldest 1000 entries
            sorted_cache = sorted(self.permission_cache.items(), key=lambda x: x[1][1])
            for key, _ in sorted_cache[:1000]:
                del self.permission_cache[key]
    
    async def _log_permission_enforcement(self, result: PermissionResult, context: PermissionContext) -> None:
        """Log permission enforcement event."""
        log_entry = {
            "event_id": str(uuid.uuid4()),
            "event_type": "permission_enforcement",
            "user_id": result.user_id,
            "endpoint": result.endpoint,
            "method": result.method,
            "allowed": result.allowed,
            "reason": result.reason,
            "permissions_checked": [p.value for p in result.permissions_checked],
            "permissions_denied": [p.value for p in result.permissions_denied],
            "response_time_ms": result.response_time_ms,
            "client_ip": context.client_ip,
            "user_agent": context.user_agent,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Log to audit trail (in production, this would go to a proper audit system)
        if result.allowed:
            logger.info(f"Permission granted: {result.user_id} -> {result.method} {result.endpoint}")
        else:
            logger.warning(f"Permission denied: {result.user_id} -> {result.method} {result.endpoint} - {result.reason}")
    
    def _update_performance_stats(self, result: PermissionResult) -> None:
        """Update performance statistics."""
        self.performance_stats["total_checks"] += 1
        
        if not result.allowed:
            self.performance_stats["denied_requests"] += 1
        
        # Update average response time
        current_avg = self.performance_stats["average_response_time_ms"]
        total_checks = self.performance_stats["total_checks"]
        
        new_avg = ((current_avg * (total_checks - 1)) + result.response_time_ms) / total_checks
        self.performance_stats["average_response_time_ms"] = new_avg
        
        # Store result for analytics
        self.permission_checks.append(result)
        
        # Keep only last 10000 checks to prevent memory issues
        if len(self.permission_checks) > 10000:
            self.permission_checks = self.permission_checks[-5000:]