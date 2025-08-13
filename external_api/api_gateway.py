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
import re
import random
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import asdict

from .models import (
    ApiGatewayConfig,
    ApiRequest,
    ApiResponse
)
from datetime import datetime
from .service_discovery import ServiceDiscovery, ServiceInstance
from .service_registry import PersistentServiceRegistry, ServiceRegistryConfig
from .load_balancer import ServiceLoadBalancer, LoadBalancingAlgorithm
from .circuit_breaker import CircuitBreakerManager, CircuitBreakerConfig, with_circuit_breaker
from .auth_middleware import AuthenticationMiddleware, AuthResult
from .rate_limit_middleware import RateLimitMiddleware


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
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, service_discovery: Optional[ServiceDiscovery] = None):
        """Initialize API Gateway with JWT authentication.

        Compatibility: accepts either a raw dict configuration or an
        ApiGatewayConfig instance used in tests. In the latter case,
        `self.config` is set to the provided ApiGatewayConfig.
        """
        # Allow both dict and ApiGatewayConfig for initialization
        if isinstance(config, ApiGatewayConfig):
            self.config = config
            gateway_cfg_dict = {k: v for k, v in asdict(config).items()}
            effective_config: Dict[str, Any] = {"gateway": gateway_cfg_dict}
        else:
            self.config = config or self._get_default_config()
            effective_config = self.config  # type: ignore[assignment]
        
        # Initialize core components
        # Allow service discovery injection for integration tests
        self.service_discovery = service_discovery or ServiceDiscovery(effective_config.get("service_discovery", {}))
        
        # Initialize enhanced service registry
        registry_config = ServiceRegistryConfig(**effective_config.get("service_registry", {}))
        self.service_registry = PersistentServiceRegistry(registry_config)
        
        # Initialize load balancer
        self.load_balancer = ServiceLoadBalancer(
            self.service_discovery,
            effective_config.get("load_balancer", {})
        )
        
        # Initialize circuit breaker manager
        cb_config = CircuitBreakerConfig(**effective_config.get("circuit_breaker", {}))
        self.circuit_breaker_manager = CircuitBreakerManager(cb_config)
        
        self.auth_middleware = AuthenticationMiddleware(effective_config.get("auth", {}))
        self.rate_limit_middleware = RateLimitMiddleware(effective_config.get("rate_limiting", {}))
        
        # Initialize JWT integration
        from .jwt_integration import JwtIntegrationService
        self.jwt_service = JwtIntegrationService(effective_config.get("jwt", {}))
        
        # Gateway configuration
        self.gateway_config = (
            self.config if isinstance(self.config, ApiGatewayConfig)
            else ApiGatewayConfig(**effective_config.get("gateway", {}))
        )
        
        # Request tracking and metrics
        self.request_count = 0
        self.response_times = []
        self.error_count = 0
        self.active_requests: Dict[str, datetime] = {}
        self.server_running: bool = False
        # Test-expected counters/flags
        self._request_count: int = 0
        
        # Route handlers (flat mapping) and test-expected nested mapping
        self.route_handlers: Dict[str, Callable] = {}
        self.routes: Dict[str, Dict[str, Callable]] = {}

        # Service route table for discovery-based proxying
        # Maps route prefixes (e.g., "/api/v1/users") -> service_name (e.g., "user-service")
        self._service_routes: Dict[str, str] = {}

        # Middleware stacks (internal and test-expected)
        self.middleware_stack: List[Callable] = []
        self.middleware: List[Callable] = []

        # Simple in-memory rate limiter and API keys for tests
        self.rate_limiter: Dict[str, int] = {}
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        # Back-compat runtime flags
        self.server_started: bool = False
        
        # Security tracking
        from typing import Set
        self.blocked_ips: Set[str] = set()
        self.security_events: List[Dict[str, Any]] = []
        
        # Service routing configuration (handle both dict and dataclass config)
        if isinstance(self.config, ApiGatewayConfig):
            self.service_routes = {}
            self.enable_service_discovery_routing = True
        else:
            self.service_routes: Dict[str, str] = effective_config.get("service_routes", {})
            self.enable_service_discovery_routing = effective_config.get("enable_service_discovery_routing", True)
        # Declarative routing DSL storage
        self.routing_config: Dict[str, Any] = {"routes": []}

        # Observability / Tracing (optional, no-op if not enabled or missing deps)
        self.observability_config: Dict[str, Any] = effective_config.get("observability", {})
        self.tracing_enabled: bool = bool(self.observability_config.get("tracing_enabled", False))
        self.tracing_service_name: str = str(self.observability_config.get("service_name", "api-gateway"))
        self._otel_tracer = None
        self._init_tracing()
        
        logger.info(f"API Gateway initialized on {self.gateway_config.host}:{self.gateway_config.port} with enhanced service discovery")
    
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
            },
            "rate_limiting": {
                "enabled": True,
                "include_headers": True,
                "log_violations": True,
                "bypass_patterns": ["/health", "/metrics", "/favicon.ico"],
                "performance_target_ms": 5.0
            }
        }
    
    async def start(self) -> None:
        """Start the API Gateway and all components."""
        try:
            # Start service discovery
            await self.service_discovery.start()
            
            # Start service registry
            await self.service_registry.start()
            
            # Start load balancer
            await self.load_balancer.start()
            
            logger.info("API Gateway started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start API Gateway: {e}")
            raise

    # ---- Runtime server control for CLI compatibility ----
    async def start_server(self) -> Dict[str, Any]:
        """Start the gateway runtime service (compatibility method for CLI)."""
        if not self.server_running:
            await self.start()
        self.server_running = True
        self.server_started = True
        return {"status": "started", "port": self.gateway_config.port}

    async def stop_server(self) -> Dict[str, Any]:
        """Stop the gateway runtime service (compatibility method for CLI)."""
        if self.server_running:
            await self.stop()
        self.server_running = False
        self.server_started = False
        return {"status": "stopped"}
    
    async def stop(self) -> None:
        """Stop the API Gateway and all components."""
        try:
            # Stop components in reverse order
            await self.load_balancer.stop()
            await self.service_registry.stop()
            await self.service_discovery.stop()
            
            logger.info("API Gateway stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping API Gateway: {e}")
    
    async def register_service(self, service_instance: ServiceInstance, 
                             dependencies: Optional[List[str]] = None) -> bool:
        """Register a service with the gateway."""
        try:
            # Register with service discovery
            discovery_success = await self.service_discovery.register_service(service_instance)
            
            # Register with service registry
            registry_success = await self.service_registry.register_service(
                service_instance, dependencies
            )
            
            # Add to load balancer
            lb_success = await self.load_balancer.add_instance(service_instance)
            
            if discovery_success and registry_success and lb_success:
                logger.info(f"Successfully registered service {service_instance.service_id}")
                return True
            else:
                logger.error(f"Partial failure registering service {service_instance.service_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to register service {service_instance.service_id}: {e}")
            return False
    
    async def deregister_service(self, service_id: str) -> bool:
        """Deregister a service from the gateway."""
        try:
            # Deregister from all components
            discovery_success = await self.service_discovery.deregister_service(service_id)
            registry_success = await self.service_registry.deregister_service(service_id)
            lb_success = await self.load_balancer.remove_instance(service_id)
            
            logger.info(f"Deregistered service {service_id}")
            return discovery_success or registry_success or lb_success
            
        except Exception as e:
            logger.error(f"Failed to deregister service {service_id}: {e}")
            return False
    
    async def route_to_service(self, service_name: str, request: ApiRequest) -> Optional[ServiceInstance]:
        """Route request to best available service instance."""
        try:
            # Use load balancer to select instance
            selected_instance = await self.load_balancer.select_instance(
                service_name=service_name,
                session_id=request.headers.get("X-Session-ID"),
                request_metadata={
                    "client_ip": request.client_ip,
                    "user_agent": request.headers.get("User-Agent"),
                    "path": request.path
                }
            )
            
            if selected_instance:
                logger.debug(f"Routed request to service {selected_instance.service_id}")
            else:
                logger.warning(f"No available instances for service {service_name}")
            
            return selected_instance
            
        except Exception as e:
            logger.error(f"Error routing to service {service_name}: {e}")
            return None
    
    async def execute_service_request(self, service_instance: ServiceInstance, 
                                    request: ApiRequest) -> ApiResponse:
        """Execute request to service instance with circuit breaker protection."""
        try:
            # Create circuit breaker name
            cb_name = f"service_{service_instance.service_name}_{service_instance.host}_{service_instance.port}"
            
            # Execute with circuit breaker
            start_time = time.time()
            
            async def service_call():
                # This would be replaced with actual HTTP client call
                # For now, simulate a service call
                await asyncio.sleep(0.01)  # Simulate network latency
                return ApiResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body={"message": f"Response from {service_instance.service_id}"},
                    timestamp=datetime.utcnow(),
                    processing_time=0.0,
                    request_id=request.request_id
                )
            
            response = await with_circuit_breaker(cb_name, service_call)
            
            # Record successful request
            response_time = (time.time() - start_time) * 1000
            await self.load_balancer.record_request_result(
                service_instance.service_id, True, response_time
            )
            
            return response
            
        except Exception as e:
            # Record failed request
            response_time = (time.time() - start_time) * 1000
            await self.load_balancer.record_request_result(
                service_instance.service_id, False, response_time, str(e)
            )
            
            logger.error(f"Service call failed to {service_instance.service_id}: {e}")
            return self._create_error_response(503, "Service unavailable", request.request_id)
    
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
            
            # Rate Limiting - process request through rate limit middleware
            async def route_handler(req):
                return await self._route_request(req)
            
            response = await self.rate_limit_middleware.process_request(request, route_handler)
            
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
    
    def register_route(
        self,
        path: str,
        method_or_handler: Union[str, Callable],
        handler: Optional[Callable] = None,
        methods: Optional[List[str]] = None,
    ) -> None:
        """Register route handler for specific path.

        Supports both call styles:
        - register_route(path, handler, methods=["GET"])  # original
        - register_route(path, "GET", handler)            # CLI style
        """
        resolved_handler: Callable
        resolved_methods: List[str]

        # Detect signature variant
        if callable(method_or_handler) and handler is None:
            # Original style: (path, handler, methods)
            resolved_handler = method_or_handler  # type: ignore[arg-type]
            resolved_methods = methods or ["GET"]
        else:
            # CLI style: (path, method, handler)
            if not isinstance(method_or_handler, str) or handler is None:
                raise ValueError("Invalid register_route signature. Expected (path, handler, methods) or (path, method, handler)")
            resolved_handler = handler
            resolved_methods = [method_or_handler]

        # Validate async handler for test expectations
        for _ in resolved_methods:
            if not asyncio.iscoroutinefunction(resolved_handler):
                raise ValueError("Handler must be an async function")

        for method in resolved_methods:
            route_key = f"{method}:{path}"
            self.route_handlers[route_key] = resolved_handler
            logger.info(f"Registered route: {route_key}")

            # Populate nested mapping for tests
            if path not in self.routes:
                self.routes[path] = {}
            self.routes[path][method] = resolved_handler

    def unregister_route(self, path: str, method: str) -> bool:
        """Unregister a specific method for a path. Remove path if last method."""
        removed = False
        route_key = f"{method}:{path}"
        if route_key in self.route_handlers:
            del self.route_handlers[route_key]
            removed = True
        if path in self.routes and method in self.routes[path]:
            del self.routes[path][method]
            removed = True
            if not self.routes[path]:
                del self.routes[path]
        return removed
    
    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to processing stack (must be async)."""
        if not asyncio.iscoroutinefunction(middleware):
            raise ValueError("Middleware must be an async function")
        self.middleware_stack.append(middleware)
        self.middleware.append(middleware)
        logger.info(f"Added middleware: {getattr(middleware, '__name__', str(middleware))}")

    def register_api_key(self, api_key: str, metadata: Dict[str, Any]) -> None:
        """Register an API key for simple auth flows in tests."""
        self.api_keys[api_key] = {
            **metadata,
            "created_at": datetime.utcnow().isoformat(),
            "request_count": 0,
        }

    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke or deactivate an API key in the in-memory store."""
        if api_key in self.api_keys:
            self.api_keys[api_key]["active"] = False
            self.api_keys[api_key]["revoked_at"] = datetime.utcnow().isoformat()
            return True
        return False

    def _find_handler(self, path: str, method: str) -> Optional[Callable]:
        """Find a handler by matching path with optional api_prefix stripping."""
        # Normalize path to stored format (without api_prefix)
        prefix = self.gateway_config.api_prefix.rstrip("/")
        normalized = path
        if prefix and normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            if not normalized:
                normalized = "/"
        # Ensure leading slash
        if not normalized.startswith("/"):
            normalized = "/" + normalized
        if normalized in self.routes and method in self.routes[normalized]:
            return self.routes[normalized][method]
        return None

    async def handle_request(self, request: ApiRequest) -> ApiResponse:
        """Handle a request through middleware, auth (optional), and route handler.

        This is a simplified implementation designed to satisfy unit tests.
        """
        start_time = time.time()

        # CORS preflight
        if request.method == "OPTIONS":
            response = self._handle_cors_preflight(request)
            return response

        # Simple rate limiting (global per gateway instance)
        self._request_count += 1
        if self._request_count > self.gateway_config.rate_limit_requests:
            # Minimal rate limit headers for client guidance
            extra_headers = {
                "Retry-After": "1",
                "X-Rate-Limit-Limit": str(self.gateway_config.rate_limit_requests),
                "X-Rate-Limit-Remaining": "0",
            }
            return self._create_error_response(429, "Rate limit exceeded", request.request_id, extra_headers=extra_headers)

        # Simple API key auth if required
        if self.gateway_config.auth_required:
            key = request.headers.get(self.gateway_config.api_key_header, "")
            if not key:
                return self._create_error_response(401, "API key required", request.request_id)
            if key not in self.api_keys:
                return self._create_error_response(401, "Invalid API key", request.request_id)
            if self.api_keys.get(key, {}).get("active") is False:
                return self._create_error_response(401, "API key revoked", request.request_id)
            # Count usage
            self.api_keys[key]["request_count"] = self.api_keys[key].get("request_count", 0) + 1

        # Run middleware; any may stop processing
        for mw in self.middleware:
            result = await mw(request)
            if isinstance(result, dict) and result.get("stop_processing"):
                return ApiResponse(
                    status_code=int(result.get("status_code", 403)),
                    headers={"Content-Type": "application/json"},
                    body=result.get("body", {"error": "Forbidden"}),
                    timestamp=datetime.utcnow(),
                    processing_time=(time.time() - start_time) * 1000,
                    request_id=request.request_id,
                )

        # Resolve handler
        handler = self._find_handler(request.path, request.method)
        if not handler:
            return self._create_error_response(404, "Route not found", request.request_id)

        # Execute with timeout, with optional tracing span
        trace_attrs = {
            "http.method": request.method,
            "http.target": request.path,
            "net.peer.ip": request.client_ip,
            "request.id": request.request_id,
        }
        with self._trace("api_gateway.handle_request", trace_attrs) as span_ctx:
            # ensure trace id propagation
            request.headers.setdefault("X-Trace-Id", span_ctx.trace_id)
            try:
                async def call_handler():
                    return await handler(request)

                handler_result = await asyncio.wait_for(
                    call_handler(), timeout=self.gateway_config.request_timeout
                )
            except asyncio.TimeoutError as _:
                span_ctx.set_attribute("error", True)
                return self._create_error_response(504, "Request timeout", request.request_id)
            except Exception as e:
                logger.exception("Handler error")
                span_ctx.record_exception(e)
                span_ctx.set_attribute("error", True)
                return self._create_error_response(500, "Internal server error", request.request_id)

        # Build response
        response = ApiResponse(
            status_code=int(handler_result.get("status_code", 200)),
            headers={"Content-Type": "application/json"},
            body=handler_result.get("body", {}),
            timestamp=datetime.utcnow(),
            processing_time=(time.time() - start_time) * 1000,
            request_id=request.request_id,
        )

        # Add CORS and security headers
        if self.gateway_config.enable_cors:
            response = self._add_cors_headers(response)
        response = self._add_security_headers(response)
        # attach trace id if present
        try:
            trace_id = request.headers.get("X-Trace-Id")
            if trace_id:
                response.headers["X-Trace-Id"] = trace_id
        except Exception:
            pass
        return response
    
    async def get_health_status(self) -> ApiResponse:
        """Get API Gateway health status."""
        try:
            # Get component health
            auth_stats = await self.jwt_service.get_authentication_stats()
            rate_limit_stats = await self.rate_limit_middleware.get_middleware_stats()
            
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
                    "blocked_ips": len(self.blocked_ips),
                    "server_running": self.server_running,
                    "registered_routes": len(self.route_handlers)
                },
                "authentication": auth_stats,
                "rate_limiting": rate_limit_stats,
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

    # ---- Lightweight helpers for CLI status ----
    async def health_check(self) -> Dict[str, Any]:
        """Lightweight health check used by CLI.status()."""
        try:
            # When server isn't running, report unhealthy for explicit status semantics
            if not self.server_running:
                return {
                    "status": "unhealthy",
                    "server_running": False,
                    "registered_routes": len(self.route_handlers),
                    "active_requests": len(self.active_requests),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            response = await self.get_health_status()
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "server_running": self.server_running,
                "registered_routes": len(self.route_handlers),
                "active_requests": len(self.active_requests),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception:
            return {"status": "unhealthy", "server_running": self.server_running, "timestamp": datetime.utcnow().isoformat()}

    def get_gateway_info(self) -> Dict[str, Any]:
        """Return summary info for CLI display."""
        # Build registered routes summary as expected by tests
        registered_routes: Dict[str, List[str]] = {
            path: sorted(list(methods.keys())) for path, methods in self.routes.items()
        }
        return {
            "server_status": "started" if self.server_started else "stopped",
            "registered_routes": registered_routes,
            "middleware_count": len(self.middleware),
            "total_requests": self._request_count,
        }
    
    async def get_metrics(self) -> ApiResponse:
        """Get detailed API Gateway metrics."""
        try:
            auth_stats = await self.jwt_service.get_authentication_stats()
            rate_limit_stats = await self.rate_limit_middleware.get_middleware_stats()
            
            # Get service discovery metrics
            discovery_info = await self.service_discovery.get_system_info()
            load_balancer_stats = await self.load_balancer.get_load_balancing_stats()
            circuit_breaker_stats = await self.circuit_breaker_manager.get_summary_stats()
            registry_stats = await self.service_registry.get_registry_stats()
            
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
                    "authentication": auth_stats.get("jwt_integration", {}),
                    "rate_limiting": rate_limit_stats
                },
                "service_discovery": {
                    "discovery": discovery_info,
                    "load_balancer": load_balancer_stats,
                    "circuit_breakers": circuit_breaker_stats,
                    "registry": registry_stats
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
        # Try routing via declarative DSL first
        dsl_response = await self._route_via_dsl(request)
        if dsl_response is not None:
            return dsl_response
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
        elif request.path == "/api/v1/services":
            return await self._handle_service_endpoints(request)
        elif request.path.startswith("/api/v1/auth"):
            return await self._handle_auth_endpoints(request)
        elif request.path.startswith("/api/v1/keys"):
            return await self._handle_api_key_endpoints(request)
        
        # Service discovery routing
        if self.enable_service_discovery_routing:
            service_response = await self._try_service_discovery_routing(request)
            if service_response:
                return service_response
        
        # No handler found
        return self._create_error_response(404, "Endpoint not found", request.request_id)

    # ---- Declarative Routing DSL ----
    def apply_routing_config(self, config: Dict[str, Any]) -> bool:
        """Apply declarative routing configuration (hot-reload safe)."""
        try:
            valid, issues = self.validate_routing_config(config)
            if not valid:
                logger.error(f"Routing config validation failed: {issues}")
                return False
            self.routing_config = config
            logger.info("Routing configuration applied")
            return True
        except Exception as e:
            logger.error(f"Failed to apply routing config: {e}")
            return False

    def validate_routing_config(self, config: Dict[str, Any]) -> (bool, List[str]):
        """Validate routing config structure and semantics."""
        issues: List[str] = []
        routes = config.get("routes")
        if not isinstance(routes, list):
            issues.append("'routes' must be a list")
            return False, issues
        for idx, route in enumerate(routes):
            match = route.get("match", {})
            path = match.get("path")
            if not path:
                issues.append(f"route[{idx}]: match.path is required")
            backends = route.get("backends", [])
            if not backends:
                issues.append(f"route[{idx}]: at least one backend is required")
        return (len(issues) == 0), issues

    async def _route_via_dsl(self, request: ApiRequest) -> Optional[ApiResponse]:
        """Attempt to route request using declarative routing config. Returns ApiResponse or None."""
        if not self.routing_config or not self.routing_config.get("routes"):
            return None

        rule = self._find_matching_rule(request)
        if not rule:
            return None

        # Compute rewritten path if configured
        rewritten_path = self._apply_rewrite(request.path, rule)
        if rewritten_path != request.path:
            request = self._clone_request_with_path(request, rewritten_path)

        # Select backend by weight
        selected_backend = self._select_weighted_backend(rule.get("backends", []))
        if not selected_backend:
            return self._create_error_response(503, "No backend available", request.request_id)

        timeout_override = None
        if isinstance(rule.get("timeouts"), dict):
            rt = rule["timeouts"].get("request_timeout")
            if isinstance(rt, (int, float)) and rt > 0:
                timeout_override = float(rt)

        # Shadow routing (fire-and-forget)
        shadow = rule.get("shadow")
        if isinstance(shadow, dict) and shadow.get("service"):
            try:
                percentage = float(shadow.get("percentage", 0))
            except Exception:
                percentage = 0.0
            if random.uniform(0, 100) < percentage:
                asyncio.create_task(self.proxy_to_service(request, shadow["service"]))

        # Execute primary proxy with optional policy overrides
        retry_cfg = rule.get("retries", {}) if isinstance(rule.get("retries"), dict) else {}
        retries = int(retry_cfg.get("count", 0)) if isinstance(retry_cfg.get("count", 0), (int, float)) else 0
        backoff_ms = int(retry_cfg.get("backoff_ms", 0)) if isinstance(retry_cfg.get("backoff_ms", 0), (int, float)) else 0

        proxy_dict = await self.proxy_to_service(
            request,
            selected_backend.get("service"),
            timeout_override=timeout_override,
            retries=retries,
            backoff_ms=backoff_ms,
        )
        return ApiResponse(
            status_code=int(proxy_dict.get("status_code", 502)),
            headers=proxy_dict.get("headers", {}),
            body=proxy_dict.get("body"),
            timestamp=datetime.utcnow(),
            processing_time=0.0,
            request_id=request.request_id,
        )

    def _find_matching_rule(self, request: ApiRequest) -> Optional[Dict[str, Any]]:
        for route in self.routing_config.get("routes", []):
            match = route.get("match", {})
            if not self._request_matches(request, match):
                continue
            return route
        return None

    def _request_matches(self, request: ApiRequest, match: Dict[str, Any]) -> bool:
        path_pattern = match.get("path")
        if not path_pattern:
            return False
        use_regex = bool(match.get("regex", False))
        if use_regex:
            if not re.match(path_pattern, request.path):
                return False
        else:
            # simple prefix or wildcard '*' match
            if "*" in path_pattern:
                regex = re.escape(path_pattern).replace("\\*", ".*") + "$"
                if not re.match(regex, request.path):
                    return False
            else:
                if not request.path.startswith(path_pattern):
                    return False
        methods = match.get("methods")
        if methods and request.method.upper() not in [m.upper() for m in methods]:
            return False
        headers = match.get("headers", {})
        for hk, hv in headers.items():
            if request.headers.get(hk) != hv:
                return False
        return True

    def _apply_rewrite(self, path: str, rule: Dict[str, Any]) -> str:
        rewrite = rule.get("rewrite")
        if not rewrite:
            return path
        match = rule.get("match", {})
        src = match.get("path")
        if src and "*" not in src and not match.get("regex", False):
            if path.startswith(src):
                return rewrite + path[len(src):]
        # fallback to static rewrite
        return rewrite

    def _select_weighted_backend(self, backends: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not backends:
            return None
        total = 0
        weighted: List[tuple] = []
        for b in backends:
            w = int(b.get("weight", 1))
            if w <= 0:
                continue
            total += w
            weighted.append((total, b))
        if total == 0:
            return None
        r = random.randint(1, total)
        for cutoff, b in weighted:
            if r <= cutoff:
                return b
        return backends[0]

    def _clone_request_with_path(self, request: ApiRequest, new_path: str) -> ApiRequest:
        return ApiRequest(
            method=request.method,
            path=new_path,
            headers=dict(request.headers),
            query_params=dict(request.query_params),
            body=request.body,
            request_id=request.request_id,
            client_ip=request.client_ip,
            timestamp=request.timestamp,
        )

    def export_envoy_virtual_host(self, name: str = "api-gateway", domains: Optional[List[str]] = None,
                                  cluster_name_for_service: Optional[Callable[[str], str]] = None) -> Dict[str, Any]:
        """Export routing DSL to an Envoy virtual_host structure."""
        from .envoy_exporter import export_envoy_virtual_host
        return export_envoy_virtual_host(self.routing_config, name=name, domains=domains or ["*"],
                                         cluster_name_for_service=cluster_name_for_service)

    # ---- OpenAPI ingestion ----
    def apply_openapi_spec(self, spec: Dict[str, Any], default_service_name: str) -> bool:
        """Generate routing rules from an OpenAPI spec. Uses x-service-name overrides if present."""
        try:
            routes: List[Dict[str, Any]] = []
            paths = spec.get("paths", {})
            for path, ops in paths.items():
                for method, op in ops.items():
                    if isinstance(op, dict) and method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]:
                        svc = op.get("x-service-name") or spec.get("x-service-name") or default_service_name
                        routes.append({
                            "match": {"path": path, "methods": [method.upper()]},
                            "backends": [{"service": svc, "weight": 100}]
                        })
            return self.apply_routing_config({"routes": routes})
        except Exception as e:
            logger.error(f"Failed to apply OpenAPI spec: {e}")
            return False

    # ---- Service discovery route helpers for integration tests ----
    def register_service_route(self, path_prefix: str, service_name: str) -> None:
        """Register a service route prefix to a service name.

        Example: register_service_route("/api/v1/users", "user-service")
        """
        self._service_routes[path_prefix.rstrip("/")] = service_name

    def unregister_service_route(self, path_prefix: str) -> bool:
        """Unregister a service route prefix."""
        key = path_prefix.rstrip("/")
        if key in self._service_routes:
            del self._service_routes[key]
            return True
        return False

    def _find_service_route(self, path: str) -> Optional[str]:
        """Find mapped service name for a given request path by longest-prefix match."""
        if not self._service_routes:
            return None
        normalized = path.rstrip("/")
        # Prefer the longest matching prefix
        candidates = [prefix for prefix in self._service_routes.keys() if normalized.startswith(prefix)]
        if not candidates:
            return None
        best = max(candidates, key=len)
        return self._service_routes[best]

    async def get_service_instance(self, service_name: str) -> Optional[ServiceInstance]:
        """Return a healthy instance for a given service name using discovery layer."""
        try:
            instance = await self.service_discovery.get_healthy_instance(service_name)
            return instance
        except Exception:
            return None

    async def proxy_to_service(self, request: ApiRequest, service_name: str, timeout_override: Optional[float] = None,
                               retries: int = 0, backoff_ms: int = 0) -> Dict[str, Any]:
        """Proxy an ApiRequest to a discovered service and return a simplified response dict.

        This method is tailored to integration tests that mock aiohttp.ClientSession.
        """
        attempt = 0
        last_error: Optional[str] = None
        while True:
            attempt += 1
            instance = await self.get_service_instance(service_name)
            if not instance:
                # Ensure deterministic shape with headers field present
                return {
                    "status_code": 503,
                    "headers": {},
                    "body": {"error": "No service instance available"}
                }

            # Build target URL preserving the request path and query string
            from urllib.parse import urlencode
            base_url = f"http://{instance.host}:{instance.port}{request.path}"
            if request.query_params:
                query = urlencode(request.query_params, doseq=True)
                url = f"{base_url}?{query}"
            else:
                url = base_url

            try:
                import aiohttp
                total_timeout = timeout_override if timeout_override is not None else self.gateway_config.request_timeout
                timeout = aiohttp.ClientTimeout(total=total_timeout)
                # tracing context for outbound call
                url_for_attrs = None
                with self._trace("api_gateway.proxy_to_service", {
                    "service.name": service_name,
                    "proxy.attempt": attempt,
                }) as span_ctx:
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        # Ensure request has required timestamp for compatibility
                        if not getattr(request, "timestamp", None):
                            try:
                                request.timestamp = datetime.utcnow()
                            except Exception:
                                pass

                        # Support both awaited and async-context-managed response objects (for AsyncMock patterns)
                        # propagate trace id header if available
                        outbound_headers = dict(request.headers)
                        outbound_headers.setdefault("X-Trace-Id", outbound_headers.get("X-Trace-Id", span_ctx.trace_id))
                        url_for_attrs = url
                        pending = session.request(method=request.method, url=url, headers=outbound_headers, json=request.body)
                    resp_ctx = getattr(pending, "__aenter__", None)
                    if callable(resp_ctx):
                        async with pending as resp:
                            text = await resp.text()
                            try:
                                body = json.loads(text)
                            except Exception:
                                body = {"raw": text}
                            result = {"status_code": resp.status, "headers": dict(resp.headers), "body": body}
                            try:
                                span_ctx.set_attribute("http.status_code", resp.status)
                                span_ctx.set_attribute("http.url", url_for_attrs or url)
                            except Exception:
                                pass
                            if resp.status >= 500 and attempt <= retries:
                                last_error = f"upstream {resp.status}"
                                if backoff_ms > 0:
                                    await asyncio.sleep(backoff_ms / 1000.0)
                                continue
                            return result
                    else:
                        resp = await pending
                        text = await resp.text()
                        # Try JSON decode, fallback to text
                        try:
                            body = json.loads(text)
                        except Exception:
                            body = {"raw": text}
                        result = {"status_code": resp.status, "headers": dict(resp.headers), "body": body}
                        try:
                            span_ctx.set_attribute("http.status_code", resp.status)
                            span_ctx.set_attribute("http.url", url_for_attrs or url)
                        except Exception:
                            pass
                        if resp.status >= 500 and attempt <= retries:
                            last_error = f"upstream {resp.status}"
                            if backoff_ms > 0:
                                await asyncio.sleep(backoff_ms / 1000.0)
                            continue
                        return result
            except Exception as e:
                last_error = str(e)
                logger.error(f"Proxy error to {service_name}: {e}")
                if attempt <= retries:
                    if backoff_ms > 0:
                        await asyncio.sleep(backoff_ms / 1000.0)
                    # try again
                    continue
                # Deterministic error shape with headers present for consistency
                return {
                    "status_code": 502,
                    "headers": {},
                    "body": {"error": "Bad gateway", "details": last_error or "proxy_failure"}
                }

    # ---- Tracing helpers (optional) ----
    def _init_tracing(self) -> None:
        if not self.tracing_enabled:
            return
        try:
            from opentelemetry import trace as _otel_trace  # type: ignore
            self._otel_tracer = _otel_trace.get_tracer(self.tracing_service_name)
        except Exception:
            # Missing dependencies or init failure; operate in no-op mode
            self._otel_tracer = None

    class _NoopSpanCtx:
        def __init__(self):
            import uuid as _uuid
            self._trace_id = _uuid.uuid4().hex
        @property
        def trace_id(self) -> str:
            return self._trace_id
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def set_attribute(self, key: str, value: Any) -> None:
            pass
        def record_exception(self, exc: Exception) -> None:
            pass

    class _OtelSpanCtx:
        def __init__(self, tracer, name: str, attributes: Optional[Dict[str, Any]] = None):
            self._tracer = tracer
            self._name = name
            self._attributes = attributes or {}
            self._span = None
            self._cm = None
            import uuid as _uuid
            self._fallback_id = _uuid.uuid4().hex
        def __enter__(self):
            self._cm = self._tracer.start_as_current_span(self._name)
            self._span = self._cm.__enter__()
            try:
                for k, v in self._attributes.items():
                    self._span.set_attribute(k, v)
            except Exception:
                pass
            return self
        def __exit__(self, exc_type, exc, tb):
            try:
                if exc is not None:
                    self.record_exception(exc)
            finally:
                try:
                    self._cm.__exit__(exc_type, exc, tb)
                except Exception:
                    pass
            return False
        @property
        def trace_id(self) -> str:
            try:
                # Return hex trace id if available
                ctx = self._span.get_span_context()
                if ctx and getattr(ctx, "trace_id", 0):
                    return f"{ctx.trace_id:032x}"
            except Exception:
                pass
            return self._fallback_id
        def set_attribute(self, key: str, value: Any) -> None:
            try:
                self._span.set_attribute(key, value)
            except Exception:
                pass
        def record_exception(self, exc: Exception) -> None:
            try:
                self._span.record_exception(exc)
            except Exception:
                pass

    def _trace(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        if self.tracing_enabled and self._otel_tracer is not None:
            return ApiGateway._OtelSpanCtx(self._otel_tracer, name, attributes)
        return ApiGateway._NoopSpanCtx()
    
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
        
        elif request.path == "/api/v1/auth/introspect" and request.method == "POST":
            if not request.body or not request.body.get("token"):
                return self._create_error_response(400, "Token required", request.request_id)
            try:
                result = await self.jwt_service.introspect_token(request.body["token"])
                return ApiResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=result,
                    timestamp=datetime.utcnow(),
                    processing_time=0.0,
                    request_id=request.request_id
                )
            except Exception:
                logger.exception("Introspection error")
                return self._create_error_response(500, "Introspection failed", request.request_id)
        
        else:
            return self._create_error_response(404, "Auth endpoint not found", request.request_id)
    
    async def _handle_service_endpoints(self, request: ApiRequest) -> ApiResponse:
        """Handle service discovery management endpoints."""
        try:
            if request.path == "/api/v1/services" and request.method == "GET":
                # List all services
                services = await self.service_registry.get_registry_stats()
                return ApiResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=services,
                    timestamp=datetime.utcnow(),
                    processing_time=0.0,
                    request_id=request.request_id
                )
            
            elif request.path == "/api/v1/services" and request.method == "POST":
                # Register new service
                if not request.body:
                    return self._create_error_response(400, "Request body required", request.request_id)
                
                service_data = request.body
                try:
                    service_instance = ServiceInstance(
                        service_id=service_data["service_id"],
                        service_name=service_data["service_name"],
                        host=service_data["host"],
                        port=service_data["port"],
                        metadata=service_data.get("metadata", {}),
                        health_check_url=service_data.get("health_check_url"),
                        tags=service_data.get("tags", []),
                        version=service_data.get("version", "1.0.0")
                    )
                    
                    dependencies = service_data.get("dependencies", [])
                    success = await self.register_service(service_instance, dependencies)
                    
                    if success:
                        return ApiResponse(
                            status_code=201,
                            headers={"Content-Type": "application/json"},
                            body={"message": "Service registered successfully", "service_id": service_instance.service_id},
                            timestamp=datetime.utcnow(),
                            processing_time=0.0,
                            request_id=request.request_id
                        )
                    else:
                        return self._create_error_response(500, "Service registration failed", request.request_id)
                
                except KeyError as e:
                    return self._create_error_response(400, f"Missing required field: {e}", request.request_id)
            
            elif request.path.startswith("/api/v1/services/") and request.method == "DELETE":
                # Deregister service
                service_id = request.path.split("/")[-1]
                success = await self.deregister_service(service_id)
                
                if success:
                    return ApiResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body={"message": "Service deregistered successfully"},
                        timestamp=datetime.utcnow(),
                        processing_time=0.0,
                        request_id=request.request_id
                    )
                else:
                    return self._create_error_response(404, "Service not found", request.request_id)
            
            elif request.path.startswith("/api/v1/services/") and "/health" in request.path:
                # Get service health
                service_id = request.path.split("/")[-2]  # /api/v1/services/{id}/health
                health_info = await self.service_registry.get_service_health(service_id)
                
                if health_info:
                    return ApiResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=health_info,
                        timestamp=datetime.utcnow(),
                        processing_time=0.0,
                        request_id=request.request_id
                    )
                else:
                    return self._create_error_response(404, "Service not found", request.request_id)
            
            elif request.path == "/api/v1/services/discovery/stats":
                # Get service discovery statistics
                discovery_info = await self.service_discovery.get_system_info()
                load_balancer_stats = await self.load_balancer.get_load_balancing_stats()
                circuit_breaker_stats = await self.circuit_breaker_manager.get_summary_stats()
                
                stats = {
                    "service_discovery": discovery_info,
                    "load_balancer": load_balancer_stats,
                    "circuit_breakers": circuit_breaker_stats,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                return ApiResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=stats,
                    timestamp=datetime.utcnow(),
                    processing_time=0.0,
                    request_id=request.request_id
                )
            
            else:
                return self._create_error_response(404, "Service endpoint not found", request.request_id)
        
        except Exception as e:
            logger.error(f"Error handling service endpoint: {e}")
            return self._create_error_response(500, "Internal server error", request.request_id)

    async def _handle_api_key_endpoints(self, request: ApiRequest) -> ApiResponse:
        """Handle API key lifecycle and analytics endpoints."""
        try:
            from security.token_manager import TokenType
            try:
                from config.auth_models import Permission  # type: ignore
            except Exception:
                from enum import Enum
                class Permission(Enum):
                    READ = "read"; WRITE = "write"; ADMIN = "admin"; EXECUTE = "execute"

            # Issue new API key
            if request.path == "/api/v1/keys" and request.method == "POST":
                if not request.body:
                    return self._create_error_response(400, "Request body required", request.request_id)
                user_id = request.body.get("user_id")
                if not user_id:
                    return self._create_error_response(400, "user_id is required", request.request_id)
                raw_perms = request.body.get("permissions") or [Permission.READ.value]
                permissions = [Permission(p) if not isinstance(p, Permission) else p for p in raw_perms]
                scopes = request.body.get("scopes") or []

                token, token_id = await self.jwt_service.token_manager.create_secure_token(
                    user_id=user_id,
                    token_type=TokenType.API_KEY,
                    permissions=permissions,
                    scopes=scopes,
                    expires_in_hours=24 * 365
                )
                # Store in in-memory API key registry for request counting
                self.api_keys[token] = {
                    "user_id": user_id,
                    "permissions": [p.value for p in permissions],
                    "scopes": scopes,
                    "active": True,
                    "created_at": datetime.utcnow().isoformat(),
                    "request_count": 0,
                }
                meta = self.jwt_service.token_manager.token_metadata.get(token_id)
                expires_at = meta.expires_at.isoformat() if meta and meta.expires_at else None
                return ApiResponse(
                    status_code=201,
                    headers={"Content-Type": "application/json"},
                    body={"api_key": token, "token_id": token_id, "expires_at": expires_at},
                    timestamp=datetime.utcnow(),
                    processing_time=0.0,
                    request_id=request.request_id
                )

            # Rotate API key
            elif request.path == "/api/v1/keys/rotate" and request.method == "POST":
                if not request.body or not request.body.get("api_key"):
                    return self._create_error_response(400, "api_key is required", request.request_id)
                old_key = request.body["api_key"]
                rotation = await self.jwt_service.token_manager.rotate_token(old_key)
                if not rotation:
                    return self._create_error_response(400, "Rotation failed", request.request_id)
                new_key, new_id = rotation
                # Deactivate old key in local registry, create new entry
                if old_key in self.api_keys:
                    meta_local = self.api_keys.pop(old_key)
                else:
                    meta_local = {"user_id": None, "permissions": [], "scopes": []}
                self.api_keys[old_key] = {**meta_local, "active": False, "revoked_at": datetime.utcnow().isoformat()}
                self.api_keys[new_key] = {**meta_local, "active": True, "created_at": datetime.utcnow().isoformat(), "request_count": 0}
                return ApiResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body={"api_key": new_key, "token_id": new_id},
                    timestamp=datetime.utcnow(),
                    processing_time=0.0,
                    request_id=request.request_id
                )

            # Revoke API key
            elif request.path == "/api/v1/keys/revoke" and request.method == "POST":
                if not request.body or not request.body.get("api_key"):
                    return self._create_error_response(400, "api_key is required", request.request_id)
                key = request.body["api_key"]
                # Extract token id and revoke in token manager
                try:
                    import jwt as _jwt
                    payload = _jwt.decode(key, options={"verify_signature": False})
                    token_id = payload.get("token_id")
                except Exception:
                    token_id = None
                if token_id:
                    await self.jwt_service.token_manager.revoke_token(token_id, reason="api_key_revoked")
                # Mark in local registry
                self.revoke_api_key(key)
                return ApiResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body={"revoked": True},
                    timestamp=datetime.utcnow(),
                    processing_time=0.0,
                    request_id=request.request_id
                )

            # Analytics
            elif request.path == "/api/v1/keys/analytics" and request.method == "GET":
                # Summarize local request counts and statuses
                total = len(self.api_keys)
                active = sum(1 for v in self.api_keys.values() if v.get("active", True))
                total_requests = sum(int(v.get("request_count", 0)) for v in self.api_keys.values())
                return ApiResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body={
                        "total_keys": total,
                        "active_keys": active,
                        "total_requests": total_requests,
                    },
                    timestamp=datetime.utcnow(),
                    processing_time=0.0,
                    request_id=request.request_id
                )

            else:
                return self._create_error_response(404, "Keys endpoint not found", request.request_id)

        except Exception as e:
            logger.error(f"Error handling API key endpoint: {e}")
            return self._create_error_response(500, "Internal server error", request.request_id)
    
    async def _try_service_discovery_routing(self, request: ApiRequest) -> Optional[ApiResponse]:
        """Try to route request using service discovery."""
        try:
            # Extract service name from path
            # Expected format: /api/v1/{service_name}/...
            path_parts = request.path.strip("/").split("/")
            if len(path_parts) < 3 or path_parts[0] != "api" or path_parts[1] != "v1":
                return None
            
            service_name = path_parts[2]
            
            # Check if this is a known service
            instances = await self.service_discovery.discover_services(service_name)
            if not instances:
                # Try service registry as fallback
                registry_instances = await self.service_registry.discover_services(service_name)
                if not registry_instances:
                    return None
            
            # Route to service instance
            selected_instance = await self.route_to_service(service_name, request)
            if not selected_instance:
                return self._create_error_response(503, f"No healthy instances available for service {service_name}", request.request_id)
            
            # Execute request to service
            return await self.execute_service_request(selected_instance, request)
            
        except Exception as e:
            logger.error(f"Error in service discovery routing: {e}")
            return None
    
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
    
    def _create_error_response(self, status_code: int, message: str, request_id: str, extra_headers: Optional[Dict[str, str]] = None) -> ApiResponse:
        """Create standardized error response."""
        headers = {"Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        return ApiResponse(
            status_code=status_code,
            headers=headers,
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