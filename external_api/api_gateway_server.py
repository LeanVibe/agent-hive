"""
FastAPI-based API Gateway Server

Provides a real HTTP server implementation that wraps the existing ApiGateway
functionality with FastAPI for production use.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .api_gateway import ApiGateway
from .models import ApiGatewayConfig, ApiRequest, ApiResponse
from .service_discovery import ServiceDiscovery


logger = logging.getLogger(__name__)


class ApiGatewayServer:
    """
    FastAPI-based API Gateway Server.
    
    Wraps the existing ApiGateway functionality with a real HTTP server.
    """
    
    def __init__(self, config: ApiGatewayConfig, service_discovery: Optional[ServiceDiscovery] = None):
        """
        Initialize the API Gateway server.
        
        Args:
            config: API gateway configuration
            service_discovery: Optional service discovery instance
        """
        self.config = config
        self.service_discovery = service_discovery
        self.api_gateway = ApiGateway(config, service_discovery)
        self.app = FastAPI(
            title="LeanVibe Agent Hive API Gateway",
            version="1.0.0",
            description="API Gateway for LeanVibe Agent Hive orchestration system"
        )
        
        # Setup CORS if enabled
        if config.enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=config.cors_origins,
                allow_credentials=True,
                allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
                allow_headers=["*"],
            )
        
        # Setup routes
        self._setup_routes()
        
        # Server state
        self.server_task: Optional[asyncio.Task] = None
        
        logger.info(f"FastAPI API Gateway initialized on {config.host}:{config.port}")
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            gateway_health = await self.api_gateway.health_check()
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "gateway": gateway_health
            }
        
        @self.app.get("/gateway/info")
        async def gateway_info():
            """Get gateway information."""
            return self.api_gateway.get_gateway_info()
        
        @self.app.get("/gateway/stats")
        async def gateway_stats():
            """Get gateway statistics."""
            return self.api_gateway.get_route_statistics()
        
        # Catch-all route to handle all API requests
        @self.app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
        async def handle_api_request(request: Request, path: str):
            """Handle all API requests through the gateway."""
            start_time = datetime.now()
            
            # Convert FastAPI request to ApiRequest
            api_request = await self._convert_request(request)
            
            # Process through API Gateway
            api_response = await self.api_gateway.handle_request(api_request)
            
            # Prepare response headers
            response_headers = api_response.headers.copy()
            
            # Add processing time header
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            response_headers["X-Processing-Time"] = f"{processing_time:.2f}ms"
            
            # Convert back to FastAPI response
            response = JSONResponse(
                status_code=api_response.status_code,
                content=api_response.body,
                headers=response_headers
            )
            
            return response
    
    async def _convert_request(self, request: Request) -> ApiRequest:
        """
        Convert FastAPI request to ApiRequest.
        
        Args:
            request: FastAPI request object
            
        Returns:
            ApiRequest object
        """
        # Get body if present
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
            except:
                body = None
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Debug headers
        headers_dict = dict(request.headers)
        logger.debug(f"Request headers: {headers_dict}")
        
        return ApiRequest(
            method=request.method,
            path=request.url.path,
            headers=headers_dict,
            query_params=dict(request.query_params),
            body=body,
            timestamp=datetime.now(),
            request_id=request.headers.get("X-Request-ID", f"req-{datetime.now().timestamp()}"),
            client_ip=client_ip
        )
    
    async def start_server(self) -> None:
        """Start the FastAPI server."""
        if self.server_task:
            logger.warning("Server already running")
            return
        
        try:
            # Start the underlying API Gateway
            await self.api_gateway.start_server()
            
            # Create server config
            server_config = uvicorn.Config(
                app=self.app,
                host=self.config.host,
                port=self.config.port,
                log_level="info",
                access_log=True
            )
            
            # Start server in background task
            server = uvicorn.Server(server_config)
            self.server_task = asyncio.create_task(server.serve())
            
            logger.info(f"FastAPI API Gateway server started on {self.config.host}:{self.config.port}")
            
        except Exception as e:
            logger.error(f"Failed to start API Gateway server: {e}")
            raise
    
    async def stop_server(self) -> None:
        """Stop the FastAPI server."""
        if not self.server_task:
            logger.warning("Server not running")
            return
        
        try:
            # Cancel the server task
            self.server_task.cancel()
            
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
            
            self.server_task = None
            
            # Stop the underlying API Gateway
            await self.api_gateway.stop_server()
            
            logger.info("FastAPI API Gateway server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping API Gateway server: {e}")
            raise
    
    def register_route(self, path: str, method: str, handler):
        """
        Register a route handler with the underlying API Gateway.
        
        Args:
            path: API endpoint path
            method: HTTP method
            handler: Handler function
        """
        self.api_gateway.register_route(path, method, handler)
    
    def register_service_route(self, path_prefix: str, service_name: str):
        """
        Register a service route for proxying.
        
        Args:
            path_prefix: Path prefix to match
            service_name: Service name to route to
        """
        self.api_gateway.register_service_route(path_prefix, service_name)
    
    def register_api_key(self, api_key: str, metadata: Dict[str, Any]):
        """
        Register an API key.
        
        Args:
            api_key: API key string
            metadata: Associated metadata
        """
        self.api_gateway.register_api_key(api_key, metadata)
    
    def add_middleware(self, middleware):
        """
        Add middleware to the API Gateway.
        
        Args:
            middleware: Middleware function
        """
        self.api_gateway.add_middleware(middleware)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.
        
        Returns:
            Health status information
        """
        gateway_health = await self.api_gateway.health_check()
        return {
            "status": "healthy" if self.server_task and not self.server_task.done() else "unhealthy",
            "server_running": self.server_task is not None and not self.server_task.done(),
            "gateway": gateway_health,
            "timestamp": datetime.now().isoformat()
        }


def create_api_gateway_server(
    config: Optional[ApiGatewayConfig] = None,
    service_discovery: Optional[ServiceDiscovery] = None
) -> ApiGatewayServer:
    """
    Create and configure an API Gateway server.
    
    Args:
        config: Optional API gateway configuration
        service_discovery: Optional service discovery instance
        
    Returns:
        Configured API Gateway server
    """
    if config is None:
        config = ApiGatewayConfig()
    
    return ApiGatewayServer(config, service_discovery)


async def run_api_gateway_server(
    config: Optional[ApiGatewayConfig] = None,
    service_discovery: Optional[ServiceDiscovery] = None
) -> None:
    """
    Run the API Gateway server.
    
    Args:
        config: Optional API gateway configuration
        service_discovery: Optional service discovery instance
    """
    server = create_api_gateway_server(config, service_discovery)
    
    try:
        await server.start_server()
        
        # Keep server running
        if server.server_task:
            await server.server_task
            
    except KeyboardInterrupt:
        logger.info("Shutting down API Gateway server...")
        await server.stop_server()
    except Exception as e:
        logger.error(f"API Gateway server error: {e}")
        await server.stop_server()
        raise


if __name__ == "__main__":
    # Example usage
    asyncio.run(run_api_gateway_server())