"""
API Gateway for External API Integration

Provides a unified API interface for external systems to interact with
the LeanVibe Agent Hive orchestration system.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import asdict

from .models import (
    ApiGatewayConfig,
    ApiRequest,
    ApiResponse
)
from .service_discovery import ServiceDiscovery, ServiceInstance
from .auth_middleware import AuthenticationMiddleware, AuthResult


logger = logging.getLogger(__name__)


class ApiGateway:
    """
    API Gateway for routing and managing external API requests.

    Provides authentication, rate limiting, request validation,
    and response formatting for the orchestration system.
    
    Features:
    - JWT authentication integration
    - Rate limiting and security monitoring
    - Request/response validation
    - Service discovery integration
    - Comprehensive logging and metrics
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize API Gateway with JWT authentication."""
        self.config = config or self._get_default_config()
        
        # Initialize core components
        self.service_discovery = ServiceDiscovery(self.config.get("service_discovery", {}))
        self.auth_middleware = AuthenticationMiddleware(self.config.get("auth", {}))
        
        # Initialize JWT integration
        from .jwt_integration import JwtIntegrationService
        self.jwt_service = JwtIntegrationService(self.config.get("jwt", {}))
        
        # Gateway configuration
        self.gateway_config = ApiGatewayConfig(**self.config.get("gateway", {}))
        
        # Request tracking and metrics
        self.request_count = 0
        self.response_times = []
        self.error_count = 0
        self.active_requests: Dict[str, datetime] = {}
        
        # Route handlers
        self.route_handlers: Dict[str, Callable] = {}
        self.middleware_stack: List[Callable] = []
        
        # Security tracking
        self.blocked_ips: Set[str] = set()
        self.security_events: List[Dict[str, Any]] = []
        
        logger.info(f"API Gateway initialized on {self.gateway_config.host}:{self.gateway_config.port}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default API Gateway configuration."""
        return {
            "gateway": {
                "host": "localhost",
                "port": 8081,
                "api_prefix": "/api/v1",
                "enable_cors": True,
                "cors_origins": ["*"],
                "rate_limit_requests": 1000,
                "rate_limit_window": 3600,
                "auth_required": True,
                "request_timeout": 30
            },
            "jwt": {
                "jwt_secret": "your-secret-key-change-in-production",
                "jwt_algorithm": "HS256",
                "token_expiry_hours": 24,
                "rate_limit_requests_per_hour": 1000,
                "require_https": True,
                "auto_refresh_threshold_hours": 1,
                "protected_endpoints": ["/api/v1/agents", "/api/v1/tasks"],
                "public_endpoints": ["/health", "/metrics", "/api/v1/auth"]
            },
            "auth": {
                "enabled_methods": ["jwt"],
                "jwt_secret": "your-secret-key-change-in-production",
                "jwt_algorithm": "HS256",
                "token_expiry_hours": 24
            },
            "service_discovery": {
                "registry_host": "localhost",
                "registry_port": 8500,
                "health_check_interval": 30
            }
        }
    
    async def process_request(self, request: ApiRequest) -> ApiResponse:
        """
        Process incoming API request with full authentication and validation.
        """
        start_time = time.time()
        request_id = request.request_id
        
        try:
            # Track active request
            self.active_requests[request_id] = datetime.utcnow()
            self.request_count += 1
            
            # Check if IP is blocked
            if request.client_ip in self.blocked_ips:
                return self._create_error_response(
                    403, "IP address blocked due to security violations", request_id
                )
            
            # CORS handling
            if request.method == "OPTIONS":
                return self._handle_cors_preflight(request)
            
            # JWT Authentication
            auth_success, auth_metadata, auth_error = await self.jwt_service.authenticate_request(
                request=request,
                required_permissions=self._get_required_permissions(request.path)
            )
            
            if not auth_success:
                self.error_count += 1
                return auth_error
            
            # Add authentication metadata to request context
            request.headers["X-User-ID"] = auth_metadata.user_id or ""
            request.headers["X-User-Roles"] = ",".join(auth_metadata.roles)
            
            # Route request to appropriate handler
            response = await self._route_request(request)
            
            # Add CORS headers if enabled
            if self.gateway_config.enable_cors:
                response = self._add_cors_headers(response)
            
            # Add security headers
            response = self._add_security_headers(response)
            
            # Track response time
            processing_time = (time.time() - start_time) * 1000
            self.response_times.append(processing_time)
            response.processing_time = processing_time
            
            # Keep only last 1000 response times for metrics
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-500:]
            
            return response
            
        except Exception as e:
            logger.error(f"API Gateway error processing request {request_id}: {e}")
            self.error_count += 1
            return self._create_error_response(500, "Internal server error", request_id)
        
        finally:
            # Clean up active request tracking
            self.active_requests.pop(request_id, None)
    
    async def authenticate_user(self, username: str, password: str, client_ip: str) -> ApiResponse:
        """Authenticate user and return JWT tokens."""
        try:
            # Use the JWT service's underlying auth service
            auth_service = self.jwt_service.auth_service
            
            # Authenticate user
            success, message, session = await auth_service.authenticate_user(
                username=username,
                password=password,
                client_ip=client_ip,
                user_agent="API Gateway"
            )
            
            if success and session:
                return ApiResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body={
                        "access_token": session.access_token,
                        "refresh_token": session.refresh_token,
                        "token_type": "Bearer",
                        "expires_at": session.expires_at.isoformat(),
                        "user_id": session.user_id
                    },
                    timestamp=datetime.utcnow(),
                    processing_time=0.0,
                    request_id=str(uuid.uuid4())
                )
            else:
                return self._create_error_response(401, message, str(uuid.uuid4()))
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return self._create_error_response(500, "Authentication failed", str(uuid.uuid4()))
    
    async def refresh_user_token(self, refresh_token: str, client_ip: str) -> ApiResponse:
        """Refresh user JWT token."""
        try:
            success, new_access_token, new_refresh_token = await self.jwt_service.refresh_token(
                refresh_token=refresh_token,
                client_ip=client_ip
            )
            
            if success:
                return ApiResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body={
                        "access_token": new_access_token,
                        "refresh_token": new_refresh_token,
                        "token_type": "Bearer"
                    },
                    timestamp=datetime.utcnow(),
                    processing_time=0.0,
                    request_id=str(uuid.uuid4())
                )
            else:
                return self._create_error_response(401, "Token refresh failed", str(uuid.uuid4()))
                
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return self._create_error_response(500, "Token refresh failed", str(uuid.uuid4()))
    
    async def logout_user(self, token: str) -> ApiResponse:
        """Logout user and revoke token."""
        try:
            success = await self.jwt_service.revoke_token(token, "user_logout")
            
            if success:
                return ApiResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body={"message": "Logout successful"},
                    timestamp=datetime.utcnow(),
                    processing_time=0.0,
                    request_id=str(uuid.uuid4())
                )
            else:
                return self._create_error_response(400, "Logout failed", str(uuid.uuid4()))
                
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return self._create_error_response(500, "Logout failed", str(uuid.uuid4()))
    
    def register_route(self, path: str, handler: Callable, methods: List[str] = None) -> None:
        """Register route handler for specific path."""
        if methods is None:
            methods = ["GET"]
        
        for method in methods:
            route_key = f"{method}:{path}"
            self.route_handlers[route_key] = handler
            logger.info(f"Registered route: {route_key}")
    
    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to processing stack."""
        self.middleware_stack.append(middleware)
        logger.info(f"Added middleware: {middleware.__name__}")
    
    async def get_health_status(self) -> ApiResponse:
        """Get API Gateway health status."""
        try:
            # Get component health
            auth_stats = await self.jwt_service.get_authentication_stats()
            
            # Calculate service health
            avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
            error_rate = (self.error_count / max(1, self.request_count)) * 100
            
            health_status = {
                "status": "healthy" if error_rate < 5 else "degraded" if error_rate < 20 else "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "gateway": {
                    "total_requests": self.request_count,
                    "error_count": self.error_count,
                    "error_rate_percent": round(error_rate, 2),
                    "avg_response_time_ms": round(avg_response_time, 2),
                    "active_requests": len(self.active_requests),
                    "blocked_ips": len(self.blocked_ips)
                },
                "authentication": auth_stats,
                "configuration": {
                    "auth_required": self.gateway_config.auth_required,
                    "cors_enabled": self.gateway_config.enable_cors,
                    "rate_limiting": f"{self.gateway_config.rate_limit_requests}/{self.gateway_config.rate_limit_window}s"
                }
            }
            
            return ApiResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=health_status,
                timestamp=datetime.utcnow(),
                processing_time=0.0,
                request_id=str(uuid.uuid4())
            )
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return self._create_error_response(500, "Health check failed", str(uuid.uuid4()))
    
    async def get_metrics(self) -> ApiResponse:
        """Get detailed API Gateway metrics."""
        try:
            auth_stats = await self.jwt_service.get_authentication_stats()
            
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "requests": {
                    "total": self.request_count,
                    "errors": self.error_count,
                    "active": len(self.active_requests),
                    "error_rate": (self.error_count / max(1, self.request_count)) * 100
                },
                "performance": {
                    "avg_response_time_ms": sum(self.response_times) / len(self.response_times) if self.response_times else 0,
                    "min_response_time_ms": min(self.response_times) if self.response_times else 0,
                    "max_response_time_ms": max(self.response_times) if self.response_times else 0,
                    "p95_response_time_ms": self._calculate_percentile(self.response_times, 95) if self.response_times else 0
                },
                "security": {
                    "blocked_ips": len(self.blocked_ips),
                    "security_events": len(self.security_events),
                    "authentication": auth_stats.get("jwt_integration", {})
                },
                "configuration": asdict(self.gateway_config)
            }
            
            return ApiResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=metrics,
                timestamp=datetime.utcnow(),
                processing_time=0.0,
                request_id=str(uuid.uuid4())
            )
            
        except Exception as e:
            logger.error(f"Metrics error: {e}")
            return self._create_error_response(500, "Metrics unavailable", str(uuid.uuid4()))
    
    # Private helper methods
    
    async def _route_request(self, request: ApiRequest) -> ApiResponse:
        """Route request to appropriate handler."""
        route_key = f"{request.method}:{request.path}"
        
        # Check for exact route match
        if route_key in self.route_handlers:
            handler = self.route_handlers[route_key]
            return await handler(request)
        
        # Check for wildcard/pattern matches
        for registered_route, handler in self.route_handlers.items():
            if self._route_matches(registered_route, route_key):
                return await handler(request)
        
        # Handle built-in endpoints
        if request.path == "/health":
            return await self.get_health_status()
        elif request.path == "/metrics":
            return await self.get_metrics()
        elif request.path.startswith("/api/v1/auth"):
            return await self._handle_auth_endpoints(request)
        
        # No handler found
        return self._create_error_response(404, "Endpoint not found", request.request_id)
    
    async def _handle_auth_endpoints(self, request: ApiRequest) -> ApiResponse:
        """Handle authentication endpoints."""
        if request.path == "/api/v1/auth/login" and request.method == "POST":
            if not request.body:
                return self._create_error_response(400, "Request body required", request.request_id)
            
            username = request.body.get("username")
            password = request.body.get("password")
            
            if not username or not password:
                return self._create_error_response(400, "Username and password required", request.request_id)
            
            return await self.authenticate_user(username, password, request.client_ip)
        
        elif request.path == "/api/v1/auth/refresh" and request.method == "POST":
            if not request.body:
                return self._create_error_response(400, "Request body required", request.request_id)
            
            refresh_token = request.body.get("refresh_token")
            if not refresh_token:
                return self._create_error_response(400, "Refresh token required", request.request_id)
            
            return await self.refresh_user_token(refresh_token, request.client_ip)
        
        elif request.path == "/api/v1/auth/logout" and request.method == "POST":
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return self._create_error_response(400, "Bearer token required", request.request_id)
            
            token = auth_header[7:]
            return await self.logout_user(token)
        
        else:
            return self._create_error_response(404, "Auth endpoint not found", request.request_id)
    
    def _get_required_permissions(self, path: str) -> Optional[List]:
        """Get required permissions for endpoint."""
        from config.auth_models import Permission
        
        # Define permission requirements for different endpoints
        if path.startswith("/api/v1/admin"):
            return [Permission.ADMIN]
        elif path.startswith("/api/v1/agents") and "POST" in path:
            return [Permission.WRITE, Permission.EXECUTE]
        elif path.startswith("/api/v1/agents"):
            return [Permission.READ]
        elif path.startswith("/api/v1/tasks"):
            return [Permission.READ, Permission.WRITE]
        else:
            return [Permission.READ]  # Default minimum permission
    
    def _route_matches(self, registered_route: str, request_route: str) -> bool:
        """Check if request route matches registered route pattern."""
        # Simple wildcard matching - can be enhanced with regex
        if "*" in registered_route:
            route_pattern = registered_route.replace("*", ".*")
            import re
            return bool(re.match(route_pattern, request_route))
        return False
    
    def _handle_cors_preflight(self, request: ApiRequest) -> ApiResponse:
        """Handle CORS preflight requests."""
        return ApiResponse(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Authorization, Content-Type, X-API-Key",
                "Access-Control-Max-Age": "86400"
            },
            body=None,
            timestamp=datetime.utcnow(),
            processing_time=0.0,
            request_id=request.request_id
        )
    
    def _add_cors_headers(self, response: ApiResponse) -> ApiResponse:
        """Add CORS headers to response."""
        cors_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Expose-Headers": "X-Rate-Limit-Remaining, X-Rate-Limit-Reset"
        }
        response.headers.update(cors_headers)
        return response
    
    def _add_security_headers(self, response: ApiResponse) -> ApiResponse:
        """Add security headers to response."""
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
        response.headers.update(security_headers)
        return response
    
    def _create_error_response(self, status_code: int, message: str, request_id: str) -> ApiResponse:
        """Create standardized error response."""
        return ApiResponse(
            status_code=status_code,
            headers={"Content-Type": "application/json"},
            body={
                "error": message,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            timestamp=datetime.utcnow(),
            processing_time=0.0,
            request_id=request_id
        )
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of response times."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]