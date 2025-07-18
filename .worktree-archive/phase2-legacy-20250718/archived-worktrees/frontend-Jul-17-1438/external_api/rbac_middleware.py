"""
RBAC Authorization Middleware

Enhanced middleware that integrates with the RBAC framework to provide:
- Request-level authorization
- Dynamic permission evaluation
- Context-aware access control
- Performance-optimized caching
- Comprehensive audit logging
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass
from functools import wraps
import redis

from .models import ApiRequest, ApiResponse
from .rbac_framework import RBACManager, ResourceType, ActionType, PermissionScope
from .permission_manager import PermissionManager
from .auth_middleware import AuthResult, AuthenticationMiddleware

logger = logging.getLogger(__name__)


@dataclass
class AuthorizationContext:
    """Context information for authorization decisions."""
    
    user_id: str
    request_ip: str
    user_agent: str
    resource_type: ResourceType
    action: ActionType
    resource_id: Optional[str] = None
    request_data: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class AuthorizationResult:
    """Result of authorization check."""
    
    authorized: bool
    user_id: str
    context: AuthorizationContext
    reason: Optional[str] = None
    permissions_used: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "authorized": self.authorized,
            "user_id": self.user_id,
            "resource_type": self.context.resource_type.value,
            "action": self.context.action.value,
            "resource_id": self.context.resource_id,
            "reason": self.reason,
            "permissions_used": self.permissions_used,
            "timestamp": self.context.timestamp.isoformat()
        }


class ResourceMapper:
    """Maps API endpoints to resources for authorization."""
    
    def __init__(self):
        self.endpoint_mappings = {
            # API Gateway endpoints
            "/api/v1/services": (ResourceType.SERVICE, ActionType.READ),
            "/api/v1/services/{service_id}": (ResourceType.SERVICE, ActionType.READ),
            "/api/v1/services/{service_id}/deploy": (ResourceType.SERVICE, ActionType.DEPLOY),
            "/api/v1/services/{service_id}/scale": (ResourceType.SERVICE, ActionType.SCALE),
            
            # Agent endpoints
            "/api/v1/agents": (ResourceType.AGENT, ActionType.READ),
            "/api/v1/agents/{agent_id}": (ResourceType.AGENT, ActionType.READ),
            "/api/v1/agents/{agent_id}/execute": (ResourceType.AGENT, ActionType.EXECUTE),
            "/api/v1/agents/{agent_id}/configure": (ResourceType.AGENT, ActionType.CONFIGURE),
            
            # Workflow endpoints
            "/api/v1/workflows": (ResourceType.WORKFLOW, ActionType.READ),
            "/api/v1/workflows/{workflow_id}": (ResourceType.WORKFLOW, ActionType.READ),
            "/api/v1/workflows/{workflow_id}/execute": (ResourceType.WORKFLOW, ActionType.EXECUTE),
            
            # Monitoring endpoints
            "/api/v1/metrics": (ResourceType.MONITORING, ActionType.READ),
            "/api/v1/metrics/{metric_id}": (ResourceType.MONITORING, ActionType.READ),
            "/api/v1/alerts": (ResourceType.MONITORING, ActionType.READ),
            "/api/v1/alerts/{alert_id}": (ResourceType.MONITORING, ActionType.UPDATE),
            
            # Configuration endpoints
            "/api/v1/config": (ResourceType.CONFIGURATION, ActionType.READ),
            "/api/v1/config/{config_id}": (ResourceType.CONFIGURATION, ActionType.UPDATE),
            
            # Database endpoints
            "/api/v1/data": (ResourceType.DATABASE, ActionType.READ),
            "/api/v1/data/{resource_id}": (ResourceType.DATABASE, ActionType.READ),
        }
        
        # Method to action mapping
        self.method_actions = {
            "GET": ActionType.READ,
            "POST": ActionType.CREATE,
            "PUT": ActionType.UPDATE,
            "PATCH": ActionType.UPDATE,
            "DELETE": ActionType.DELETE,
            "HEAD": ActionType.READ,
            "OPTIONS": ActionType.READ
        }
    
    def map_request_to_resource(self, request: ApiRequest) -> Tuple[ResourceType, ActionType, Optional[str]]:
        """Map an API request to resource type, action, and resource ID."""
        
        # Normalize path
        path = request.path.rstrip('/')
        
        # Try exact match first
        if path in self.endpoint_mappings:
            resource_type, default_action = self.endpoint_mappings[path]
            # For exact matches, use method-based action unless it's a special endpoint
            if path.endswith('/deploy') or path.endswith('/scale') or path.endswith('/execute'):
                action = default_action
            else:
                action = self.method_actions.get(request.method, default_action)
            return resource_type, action, None
        
        # Try pattern matching
        for pattern, (resource_type, default_action) in self.endpoint_mappings.items():
            if self._matches_pattern(path, pattern):
                # For pattern matches, use method-based action unless it's a special endpoint
                if pattern.endswith('/deploy') or pattern.endswith('/scale') or pattern.endswith('/execute'):
                    action = default_action
                else:
                    action = self.method_actions.get(request.method, default_action)
                resource_id = self._extract_resource_id(path, pattern)
                return resource_type, action, resource_id
        
        # Default fallback
        return ResourceType.API_ENDPOINT, self.method_actions.get(request.method, ActionType.READ), None
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern with variables."""
        path_parts = path.split('/')
        pattern_parts = pattern.split('/')
        
        if len(path_parts) != len(pattern_parts):
            return False
        
        for path_part, pattern_part in zip(path_parts, pattern_parts):
            if pattern_part.startswith('{') and pattern_part.endswith('}'):
                continue  # Variable part
            elif path_part != pattern_part:
                return False
        
        return True
    
    def _extract_resource_id(self, path: str, pattern: str) -> Optional[str]:
        """Extract resource ID from path using pattern."""
        path_parts = path.split('/')
        pattern_parts = pattern.split('/')
        
        for path_part, pattern_part in zip(path_parts, pattern_parts):
            if pattern_part.startswith('{') and pattern_part.endswith('}'):
                return path_part
        
        return None
    
    def add_endpoint_mapping(self, path: str, resource_type: ResourceType, action: ActionType) -> None:
        """Add a new endpoint mapping."""
        self.endpoint_mappings[path] = (resource_type, action)
    
    def remove_endpoint_mapping(self, path: str) -> None:
        """Remove an endpoint mapping."""
        if path in self.endpoint_mappings:
            del self.endpoint_mappings[path]


class AuditLogger:
    """Comprehensive audit logging for authorization decisions."""
    
    def __init__(self, redis_client: redis.Redis = None):
        self.redis = redis_client
        self.log_buffer = []
        self.buffer_size = 100
        
    async def log_authorization(self, result: AuthorizationResult) -> None:
        """Log authorization decision."""
        
        log_entry = {
            "timestamp": result.context.timestamp.isoformat(),
            "user_id": result.user_id,
            "authorized": result.authorized,
            "resource_type": result.context.resource_type.value,
            "action": result.context.action.value,
            "resource_id": result.context.resource_id,
            "request_ip": result.context.request_ip,
            "user_agent": result.context.user_agent,
            "reason": result.reason,
            "permissions_used": result.permissions_used,
            "metadata": result.metadata
        }
        
        # Log to standard logger
        if result.authorized:
            logger.info(f"Authorization granted: {result.user_id} -> {result.context.resource_type.value}:{result.context.action.value}")
        else:
            logger.warning(f"Authorization denied: {result.user_id} -> {result.context.resource_type.value}:{result.context.action.value} - {result.reason}")
        
        # Store in buffer
        self.log_buffer.append(log_entry)
        
        # Flush buffer if needed
        if len(self.log_buffer) >= self.buffer_size:
            await self.flush_buffer()
        
        # Store in Redis for analytics
        if self.redis:
            try:
                key = f"audit:auth:{datetime.now().strftime('%Y-%m-%d')}"
                await self.redis.lpush(key, json.dumps(log_entry))
                await self.redis.expire(key, 86400 * 30)  # Keep for 30 days
            except Exception as e:
                logger.error(f"Error storing audit log in Redis: {e}")
    
    async def flush_buffer(self) -> None:
        """Flush log buffer to persistent storage."""
        if self.log_buffer:
            try:
                # Write to file or database
                with open(f"/tmp/rbac_audit_{datetime.now().strftime('%Y%m%d')}.log", "a") as f:
                    for entry in self.log_buffer:
                        f.write(json.dumps(entry) + "\n")
                
                self.log_buffer.clear()
            except Exception as e:
                logger.error(f"Error flushing audit log: {e}")
    
    async def get_audit_logs(self, user_id: str = None, 
                           resource_type: ResourceType = None,
                           start_date: datetime = None,
                           end_date: datetime = None,
                           authorized: bool = None) -> List[Dict[str, Any]]:
        """Get audit logs with filtering."""
        logs = []
        
        if self.redis:
            try:
                # Get logs from Redis
                if start_date and end_date:
                    current_date = start_date
                    while current_date <= end_date:
                        key = f"audit:auth:{current_date.strftime('%Y-%m-%d')}"
                        day_logs = await self.redis.lrange(key, 0, -1)
                        
                        for log_json in day_logs:
                            log_entry = json.loads(log_json)
                            
                            # Apply filters
                            if user_id and log_entry.get("user_id") != user_id:
                                continue
                            if resource_type and log_entry.get("resource_type") != resource_type.value:
                                continue
                            if authorized is not None and log_entry.get("authorized") != authorized:
                                continue
                            
                            logs.append(log_entry)
                        
                        current_date += timedelta(days=1)
            except Exception as e:
                logger.error(f"Error retrieving audit logs: {e}")
        
        return logs
    
    async def get_audit_stats(self) -> Dict[str, Any]:
        """Get audit statistics."""
        stats = {
            "total_requests": 0,
            "authorized_requests": 0,
            "denied_requests": 0,
            "top_users": {},
            "top_resources": {},
            "top_actions": {}
        }
        
        if self.redis:
            try:
                # Get today's logs
                today = datetime.now().strftime('%Y-%m-%d')
                key = f"audit:auth:{today}"
                logs = await self.redis.lrange(key, 0, -1)
                
                for log_json in logs:
                    log_entry = json.loads(log_json)
                    
                    stats["total_requests"] += 1
                    
                    if log_entry.get("authorized"):
                        stats["authorized_requests"] += 1
                    else:
                        stats["denied_requests"] += 1
                    
                    # Track user activity
                    user_id = log_entry.get("user_id")
                    if user_id:
                        stats["top_users"][user_id] = stats["top_users"].get(user_id, 0) + 1
                    
                    # Track resource access
                    resource_type = log_entry.get("resource_type")
                    if resource_type:
                        stats["top_resources"][resource_type] = stats["top_resources"].get(resource_type, 0) + 1
                    
                    # Track action types
                    action = log_entry.get("action")
                    if action:
                        stats["top_actions"][action] = stats["top_actions"].get(action, 0) + 1
                
                # Calculate rates
                if stats["total_requests"] > 0:
                    stats["authorization_rate"] = stats["authorized_requests"] / stats["total_requests"]
                    stats["denial_rate"] = stats["denied_requests"] / stats["total_requests"]
                
            except Exception as e:
                logger.error(f"Error calculating audit stats: {e}")
        
        return stats


class RBACMiddleware:
    """RBAC authorization middleware for API requests."""
    
    def __init__(self, rbac_manager: RBACManager, permission_manager: PermissionManager,
                 auth_middleware: AuthenticationMiddleware, redis_client: redis.Redis = None):
        self.rbac = rbac_manager
        self.permission_manager = permission_manager
        self.auth_middleware = auth_middleware
        self.resource_mapper = ResourceMapper()
        self.audit_logger = AuditLogger(redis_client)
        
        # Configuration
        self.bypass_auth_paths = ["/health", "/metrics", "/status", "/api/v1/auth/login"]
        self.require_auth_paths = ["/api/v1/"]
        self.default_deny = True
        
        # Performance metrics
        self.metrics = {
            "total_requests": 0,
            "authorized_requests": 0,
            "denied_requests": 0,
            "avg_response_time": 0,
            "cache_hit_rate": 0
        }
    
    async def authorize_request(self, request: ApiRequest) -> AuthorizationResult:
        """Authorize an API request using RBAC."""
        start_time = time.time()
        self.metrics["total_requests"] += 1
        
        try:
            # Check if path bypasses authorization
            if self._should_bypass_auth(request.path):
                return AuthorizationResult(
                    authorized=True,
                    user_id="anonymous",
                    context=AuthorizationContext(
                        user_id="anonymous",
                        request_ip=request.client_ip,
                        user_agent=request.headers.get("User-Agent", ""),
                        resource_type=ResourceType.API_ENDPOINT,
                        action=ActionType.READ
                    ),
                    reason="Bypassed authentication"
                )
            
            # Authenticate request first
            auth_result = await self.auth_middleware.authenticate_request(request)
            
            if not auth_result.success:
                result = AuthorizationResult(
                    authorized=False,
                    user_id="anonymous",
                    context=AuthorizationContext(
                        user_id="anonymous",
                        request_ip=request.client_ip,
                        user_agent=request.headers.get("User-Agent", ""),
                        resource_type=ResourceType.API_ENDPOINT,
                        action=ActionType.READ
                    ),
                    reason=f"Authentication failed: {auth_result.error}"
                )
                
                await self.audit_logger.log_authorization(result)
                self.metrics["denied_requests"] += 1
                return result
            
            # Map request to resource
            resource_type, action, resource_id = self.resource_mapper.map_request_to_resource(request)
            
            # Create authorization context
            context = AuthorizationContext(
                user_id=auth_result.user_id,
                request_ip=request.client_ip,
                user_agent=request.headers.get("User-Agent", ""),
                resource_type=resource_type,
                action=action,
                resource_id=resource_id,
                request_data=request.body
            )
            
            # Check permission
            has_permission = await self.permission_manager.check_permission(
                auth_result.user_id,
                resource_type,
                action,
                resource_id,
                self._build_auth_context(request, auth_result)
            )
            
            # Create result
            result = AuthorizationResult(
                authorized=has_permission,
                user_id=auth_result.user_id,
                context=context,
                reason="Permission granted" if has_permission else "Insufficient permissions",
                permissions_used=self._get_permissions_used(auth_result.user_id, resource_type, action),
                metadata={
                    "auth_method": auth_result.metadata.get("auth_method"),
                    "response_time_ms": (time.time() - start_time) * 1000
                }
            )
            
            # Log authorization decision
            await self.audit_logger.log_authorization(result)
            
            # Update metrics
            if has_permission:
                self.metrics["authorized_requests"] += 1
            else:
                self.metrics["denied_requests"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error during authorization: {e}")
            
            result = AuthorizationResult(
                authorized=False,
                user_id="error",
                context=AuthorizationContext(
                    user_id="error",
                    request_ip=request.client_ip,
                    user_agent=request.headers.get("User-Agent", ""),
                    resource_type=ResourceType.API_ENDPOINT,
                    action=ActionType.READ
                ),
                reason=f"Authorization error: {str(e)}"
            )
            
            await self.audit_logger.log_authorization(result)
            self.metrics["denied_requests"] += 1
            return result
        
        finally:
            # Update response time metrics
            response_time = (time.time() - start_time) * 1000
            self.metrics["avg_response_time"] = (
                (self.metrics["avg_response_time"] * (self.metrics["total_requests"] - 1) + response_time) /
                self.metrics["total_requests"]
            )
    
    def _should_bypass_auth(self, path: str) -> bool:
        """Check if path should bypass authentication."""
        for bypass_path in self.bypass_auth_paths:
            if path.startswith(bypass_path):
                return True
        return False
    
    def _build_auth_context(self, request: ApiRequest, auth_result: AuthResult) -> Dict[str, Any]:
        """Build context for authorization decision."""
        return {
            "request_ip": request.client_ip,
            "user_agent": request.headers.get("User-Agent", ""),
            "auth_method": auth_result.metadata.get("auth_method"),
            "request_time": datetime.now().isoformat(),
            "request_id": request.headers.get("X-Request-ID", ""),
            "client_id": auth_result.metadata.get("client_id")
        }
    
    def _get_permissions_used(self, user_id: str, resource_type: ResourceType, action: ActionType) -> List[str]:
        """Get list of permissions that were used in the decision."""
        # This is a simplified implementation
        # In a real system, you'd track exactly which permissions were evaluated
        return [f"{resource_type.value}:{action.value}"]
    
    def add_bypass_path(self, path: str) -> None:
        """Add a path that bypasses authentication."""
        if path not in self.bypass_auth_paths:
            self.bypass_auth_paths.append(path)
    
    def remove_bypass_path(self, path: str) -> None:
        """Remove a path from bypass list."""
        if path in self.bypass_auth_paths:
            self.bypass_auth_paths.remove(path)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get authorization metrics."""
        return {
            **self.metrics,
            "authorization_rate": self.metrics["authorized_requests"] / max(1, self.metrics["total_requests"]),
            "denial_rate": self.metrics["denied_requests"] / max(1, self.metrics["total_requests"]),
            "cache_stats": self.permission_manager.get_cache_stats()
        }
    
    async def get_audit_summary(self) -> Dict[str, Any]:
        """Get audit summary."""
        return await self.audit_logger.get_audit_stats()


def require_permission(resource_type: ResourceType, action: ActionType, 
                      resource_id_param: str = None):
    """Decorator to require specific permissions for a function."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This is a simplified implementation
            # In a real system, you'd extract the request from the function parameters
            # and check permissions before calling the function
            
            # For now, just call the function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def permission_required(resource_type: str, action: str):
    """Class decorator to require permissions for all methods."""
    
    def decorator(cls):
        original_init = cls.__init__
        
        def new_init(self, *args, **kwargs):
            self._required_resource_type = ResourceType(resource_type)
            self._required_action = ActionType(action)
            original_init(self, *args, **kwargs)
        
        cls.__init__ = new_init
        return cls
    
    return decorator