"""
Enhanced RBAC Middleware with PostgreSQL Backend and Redis Caching

Integrates with Security Agent's database models and provides high-performance
authorization with Redis caching, comprehensive audit logging, and seamless
coordination between database persistence and caching layers.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import sessionmaker
import redis
import hashlib

from .models import ApiRequest
from .rbac_postgres_manager import PostgreSQLRBACManager
from .rbac_framework import ResourceType, ActionType
from .rbac_middleware import (
    AuthorizationContext, AuthorizationResult, ResourceMapper, 
    AuditLogger as BaseAuditLogger
)
from .auth_middleware import AuthResult, AuthenticationMiddleware

# Import Security Agent's database models
import sys
sys.path.append('../security-Jul-17-0944')
from external_api.database_models import User, AuditLog

logger = logging.getLogger(__name__)


class PostgreSQLAuditLogger(BaseAuditLogger):
    """Enhanced audit logger with PostgreSQL persistence and Redis caching."""
    
    def __init__(self, session_factory: sessionmaker, redis_client: redis.Redis = None):
        super().__init__(redis_client)
        self.session_factory = session_factory
        self.redis_client = redis_client
    
    async def log_authorization(self, result: AuthorizationResult) -> None:
        """Log authorization decision to PostgreSQL and Redis."""
        
        # Log to database
        try:
            with self.session_factory() as session:
                # Get user by username
                user = session.query(User).filter_by(username=result.user_id).first()
                if user:
                    audit_log = AuditLog(
                        user_id=user.id,
                        resource_type=result.context.resource_type.value,
                        action=result.context.action.value,
                        resource_id=result.context.resource_id,
                        authorized=result.authorized,
                        reason=result.reason,
                        permissions_used=result.permissions_used,
                        client_ip=result.context.request_ip,
                        user_agent=result.context.user_agent,
                        request_context=result.metadata or {}
                    )
                    session.add(audit_log)
                    session.commit()
                    
        except Exception as e:
            logger.error(f"Error logging to database: {e}")
        
        # Log to Redis and standard logger
        await super().log_authorization(result)
    
    async def get_database_audit_logs(self, user_id: str = None,
                                     resource_type: ResourceType = None,
                                     start_date: datetime = None,
                                     end_date: datetime = None,
                                     authorized: bool = None,
                                     limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit logs from PostgreSQL database."""
        logs = []
        
        try:
            with self.session_factory() as session:
                query = session.query(AuditLog)
                
                # Apply filters
                if user_id:
                    user = session.query(User).filter_by(username=user_id).first()
                    if user:
                        query = query.filter(AuditLog.user_id == user.id)
                
                if resource_type:
                    query = query.filter(AuditLog.resource_type == resource_type.value)
                
                if start_date:
                    query = query.filter(AuditLog.created_at >= start_date)
                
                if end_date:
                    query = query.filter(AuditLog.created_at <= end_date)
                
                if authorized is not None:
                    query = query.filter(AuditLog.authorized == authorized)
                
                # Order by most recent first
                query = query.order_by(AuditLog.created_at.desc())
                
                # Apply limit
                audit_logs = query.limit(limit).all()
                
                logs = [log.to_dict() for log in audit_logs]
                
        except Exception as e:
            logger.error(f"Error retrieving database audit logs: {e}")
        
        return logs
    
    async def get_audit_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get audit analytics from PostgreSQL."""
        analytics = {}
        
        try:
            with self.session_factory() as session:
                # Get date range
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                
                # Total requests
                total_requests = session.query(AuditLog).filter(
                    AuditLog.created_at >= start_date
                ).count()
                
                # Authorized vs denied
                authorized_count = session.query(AuditLog).filter(
                    AuditLog.created_at >= start_date,
                    AuditLog.authorized == True
                ).count()
                
                denied_count = total_requests - authorized_count
                
                # Top users
                top_users = session.query(
                    User.username, 
                    func.count(AuditLog.id).label('request_count')
                ).join(AuditLog).filter(
                    AuditLog.created_at >= start_date
                ).group_by(User.username).order_by(
                    func.count(AuditLog.id).desc()
                ).limit(10).all()
                
                # Top resources
                top_resources = session.query(
                    AuditLog.resource_type,
                    func.count(AuditLog.id).label('request_count')
                ).filter(
                    AuditLog.created_at >= start_date
                ).group_by(AuditLog.resource_type).order_by(
                    func.count(AuditLog.id).desc()
                ).limit(10).all()
                
                # Top actions
                top_actions = session.query(
                    AuditLog.action,
                    func.count(AuditLog.id).label('request_count')
                ).filter(
                    AuditLog.created_at >= start_date
                ).group_by(AuditLog.action).order_by(
                    func.count(AuditLog.id).desc()
                ).limit(10).all()
                
                analytics = {
                    "period_days": days,
                    "total_requests": total_requests,
                    "authorized_requests": authorized_count,
                    "denied_requests": denied_count,
                    "authorization_rate": authorized_count / max(1, total_requests),
                    "denial_rate": denied_count / max(1, total_requests),
                    "top_users": [{"username": u, "count": c} for u, c in top_users],
                    "top_resources": [{"resource_type": r, "count": c} for r, c in top_resources],
                    "top_actions": [{"action": a, "count": c} for a, c in top_actions]
                }
                
        except Exception as e:
            logger.error(f"Error getting audit analytics: {e}")
            analytics = {"error": str(e)}
        
        return analytics


class PostgreSQLRBACMiddleware:
    """Enhanced RBAC middleware with PostgreSQL backend and Redis caching."""
    
    def __init__(self, session_factory: sessionmaker, 
                 auth_middleware: AuthenticationMiddleware,
                 redis_client: redis.Redis = None):
        """Initialize PostgreSQL RBAC middleware."""
        self.session_factory = session_factory
        self.auth_middleware = auth_middleware
        self.redis_client = redis_client
        
        # Initialize RBAC manager
        self.rbac_manager = PostgreSQLRBACManager(session_factory, redis_client)
        
        # Initialize components
        self.resource_mapper = ResourceMapper()
        self.audit_logger = PostgreSQLAuditLogger(session_factory, redis_client)
        
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
            "cache_hit_rate": 0,
            "database_queries": 0,
            "cache_lookups": 0
        }
        
        # Cache for frequent permission checks
        self.permission_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def authorize_request(self, request: ApiRequest) -> AuthorizationResult:
        """Authorize an API request using PostgreSQL RBAC with Redis caching."""
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
            
            # Check permission with caching
            has_permission = await self._check_permission_with_cache(
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
                    "response_time_ms": (time.time() - start_time) * 1000,
                    "cache_hit": self._was_cache_hit(auth_result.user_id, resource_type, action)
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
    
    async def _check_permission_with_cache(self, user_id: str, resource_type: ResourceType,
                                          action: ActionType, resource_id: Optional[str] = None,
                                          context: Optional[Dict[str, Any]] = None) -> bool:
        """Check permission with Redis and in-memory caching."""
        
        # Generate cache key
        cache_key = self._generate_cache_key(user_id, resource_type, action, resource_id, context)
        
        # Check in-memory cache first
        if cache_key in self.permission_cache:
            cached_result, timestamp = self.permission_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                self.metrics["cache_lookups"] += 1
                return cached_result
        
        # Check Redis cache
        if self.redis_client:
            try:
                redis_key = f"rbac:permission:{cache_key}"
                cached_result = self.redis_client.get(redis_key)
                if cached_result:
                    result = json.loads(cached_result)
                    self.metrics["cache_lookups"] += 1
                    
                    # Update in-memory cache
                    self.permission_cache[cache_key] = (result["allowed"], time.time())
                    
                    return result["allowed"]
            except Exception as e:
                logger.error(f"Error checking Redis cache: {e}")
        
        # Cache miss - check database
        self.metrics["database_queries"] += 1
        result = self.rbac_manager.check_permission(user_id, resource_type, action, resource_id, context)
        
        # Cache the result
        try:
            # In-memory cache
            self.permission_cache[cache_key] = (result, time.time())
            
            # Redis cache
            if self.redis_client:
                redis_key = f"rbac:permission:{cache_key}"
                cache_data = {
                    "allowed": result,
                    "timestamp": time.time(),
                    "user_id": user_id
                }
                self.redis_client.setex(redis_key, self.cache_ttl, json.dumps(cache_data))
        
        except Exception as e:
            logger.error(f"Error caching permission result: {e}")
        
        return result
    
    def _generate_cache_key(self, user_id: str, resource_type: ResourceType,
                           action: ActionType, resource_id: Optional[str] = None,
                           context: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key for permission checks."""
        key_parts = [user_id, resource_type.value, action.value, resource_id or ""]
        if context:
            context_str = json.dumps(context, sort_keys=True)
            key_parts.append(hashlib.md5(context_str.encode()).hexdigest())
        return ":".join(key_parts)
    
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
            "request_time": datetime.utcnow().isoformat(),
            "request_id": request.headers.get("X-Request-ID", ""),
            "client_id": auth_result.metadata.get("client_id")
        }
    
    def _get_permissions_used(self, user_id: str, resource_type: ResourceType, action: ActionType) -> List[str]:
        """Get list of permissions that were used in the decision."""
        return [f"{resource_type.value}:{action.value}"]
    
    def _was_cache_hit(self, user_id: str, resource_type: ResourceType, action: ActionType) -> bool:
        """Check if the last permission check was a cache hit."""
        cache_key = self._generate_cache_key(user_id, resource_type, action)
        return cache_key in self.permission_cache
    
    # Cache Management
    
    async def invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate cache for a specific user."""
        # Clear in-memory cache
        keys_to_remove = [key for key in self.permission_cache.keys() if key.startswith(user_id)]
        for key in keys_to_remove:
            del self.permission_cache[key]
        
        # Clear Redis cache
        if self.redis_client:
            try:
                pattern = f"rbac:permission:{user_id}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                logger.error(f"Error clearing Redis cache for user {user_id}: {e}")
    
    async def invalidate_role_cache(self, role_name: str) -> None:
        """Invalidate cache for users with a specific role."""
        # Get users with this role
        users_with_role = self.rbac_manager.get_users_with_role(role_name)
        
        # Invalidate cache for each user
        for user in users_with_role:
            await self.invalidate_user_cache(user.user_id)
    
    async def clear_all_caches(self) -> None:
        """Clear all caches."""
        # Clear in-memory cache
        self.permission_cache.clear()
        
        # Clear Redis cache
        if self.redis_client:
            try:
                pattern = "rbac:permission:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                logger.error(f"Error clearing Redis cache: {e}")
        
        # Clear RBAC manager caches
        self.rbac_manager.clear_all_caches()
    
    # Bulk Operations
    
    async def bulk_authorize_requests(self, requests: List[ApiRequest]) -> List[AuthorizationResult]:
        """Authorize multiple requests efficiently."""
        results = []
        
        for request in requests:
            result = await self.authorize_request(request)
            results.append(result)
        
        return results
    
    async def bulk_check_permissions(self, user_id: str, 
                                   permission_requests: List[Tuple[ResourceType, ActionType, Optional[str]]]) -> Dict[str, bool]:
        """Check multiple permissions for a single user."""
        results = {}
        
        for resource_type, action, resource_id in permission_requests:
            has_permission = await self._check_permission_with_cache(
                user_id, resource_type, action, resource_id
            )
            key = f"{resource_type.value}:{action.value}:{resource_id or '*'}"
            results[key] = has_permission
        
        return results
    
    # Analytics and Reporting
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get authorization metrics."""
        cache_hit_rate = 0
        if self.metrics["cache_lookups"] > 0:
            cache_hit_rate = self.metrics["cache_lookups"] / (
                self.metrics["cache_lookups"] + self.metrics["database_queries"]
            )
        
        return {
            **self.metrics,
            "authorization_rate": self.metrics["authorized_requests"] / max(1, self.metrics["total_requests"]),
            "denial_rate": self.metrics["denied_requests"] / max(1, self.metrics["total_requests"]),
            "cache_hit_rate": cache_hit_rate,
            "cache_sizes": {
                "in_memory": len(self.permission_cache),
                "redis": self._get_redis_cache_size()
            }
        }
    
    def _get_redis_cache_size(self) -> int:
        """Get Redis cache size."""
        if self.redis_client:
            try:
                return len(self.redis_client.keys("rbac:permission:*"))
            except Exception as e:
                logger.error(f"Error getting Redis cache size: {e}")
        return 0
    
    async def get_audit_summary(self) -> Dict[str, Any]:
        """Get comprehensive audit summary."""
        # Get database analytics
        db_analytics = await self.audit_logger.get_audit_analytics()
        
        # Get Redis analytics
        redis_analytics = await self.audit_logger.get_audit_stats()
        
        # Combine metrics
        return {
            "database_analytics": db_analytics,
            "redis_analytics": redis_analytics,
            "middleware_metrics": self.get_metrics(),
            "rbac_stats": self.rbac_manager.get_stats()
        }
    
    # Configuration Management
    
    def add_bypass_path(self, path: str) -> None:
        """Add a path that bypasses authentication."""
        if path not in self.bypass_auth_paths:
            self.bypass_auth_paths.append(path)
    
    def remove_bypass_path(self, path: str) -> None:
        """Remove a path from bypass list."""
        if path in self.bypass_auth_paths:
            self.bypass_auth_paths.remove(path)
    
    def update_cache_ttl(self, ttl: int) -> None:
        """Update cache TTL."""
        self.cache_ttl = ttl
    
    # Health Checks
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components."""
        health = {
            "status": "healthy",
            "components": {}
        }
        
        # Check PostgreSQL
        try:
            with self.session_factory() as session:
                session.execute("SELECT 1")
            health["components"]["postgresql"] = {"status": "healthy"}
        except Exception as e:
            health["components"]["postgresql"] = {"status": "unhealthy", "error": str(e)}
            health["status"] = "unhealthy"
        
        # Check Redis
        if self.redis_client:
            try:
                self.redis_client.ping()
                health["components"]["redis"] = {"status": "healthy"}
            except Exception as e:
                health["components"]["redis"] = {"status": "unhealthy", "error": str(e)}
                # Redis is optional, so don't mark overall as unhealthy
        
        # Check RBAC manager
        try:
            stats = self.rbac_manager.get_stats()
            health["components"]["rbac_manager"] = {"status": "healthy", "stats": stats}
        except Exception as e:
            health["components"]["rbac_manager"] = {"status": "unhealthy", "error": str(e)}
            health["status"] = "unhealthy"
        
        return health