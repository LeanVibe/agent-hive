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

# FastAPI imports for real HTTP server
try:
    from fastapi import FastAPI, Request, Response, HTTPException, Depends
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None
    Request = None
    Response = None
    HTTPException = None
    Depends = None
    CORSMiddleware = None
    uvicorn = None

from .models import (
    ApiGatewayConfig,
    ApiRequest,
    ApiResponse
)
from .service_discovery import ServiceDiscovery, ServiceInstance


logger = logging.getLogger(__name__)


class ApiGateway:
    """
    API Gateway for routing and managing external API requests.
    
    Provides authentication, rate limiting, request validation,
    and response formatting for the orchestration system.
    """
    
    def __init__(self, config: ApiGatewayConfig, service_discovery: Optional[ServiceDiscovery] = None):
        """
        Initialize API gateway.
        
        Args:
            config: API gateway configuration
            service_discovery: Service discovery instance for dynamic routing
        """
        self.config = config
        self.service_discovery = service_discovery
        self.routes: Dict[str, Dict[str, Callable]] = {}  # {path: {method: handler}}
        self.service_routes: Dict[str, str] = {}  # {path_prefix: service_name}
        self.middleware: List[Callable] = []
        self.rate_limiter: Dict[str, List[float]] = {}
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.server_started = False
        self._request_count = 0
        
        # FastAPI app and server instance
        self.app: Optional[FastAPI] = None
        self.server: Optional[uvicorn.Server] = None
        self.server_task: Optional[asyncio.Task] = None
        
        logger.info(f"ApiGateway initialized on {config.host}:{config.port}")
        if service_discovery:
            logger.info("Service discovery integration enabled")
            
        # Initialize FastAPI app
        if FASTAPI_AVAILABLE:
            self._init_fastapi_app()
        else:
            logger.warning("FastAPI not available - falling back to simulation mode")
    
    async def start_server(self) -> None:
        """Start the API gateway server."""
        if self.server_started:
            logger.warning("API gateway already started")
            return
            
        try:
            logger.info(f"Starting API gateway on {self.config.host}:{self.config.port}")
            
            if FASTAPI_AVAILABLE and self.app:
                # Start real FastAPI server
                config = uvicorn.Config(
                    app=self.app,
                    host=self.config.host,
                    port=self.config.port,
                    log_level="info",
                    access_log=True
                )
                self.server = uvicorn.Server(config)
                
                # Start server in background task
                self.server_task = asyncio.create_task(self.server.serve())
                
                # Wait for server to start
                await asyncio.sleep(0.1)
                
                self.server_started = True
                logger.info("Real FastAPI API gateway started successfully")
            else:
                # Fallback to simulation mode
                await asyncio.sleep(0.1)  # Simulate startup time
                self.server_started = True
                logger.info("API gateway started in simulation mode")
            
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
            
            if self.server and self.server_task:
                # Stop real FastAPI server
                self.server.should_exit = True
                if not self.server_task.done():
                    self.server_task.cancel()
                    try:
                        await self.server_task
                    except asyncio.CancelledError:
                        pass
                self.server = None
                self.server_task = None
                logger.info("Real FastAPI server stopped")
            
            self.server_started = False
            logger.info("API gateway stopped")
            
        except Exception as e:
            logger.error(f"Error stopping API gateway: {e}")
            raise
    
    def register_route(self, path: str, method: str, handler: Callable) -> None:
        """
        Register a route handler.
        
        Args:
            path: API endpoint path
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            handler: Async function to handle the request
        """
        if not asyncio.iscoroutinefunction(handler):
            raise ValueError("Handler must be an async function")
            
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
    
    def register_service_route(self, path_prefix: str, service_name: str) -> None:
        """
        Register a path prefix to be routed to a specific service.
        
        Args:
            path_prefix: Path prefix to match (e.g., "/api/v1/users")
            service_name: Service name to route to
        """
        self.service_routes[path_prefix] = service_name
        logger.info(f"Registered service route: {path_prefix} -> {service_name}")
    
    def unregister_service_route(self, path_prefix: str) -> bool:
        """
        Unregister a service route.
        
        Args:
            path_prefix: Path prefix to remove
            
        Returns:
            True if route was removed, False if not found
        """
        if path_prefix in self.service_routes:
            del self.service_routes[path_prefix]
            logger.info(f"Unregistered service route: {path_prefix}")
            return True
        return False
    
    async def get_service_instance(self, service_name: str) -> Optional[ServiceInstance]:
        """
        Get a healthy service instance for routing.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service instance if available, None otherwise
        """
        if not self.service_discovery:
            return None
        
        try:
            instance = await self.service_discovery.get_healthy_instance(service_name)
            if instance:
                logger.debug(f"Found healthy instance for {service_name}: {instance.host}:{instance.port}")
            else:
                logger.warning(f"No healthy instances found for service: {service_name}")
            return instance
        except Exception as e:
            logger.error(f"Error getting service instance for {service_name}: {e}")
            return None
    
    async def proxy_to_service(self, request: ApiRequest, service_name: str) -> Dict[str, Any]:
        """
        Proxy request to a service instance.
        
        Args:
            request: API request to proxy
            service_name: Target service name
            
        Returns:
            Response from the service
        """
        instance = await self.get_service_instance(service_name)
        if not instance:
            return {
                "status_code": 503,
                "body": {"error": f"Service {service_name} not available"}
            }
        
        try:
            import aiohttp
            
            # Build target URL
            target_url = f"http://{instance.host}:{instance.port}{request.path}"
            
            # Prepare headers (exclude host header to avoid conflicts)
            headers = {k: v for k, v in request.headers.items() if k.lower() != 'host'}
            
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    params=request.query_params,
                    json=request.body if request.method in ["POST", "PUT", "PATCH"] else None
                ) as response:
                    body = await response.text()
                    
                    # Try to parse as JSON, fallback to text
                    try:
                        import json
                        body = json.loads(body)
                    except (json.JSONDecodeError, ValueError):
                        pass
                    
                    return {
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "body": body
                    }
                    
        except ImportError:
            logger.error("aiohttp not available for service proxying")
            return {
                "status_code": 500,
                "body": {"error": "Service proxying not available"}
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout proxying request to {service_name}")
            return {
                "status_code": 504,
                "body": {"error": "Gateway timeout"}
            }
            
        except Exception as e:
            logger.error(f"Error proxying request to {service_name}: {e}")
            return {
                "status_code": 502,
                "body": {"error": "Bad gateway"}
            }
    
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
                auth_result = await self._authenticate_request(request)
                if not auth_result["success"]:
                    return self._create_error_response(
                        request.request_id,
                        401,
                        auth_result["message"],
                        start_time
                    )
            
            # Rate limiting check
            rate_limit_result = await self._check_rate_limit(request)
            if not rate_limit_result["success"]:
                return self._create_error_response(
                    request.request_id,
                    429,
                    rate_limit_result["message"],
                    start_time
                )
            
            # CORS handling
            if self.config.enable_cors and request.method == "OPTIONS":
                return self._create_cors_response(request.request_id, start_time)
            
            # Route matching - first try direct handlers
            handler = self._find_handler(request.path, request.method)
            
            # If no direct handler found, try service routing
            if not handler:
                service_name = self._find_service_route(request.path)
                if service_name:
                    # Proxy to service
                    try:
                        result = await self.proxy_to_service(request, service_name)
                        
                        response = ApiResponse(
                            status_code=result.get("status_code", 200),
                            headers={**self._get_response_headers(), **result.get("headers", {})},
                            body=result.get("body"),
                            timestamp=datetime.now(),
                            processing_time=(time.time() - start_time) * 1000,
                            request_id=request.request_id
                        )
                        
                        self._request_count += 1
                        logger.info(f"Proxied request {request.request_id} to {service_name} in {response.processing_time:.2f}ms")
                        return response
                        
                    except Exception as e:
                        logger.error(f"Error proxying to service {service_name}: {e}")
                        return self._create_error_response(
                            request.request_id,
                            502,
                            "Bad gateway",
                            start_time
                        )
                else:
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
        Find handler for the given path and method.
        
        Args:
            path: Request path
            method: HTTP method
            
        Returns:
            Handler function or None
        """
        # Remove API prefix if present
        if path.startswith(self.config.api_prefix):
            path = path[len(self.config.api_prefix):]
        
        return self.routes.get(path, {}).get(method.upper())
    
    def _find_service_route(self, path: str) -> Optional[str]:
        """
        Find service name for the given path based on registered service routes.
        
        Args:
            path: Request path
            
        Returns:
            Service name or None
        """
        # Remove API prefix if present
        if path.startswith(self.config.api_prefix):
            path = path[len(self.config.api_prefix):]
        
        # Find the longest matching prefix
        best_match = None
        best_length = 0
        
        for prefix, service_name in self.service_routes.items():
            if path.startswith(prefix) and len(prefix) > best_length:
                best_match = service_name
                best_length = len(prefix)
        
        return best_match
    
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
        """Get API gateway information."""
        return {
            "server_status": "running" if self.server_started else "stopped",
            "registered_routes": {
                path: list(methods.keys()) 
                for path, methods in self.routes.items()
            },
            "middleware_count": len(self.middleware),
            "api_keys_count": len(self.api_keys),
            "total_requests": self._request_count,
            "config": asdict(self.config)
        }
    
    def get_route_statistics(self) -> Dict[str, Any]:
        """Get route usage statistics."""
        # In a real implementation, this would track actual usage
        return {
            "total_routes": len(self.routes),
            "routes_by_method": {},
            "request_count": self._request_count,
            "average_response_time": "15ms"  # Placeholder
        }
    
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
    
    def _init_fastapi_app(self) -> None:
        """Initialize FastAPI application with routes and middleware."""
        if not FASTAPI_AVAILABLE:
            return
            
        self.app = FastAPI(
            title="LeanVibe Agent Hive API Gateway",
            description="API Gateway for external system integration",
            version="1.0.0"
        )
        
        # Add CORS middleware if enabled
        if self.config.enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.cors_origins,
                allow_credentials=True,
                allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
                allow_headers=["*"],
            )
        
        # Add health check endpoint
        @self.app.get("/health")
        async def health_check_endpoint():
            health_status = await self.health_check()
            return health_status
        
        # Add catch-all route for dynamic handling
        @self.app.api_route(
            "/{path:path}",
            methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        )
        async def catch_all_route(request: Request, path: str):
            """Handle all requests through the ApiGateway logic."""
            # Convert FastAPI Request to ApiRequest
            api_request = await self._convert_fastapi_request(request, path)
            
            # Process through existing handle_request logic
            api_response = await self.handle_request(api_request)
            
            # Convert ApiResponse back to FastAPI response
            return self._convert_to_fastapi_response(api_response)
    
    async def _convert_fastapi_request(self, request: Request, path: str) -> ApiRequest:
        """Convert FastAPI Request to ApiRequest."""
        try:
            body = await request.json()
        except:
            body = None
            
        return ApiRequest(
            method=request.method,
            path=f"/{path}" if path else "/",
            headers=dict(request.headers),
            query_params=dict(request.query_params),
            body=body,
            timestamp=datetime.now(),
            request_id=str(uuid.uuid4()),
            client_ip=request.client.host if request.client else "unknown"
        )
    
    def _convert_to_fastapi_response(self, api_response: ApiResponse) -> Response:
        """Convert ApiResponse to FastAPI Response."""
        import json
        
        content = json.dumps(api_response.body) if api_response.body else ""
        
        return Response(
            content=content,
            status_code=api_response.status_code,
            headers=api_response.headers,
            media_type="application/json"
        )
