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

import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import aiohttp

from .models import (
    ApiGatewayConfig,
    ApiRequest,
    ApiResponse
)
from .service_discovery import ServiceDiscovery


logger = logging.getLogger(__name__)


class ApiGateway:
    """
    API Gateway for routing and managing external API requests.
    
    Provides authentication, rate limiting, request validation,
    and response formatting for the orchestration system.
    """
    
    def __init__(self, config: ApiGatewayConfig):
        """
        Initialize API gateway.
        
        Args:
            config: API gateway configuration
        """
        self.config = config
        self.routes: Dict[str, Dict[str, Callable]] = {}  # {path: {method: handler}}
        self.middleware: List[Callable] = []
        self.rate_limiter: Dict[str, List[float]] = {}
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.server_started = False
        self._request_count = 0
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="LeanVibe Agent Hive API Gateway",
            description="Unified API for agent hive orchestration",
            version="1.0.0"
        )
        
        # Service discovery integration
        self.service_discovery = ServiceDiscovery()
        
        # Configure CORS if enabled
        if self.config.enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        
        # Setup catch-all route for dynamic routing
        self.app.add_api_route("/{path:path}", self._handle_fastapi_request, methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
        
        # Server instance for stopping
        self.server = None
        
        logger.info(f"ApiGateway initialized on {config.host}:{config.port}")
    
    async def start_server(self) -> None:
        """Start the API gateway server."""
        if self.server_started:
            logger.warning("API gateway already started")
            return
            
        try:
            logger.info(f"Starting API gateway on {self.config.host}:{self.config.port}")
            
            # Create uvicorn config
            config = uvicorn.Config(
                app=self.app,
                host=self.config.host,
                port=self.config.port,
                log_level="info",
                access_log=True
            )
            
            # Create and start server
            self.server = uvicorn.Server(config)
            
            # Start server in background task
            self._server_task = asyncio.create_task(self.server.serve())
            
            # Wait a bit for server to start
            await asyncio.sleep(0.5)
            
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
            
            if self.server:
                # Stop the uvicorn server
                self.server.should_exit = True
                
                # Cancel the server task
                if hasattr(self, '_server_task'):
                    self._server_task.cancel()
                    try:
                        await self._server_task
                    except asyncio.CancelledError:
                        pass
            
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
    
    async def _handle_fastapi_request(self, request: Request) -> Response:
        """
        FastAPI route handler that converts to our internal ApiRequest format.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            FastAPI Response object
        """
        # Convert FastAPI request to our ApiRequest format
        path = request.url.path
        method = request.method
        headers = dict(request.headers)
        query_params = dict(request.query_params)
        
        # Get body for non-GET requests
        body = None
        if method != "GET":
            try:
                body = await request.json()
            except:
                body_bytes = await request.body()
                body = body_bytes.decode() if body_bytes else None
        
        # Create our internal request object
        api_request = ApiRequest(
            method=method,
            path=path,
            headers=headers,
            query_params=query_params,
            body=body,
            timestamp=datetime.now(),
            request_id=f"req-{uuid.uuid4().hex[:8]}",
            client_ip=request.client.host if request.client else "unknown"
        )
        
        # Process request using our existing logic
        api_response = await self.handle_request(api_request)
        
        # Convert our ApiResponse to FastAPI Response
        return Response(
            content=json.dumps(api_response.body) if api_response.body is not None else "",
            status_code=api_response.status_code,
            headers=api_response.headers,
            media_type="application/json"
        )
    
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
            
            # Check for service routing first (e.g., /api/v1/services/{service_name}/...)
            service_name = self._extract_service_name(request.path)
            if service_name:
                # Proxy to discovered service
                return await self.proxy_to_service(request, service_name)
            
            # Route matching for local handlers
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
    
    async def proxy_to_service(self, request: ApiRequest, service_name: str) -> ApiResponse:
        """
        Proxy request to a discovered service instance.
        
        Args:
            request: The API request to proxy
            service_name: Name of the service to proxy to
            
        Returns:
            API response from the service
        """
        start_time = time.time()
        
        try:
            # Find a healthy service instance
            service_instance = await self.service_discovery.get_healthy_instance(service_name)
            
            if not service_instance:
                logger.warning(f"No healthy instances found for service: {service_name}")
                return self._create_error_response(
                    request.request_id,
                    503,
                    f"Service {service_name} unavailable",
                    start_time
                )
            
            # Build target URL
            target_url = f"http://{service_instance.host}:{service_instance.port}{request.path}"
            
            # Prepare request data
            request_data = {
                "method": request.method,
                "url": target_url,
                "params": request.query_params,
                "headers": request.headers,
                "timeout": aiohttp.ClientTimeout(total=self.config.request_timeout)
            }
            
            # Add body for non-GET requests
            if request.method != "GET" and request.body is not None:
                if isinstance(request.body, dict):
                    request_data["json"] = request.body
                else:
                    request_data["data"] = request.body
            
            # Make the proxied request
            async with aiohttp.ClientSession() as session:
                async with session.request(**request_data) as response:
                    # Read response body
                    response_body = await response.text()
                    
                    # Try to parse as JSON, fallback to text
                    try:
                        response_json = json.loads(response_body) if response_body else None
                    except json.JSONDecodeError:
                        response_json = {"content": response_body}
                    
                    # Create response headers
                    response_headers = dict(response.headers)
                    response_headers.update(self._get_response_headers())
                    
                    processing_time = (time.time() - start_time) * 1000
                    logger.info(f"Proxied request {request.request_id} to {service_name} in {processing_time:.2f}ms")
                    
                    return ApiResponse(
                        status_code=response.status,
                        headers=response_headers,
                        body=response_json,
                        timestamp=datetime.now(),
                        processing_time=processing_time,
                        request_id=request.request_id
                    )
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout proxying request {request.request_id} to {service_name}")
            return self._create_error_response(
                request.request_id,
                504,
                f"Service {service_name} timeout",
                start_time
            )
            
        except Exception as e:
            logger.error(f"Error proxying request {request.request_id} to {service_name}: {e}")
            return self._create_error_response(
                request.request_id,
                502,
                f"Bad gateway to {service_name}",
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
    
    def _extract_service_name(self, path: str) -> Optional[str]:
        """
        Extract service name from request path for service discovery routing.
        
        Expected patterns:
        - /api/v1/services/{service_name}/...
        - /services/{service_name}/...
        
        Args:
            path: Request path
            
        Returns:
            Service name if found, None otherwise
        """
        # Remove API prefix if present
        if path.startswith(self.config.api_prefix):
            path = path[len(self.config.api_prefix):]
        
        # Check for service routing patterns
        if path.startswith("/services/"):
            parts = path.split("/")
            if len(parts) >= 3:  # ["", "services", "service_name", ...]
                service_name = parts[2]
                if service_name:  # Ensure not empty
                    return service_name
        
        return None
    
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