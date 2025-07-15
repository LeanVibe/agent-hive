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
from ..advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
from ..advanced_orchestration.models import LoadBalancingStrategy
from .auth_middleware import AuthenticationMiddleware, AuthMethod, Permission
from .rate_limiter import AdvancedRateLimiter, RateLimitStrategy


logger = logging.getLogger(__name__)


class ApiGateway:
    """
    API Gateway for routing and managing external API requests.
    
    Provides authentication, rate limiting, request validation,
    and response formatting for the orchestration system.
    """
    
    def __init__(self, config: ApiGatewayConfig, coordinator: Optional[MultiAgentCoordinator] = None, 
                 auth_config: Optional[Dict[str, Any]] = None, rate_limit_config: Optional[Dict[str, Any]] = None):
        """
        Initialize API gateway.
        
        Args:
            config: API gateway configuration
            coordinator: Optional multi-agent coordinator for load balancing
            auth_config: Optional authentication configuration
            rate_limit_config: Optional rate limiter configuration
        """
        self.config = config
        self.coordinator = coordinator
        self.routes: Dict[str, Dict[str, Callable]] = {}  # {path: {method: handler}}
        self.versioned_routes: Dict[str, Dict[str, Dict[str, Callable]]] = {}  # {version: {path: {method: handler}}}
        self.service_routes: Dict[str, List[str]] = {}  # {service_name: [agent_ids]}
        self.middleware: List[Callable] = []
        self.rate_limiter: Dict[str, List[float]] = {}  # Legacy rate limiter (kept for compatibility)
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.server_started = False
        self._request_count = 0
        self.supported_versions = ["v1", "v2"]  # Default supported versions
        
        # Initialize authentication middleware
        if auth_config:
            self.auth_middleware = AuthenticationMiddleware(auth_config)
        else:
            # Default auth config
            default_auth_config = {
                "enabled_methods": [AuthMethod.API_KEY],
                "max_auth_attempts": 5,
                "auth_window_minutes": 15
            }
            self.auth_middleware = AuthenticationMiddleware(default_auth_config)
        
        # Initialize advanced rate limiter
        if rate_limit_config:
            self.advanced_rate_limiter = AdvancedRateLimiter(rate_limit_config)
        else:
            # Default rate limiter config
            default_rate_config = {
                "strategy": "token_bucket",
                "default_limit": 1000,
                "window_size": 3600,
                "enable_adaptive": True
            }
            self.advanced_rate_limiter = AdvancedRateLimiter(default_rate_config)
        
        # Load balancing for service routing
        self.service_load_balancer = {
            'round_robin_counters': {},
            'health_cache': {},
            'last_health_check': {}
        }
        
        logger.info(f"ApiGateway initialized on {config.host}:{config.port}")
    
    async def start_server(self) -> None:
        """Start the API gateway server."""
        if self.server_started:
            logger.warning("API gateway already started")
            return
            
        try:
            logger.info(f"Starting API gateway on {self.config.host}:{self.config.port}")
            await asyncio.sleep(0.1)  # Simulate startup time
            
            self.server_started = True
            logger.info("API gateway started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start API gateway: {e}")
            raise
    
    async def stop_server(self) -> None:
        """Stop the API gateway server."""
        if not self.server_started:
            logger.warning("API gateway not running")
            return
            
        try:
            logger.info("Stopping API gateway...")
            self.server_started = False
            logger.info("API gateway stopped")
            
        except Exception as e:
            logger.error(f"Error stopping API gateway: {e}")
            raise
    
    def register_route(self, path: str, method: str, handler: Callable, version: Optional[str] = None) -> None:
        """
        Register a route handler with optional versioning.
        
        Args:
            path: API endpoint path
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            handler: Async function to handle the request
            version: API version (e.g., "v1", "v2")
        """
        if not asyncio.iscoroutinefunction(handler):
            raise ValueError("Handler must be an async function")
        
        if version:
            # Register versioned route
            if version not in self.versioned_routes:
                self.versioned_routes[version] = {}
            if path not in self.versioned_routes[version]:
                self.versioned_routes[version][path] = {}
            
            self.versioned_routes[version][path][method.upper()] = handler
            logger.info(f"Registered versioned route: {method.upper()} {path} ({version})")
        else:
            # Register unversioned route
            if path not in self.routes:
                self.routes[path] = {}
                
            self.routes[path][method.upper()] = handler
            logger.info(f"Registered route: {method.upper()} {path}")
    
    def unregister_route(self, path: str, method: str) -> bool:
        """
        Unregister a route handler.
        
        Args:
            path: API endpoint path
            method: HTTP method
            
        Returns:
            True if route was removed, False if not found
        """
        if path in self.routes and method.upper() in self.routes[path]:
            del self.routes[path][method.upper()]
            if not self.routes[path]:  # Remove path if no methods left
                del self.routes[path]
            logger.info(f"Unregistered route: {method.upper()} {path}")
            return True
        return False
    
    def add_middleware(self, middleware: Callable) -> None:
        """
        Add middleware function to the processing pipeline.
        
        Args:
            middleware: Async function to process requests/responses
        """
        if not asyncio.iscoroutinefunction(middleware):
            raise ValueError("Middleware must be an async function")
            
        self.middleware.append(middleware)
        logger.info(f"Added middleware: {middleware.__name__}")
    
    def register_service(self, service_name: str, agent_ids: List[str]) -> None:
        """
        Register a service with associated agent IDs for load balancing.
        
        Args:
            service_name: Name of the service
            agent_ids: List of agent IDs that can handle this service
        """
        self.service_routes[service_name] = agent_ids
        self.service_load_balancer['round_robin_counters'][service_name] = 0
        self.service_load_balancer['health_cache'][service_name] = {}
        self.service_load_balancer['last_health_check'][service_name] = time.time()
        logger.info(f"Registered service {service_name} with {len(agent_ids)} agents")
    
    def unregister_service(self, service_name: str) -> bool:
        """
        Unregister a service.
        
        Args:
            service_name: Name of the service to unregister
            
        Returns:
            True if service was removed, False if not found
        """
        if service_name in self.service_routes:
            del self.service_routes[service_name]
            self.service_load_balancer['round_robin_counters'].pop(service_name, None)
            self.service_load_balancer['health_cache'].pop(service_name, None)
            self.service_load_balancer['last_health_check'].pop(service_name, None)
            logger.info(f"Unregistered service: {service_name}")
            return True
        return False
    
    async def select_agent_for_service(self, service_name: str, strategy: str = "round_robin") -> Optional[str]:
        """
        Select an agent for a service based on load balancing strategy.
        
        Args:
            service_name: Name of the service
            strategy: Load balancing strategy (round_robin, least_connections, health_based)
            
        Returns:
            Selected agent ID or None if no available agents
        """
        if service_name not in self.service_routes:
            return None
        
        agent_ids = self.service_routes[service_name]
        if not agent_ids:
            return None
        
        # If coordinator is available, use its load balancing
        if self.coordinator:
            return await self._select_agent_with_coordinator(agent_ids, strategy)
        
        # Fallback to simple round-robin
        return self._select_agent_round_robin(service_name, agent_ids)
    
    async def _select_agent_with_coordinator(self, agent_ids: List[str], strategy: str) -> Optional[str]:
        """
        Select agent using the multi-agent coordinator.
        
        Args:
            agent_ids: Available agent IDs
            strategy: Load balancing strategy
            
        Returns:
            Selected agent ID or None
        """
        # Get healthy agents from coordinator
        healthy_agents = []
        for agent_id in agent_ids:
            agent_info = await self.coordinator.get_agent_status(agent_id)
            if agent_info and agent_info.status.value == "healthy":
                healthy_agents.append(agent_id)
        
        if not healthy_agents:
            return None
        
        if strategy == "least_connections":
            # Select agent with least active tasks
            return min(healthy_agents, key=lambda a: self.coordinator.agents[a].active_tasks)
        elif strategy == "resource_based":
            # Use coordinator's resource-based selection
            return await self.coordinator._select_resource_based(healthy_agents)
        else:
            # Default to round-robin
            return healthy_agents[0]
    
    def _select_agent_round_robin(self, service_name: str, agent_ids: List[str]) -> str:
        """
        Select agent using round-robin strategy.
        
        Args:
            service_name: Name of the service
            agent_ids: Available agent IDs
            
        Returns:
            Selected agent ID
        """
        counter = self.service_load_balancer['round_robin_counters'][service_name]
        selected_agent = agent_ids[counter % len(agent_ids)]
        self.service_load_balancer['round_robin_counters'][service_name] = counter + 1
        return selected_agent
    
    def register_api_key(self, api_key: str, metadata: Dict[str, Any]) -> None:
        """
        Register an API key with associated metadata.
        
        Args:
            api_key: API key string
            metadata: Associated metadata (permissions, rate limits, etc.)
        """
        self.api_keys[api_key] = {
            **metadata,
            "created_at": datetime.now().isoformat(),
            "last_used": None,
            "request_count": 0
        }
        logger.info(f"Registered API key with metadata: {list(metadata.keys())}")
    
    async def handle_request(self, request: ApiRequest) -> ApiResponse:
        """
        Handle incoming API request.
        
        Args:
            request: API request data
            
        Returns:
            API response
        """
        start_time = time.time()
        
        try:
            # Authentication check
            if self.config.auth_required:
                auth_result = await self.auth_middleware.authenticate_request(request)
                if not auth_result.success:
                    return self._create_error_response(
                        request.request_id,
                        401,
                        auth_result.error or "Authentication failed",
                        start_time
                    )
                
                # Store auth context for downstream use
                request.auth_context = {
                    "user_id": auth_result.user_id,
                    "permissions": auth_result.permissions,
                    "metadata": auth_result.metadata
                }
            
            # Rate limiting check
            rate_limit_result = await self.advanced_rate_limiter.check_rate_limit(request)
            if not rate_limit_result.allowed:
                response = self._create_error_response(
                    request.request_id,
                    429,
                    rate_limit_result.error_message or "Rate limit exceeded",
                    start_time
                )
                
                # Add rate limit headers
                response.headers.update({
                    "X-RateLimit-Remaining": str(rate_limit_result.remaining),
                    "X-RateLimit-Reset": str(int(rate_limit_result.reset_time)),
                    "X-RateLimit-Throttle-Level": rate_limit_result.throttle_level.value
                })
                
                if rate_limit_result.retry_after:
                    response.headers["Retry-After"] = str(int(rate_limit_result.retry_after))
                
                return response
            
            # CORS handling
            if self.config.enable_cors and request.method == "OPTIONS":
                return self._create_cors_response(request.request_id, start_time)
            
            # Route matching
            handler = self._find_handler(request.path, request.method)
            if not handler:
                return self._create_error_response(
                    request.request_id,
                    404,
                    "Route not found",
                    start_time
                )
            
            # Process middleware
            for middleware in self.middleware:
                middleware_result = await middleware(request)
                if middleware_result.get("stop_processing"):
                    return self._create_response_from_middleware(
                        request.request_id,
                        middleware_result,
                        start_time
                    )
            
            # Execute handler with timeout
            try:
                result = await asyncio.wait_for(
                    handler(request),
                    timeout=self.config.request_timeout
                )
                
                # Update API key usage
                if self.config.auth_required:
                    self._update_api_key_usage(request.headers.get(self.config.api_key_header))
                
                response = ApiResponse(
                    status_code=result.get("status_code", 200),
                    headers=self._get_response_headers(),
                    body=result.get("body"),
                    timestamp=datetime.now(),
                    processing_time=(time.time() - start_time) * 1000,
                    request_id=request.request_id
                )
                
                self._request_count += 1
                logger.info(f"Processed request {request.request_id} in {response.processing_time:.2f}ms")
                return response
                
            except asyncio.TimeoutError:
                logger.error(f"Request timeout for {request.request_id}")
                return self._create_error_response(
                    request.request_id,
                    504,
                    "Request timeout",
                    start_time
                )
                
        except Exception as e:
            logger.error(f"Error handling request {request.request_id}: {e}")
            return self._create_error_response(
                request.request_id,
                500,
                "Internal server error",
                start_time
            )
    
    async def _authenticate_request(self, request: ApiRequest) -> Dict[str, Any]:
        """
        Authenticate API request using API key.
        
        Args:
            request: API request to authenticate
            
        Returns:
            Authentication result
        """
        api_key = request.headers.get(self.config.api_key_header)
        
        if not api_key:
            return {
                "success": False,
                "message": f"Missing {self.config.api_key_header} header"
            }
        
        if api_key not in self.api_keys:
            return {
                "success": False,
                "message": "Invalid API key"
            }
        
        # Check if API key is active
        key_data = self.api_keys[api_key]
        if key_data.get("active", True) is False:
            return {
                "success": False,
                "message": "API key is inactive"
            }
        
        return {
            "success": True,
            "message": "Authentication successful",
            "key_data": key_data
        }
    
    async def _check_rate_limit(self, request: ApiRequest) -> Dict[str, Any]:
        """
        Check if request is within rate limits.
        
        Args:
            request: API request to check
            
        Returns:
            Rate limit check result
        """
        # Use API key or client IP for rate limiting
        rate_limit_key = request.headers.get(self.config.api_key_header, request.client_ip)
        
        current_time = time.time()
        window_start = current_time - self.config.rate_limit_window
        
        # Clean old entries
        if rate_limit_key in self.rate_limiter:
            self.rate_limiter[rate_limit_key] = [
                timestamp for timestamp in self.rate_limiter[rate_limit_key]
                if timestamp > window_start
            ]
        else:
            self.rate_limiter[rate_limit_key] = []
        
        # Check current count
        current_count = len(self.rate_limiter[rate_limit_key])
        if current_count >= self.config.rate_limit_requests:
            return {
                "success": False,
                "message": "Rate limit exceeded"
            }
        
        # Add current request
        self.rate_limiter[rate_limit_key].append(current_time)
        return {
            "success": True,
            "message": "Rate limit check passed"
        }
    
    def _find_handler(self, path: str, method: str) -> Optional[Callable]:
        """
        Find handler for the given path and method with version support.
        
        Args:
            path: Request path
            method: HTTP method
            
        Returns:
            Handler function or None
        """
        # Remove API prefix if present
        if path.startswith(self.config.api_prefix):
            path = path[len(self.config.api_prefix):]
        
        # Check for versioned routes first
        version = self._extract_version_from_path(path)
        if version:
            versioned_path = self._remove_version_from_path(path, version)
            if version in self.versioned_routes:
                handler = self.versioned_routes[version].get(versioned_path, {}).get(method.upper())
                if handler:
                    return handler
        
        # Fallback to unversioned routes
        return self.routes.get(path, {}).get(method.upper())
    
    def _extract_version_from_path(self, path: str) -> Optional[str]:
        """
        Extract API version from path.
        
        Args:
            path: Request path
            
        Returns:
            API version or None
        """
        path_parts = path.strip('/').split('/')
        if path_parts and path_parts[0] in self.supported_versions:
            return path_parts[0]
        return None
    
    def _remove_version_from_path(self, path: str, version: str) -> str:
        """
        Remove version from path.
        
        Args:
            path: Request path
            version: API version to remove
            
        Returns:
            Path without version
        """
        if path.startswith(f'/{version}/'):
            return path[len(f'/{version}'):]
        elif path.startswith(f'{version}/'):
            return path[len(f'{version}'):]
        return path
    
    def _get_response_headers(self) -> Dict[str, str]:
        """Get response headers including CORS if enabled."""
        headers = {
            "Content-Type": "application/json",
            "X-API-Gateway": "LeanVibe-Agent-Hive"
        }
        
        if self.config.enable_cors:
            headers.update({
                "Access-Control-Allow-Origin": ",".join(self.config.cors_origins),
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-API-Key"
            })
        
        return headers
    
    def _create_error_response(self, request_id: str, status_code: int, message: str, start_time: float) -> ApiResponse:
        """Create error response."""
        return ApiResponse(
            status_code=status_code,
            headers=self._get_response_headers(),
            body={"error": message, "request_id": request_id},
            timestamp=datetime.now(),
            processing_time=(time.time() - start_time) * 1000,
            request_id=request_id
        )
    
    def _create_cors_response(self, request_id: str, start_time: float) -> ApiResponse:
        """Create CORS preflight response."""
        return ApiResponse(
            status_code=200,
            headers=self._get_response_headers(),
            body=None,
            timestamp=datetime.now(),
            processing_time=(time.time() - start_time) * 1000,
            request_id=request_id
        )
    
    def _create_response_from_middleware(self, request_id: str, middleware_result: Dict[str, Any], start_time: float) -> ApiResponse:
        """Create response from middleware result."""
        return ApiResponse(
            status_code=middleware_result.get("status_code", 200),
            headers=self._get_response_headers(),
            body=middleware_result.get("body"),
            timestamp=datetime.now(),
            processing_time=(time.time() - start_time) * 1000,
            request_id=request_id
        )
    
    def _update_api_key_usage(self, api_key: Optional[str]) -> None:
        """Update API key usage statistics."""
        if api_key and api_key in self.api_keys:
            self.api_keys[api_key]["last_used"] = datetime.now().isoformat()
            self.api_keys[api_key]["request_count"] += 1
    
    def get_gateway_info(self) -> Dict[str, Any]:
        """Get comprehensive API gateway information."""
        return {
            "server_status": "running" if self.server_started else "stopped",
            "registered_routes": {
                path: list(methods.keys()) 
                for path, methods in self.routes.items()
            },
            "versioned_routes": {
                version: {
                    path: list(methods.keys())
                    for path, methods in routes.items()
                }
                for version, routes in self.versioned_routes.items()
            },
            "services": {
                service: len(agents)
                for service, agents in self.service_routes.items()
            },
            "middleware_count": len(self.middleware),
            "api_keys_count": len(self.api_keys),
            "total_requests": self._request_count,
            "authentication": self.auth_middleware.get_auth_stats(),
            "rate_limiting": self.advanced_rate_limiter.get_global_stats(),
            "coordinator_connected": self.coordinator is not None,
            "supported_versions": self.supported_versions,
            "config": asdict(self.config)
        }
    
    def get_route_statistics(self) -> Dict[str, Any]:
        """Get route usage statistics."""
        # Count versioned routes
        versioned_count = sum(
            len(version_routes) for version_routes in self.versioned_routes.values()
        )
        
        return {
            "total_routes": len(self.routes),
            "versioned_routes": versioned_count,
            "routes_by_method": {},
            "request_count": self._request_count,
            "average_response_time": "15ms"  # Placeholder
        }
    
    def get_api_documentation(self) -> Dict[str, Any]:
        """
        Generate API documentation.
        
        Returns:
            API documentation structure
        """
        documentation = {
            "title": "LeanVibe Agent Hive API",
            "version": "1.0.0",
            "description": "API Gateway for the LeanVibe Agent Hive orchestration system",
            "base_url": f"http://{self.config.host}:{self.config.port}{self.config.api_prefix}",
            "supported_versions": self.supported_versions,
            "authentication": {
                "type": "API Key",
                "header": self.config.api_key_header,
                "required": self.config.auth_required
            },
            "rate_limiting": {
                "requests_per_window": self.config.rate_limit_requests,
                "window_seconds": self.config.rate_limit_window
            },
            "endpoints": {
                "unversioned": self._format_routes_for_docs(self.routes),
                "versioned": {
                    version: self._format_routes_for_docs(routes)
                    for version, routes in self.versioned_routes.items()
                }
            },
            "services": {
                service: {
                    "agent_count": len(agents),
                    "load_balancing": "round_robin"
                }
                for service, agents in self.service_routes.items()
            }
        }
        
        return documentation
    
    def _format_routes_for_docs(self, routes: Dict[str, Dict[str, Callable]]) -> Dict[str, Any]:
        """
        Format routes for documentation.
        
        Args:
            routes: Route dictionary
            
        Returns:
            Formatted routes for documentation
        """
        formatted_routes = {}
        for path, methods in routes.items():
            formatted_routes[path] = {
                "methods": list(methods.keys()),
                "handler_names": [handler.__name__ for handler in methods.values()]
            }
        
        return formatted_routes
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on API gateway.
        
        Returns:
            Health status information
        """
        return {
            "status": "healthy" if self.server_started else "unhealthy",
            "server_running": self.server_started,
            "registered_routes": len(self.routes),
            "active_rate_limits": len(self.rate_limiter),
            "config_valid": True,
            "timestamp": datetime.now().isoformat()
        }