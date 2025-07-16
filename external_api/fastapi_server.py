"""
Real FastAPI HTTP Server for API Gateway
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from .models import (
    ApiGatewayConfig,
    ApiRequest,
    ApiResponse,
    WebhookConfig,
    WebhookEvent,
    WebhookEventType,
    EventPriority
)
from .api_gateway import ApiGateway
from .webhook_server import WebhookServer
from .service_discovery import ServiceDiscovery


logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    services: Dict[str, Any]


class WebhookPayload(BaseModel):
    """Webhook payload model."""
    type: str
    data: Dict[str, Any]
    priority: Optional[str] = "medium"
    source: Optional[str] = None


class FastAPIServer:
    """
    Real FastAPI HTTP server implementation.
    
    Replaces simulation with actual HTTP server functionality.
    """
    
    def __init__(self, gateway_config: ApiGatewayConfig, webhook_config: WebhookConfig):
        """
        Initialize FastAPI server.
        
        Args:
            gateway_config: API gateway configuration
            webhook_config: Webhook server configuration
        """
        self.gateway_config = gateway_config
        self.webhook_config = webhook_config
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="LeanVibe Agent Hive API Gateway",
            description="Real HTTP server for agent coordination and webhooks",
            version="1.0.0"
        )
        
        # Add CORS middleware
        if gateway_config.enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=gateway_config.cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"]
            )
        
        # Initialize components
        self.service_discovery = ServiceDiscovery()
        self.api_gateway = ApiGateway(gateway_config, self.service_discovery)
        self.webhook_server = WebhookServer(webhook_config)
        
        self.server = None
        self.server_task = None
        
        # Setup routes
        self._setup_routes()
        
        logger.info("FastAPI server initialized")
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint."""
            gateway_health = await self.api_gateway.health_check()
            webhook_health = await self.webhook_server.health_check()
            
            return HealthResponse(
                status="healthy" if gateway_health["status"] == "healthy" and webhook_health["status"] == "healthy" else "degraded",
                timestamp=datetime.now().isoformat(),
                services={
                    "api_gateway": gateway_health,
                    "webhook_server": webhook_health,
                    "service_discovery": await self.service_discovery.health_check()
                }
            )
        
        @self.app.post("/webhooks/{event_type}")
        async def webhook_handler(event_type: str, payload: WebhookPayload, request: Request):
            """Handle incoming webhooks."""
            client_ip = request.client.host if request.client else "unknown"
            
            # Create webhook event
            webhook_payload = {
                "type": event_type,
                "data": payload.data,
                "priority": payload.priority,
                "source": payload.source or client_ip
            }
            
            result = await self.webhook_server.handle_webhook(webhook_payload, client_ip)
            
            if result.get("status") == "error":
                raise HTTPException(
                    status_code=result.get("code", 500),
                    detail=result.get("message", "Webhook processing failed")
                )
            
            return result
        
        @self.app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
        async def api_proxy(path: str, request: Request):
            """Proxy API requests through the gateway."""
            # Extract request data
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.json()
                except Exception:
                    body = {}
            
            # Create API request
            api_request = ApiRequest(
                request_id=str(uuid.uuid4()),
                method=request.method,
                path=f"/{path}",
                headers=dict(request.headers),
                query_params=dict(request.query_params),
                body=body,
                client_ip=request.client.host if request.client else "unknown",
                timestamp=datetime.now()
            )
            
            # Process through gateway
            response = await self.api_gateway.handle_request(api_request)
            
            return {
                "status_code": response.status_code,
                "headers": response.headers,
                "body": response.body,
                "processing_time": response.processing_time,
                "request_id": response.request_id
            }
        
        @self.app.get("/api/gateway/info")
        async def gateway_info():
            """Get API gateway information."""
            return self.api_gateway.get_gateway_info()
        
        @self.app.get("/api/gateway/routes")
        async def gateway_routes():
            """Get registered routes."""
            return self.api_gateway.get_route_statistics()
        
        @self.app.get("/api/webhook/status")
        async def webhook_status():
            """Get webhook server status."""
            return self.webhook_server.get_handler_info()
        
        @self.app.get("/api/webhook/rate-limits")
        async def webhook_rate_limits():
            """Get rate limiting status."""
            return self.webhook_server.get_rate_limit_status()
        
        @self.app.get("/api/services")
        async def list_services():
            """List registered services."""
            return await self.service_discovery.list_services()
        
        @self.app.post("/api/services/register")
        async def register_service(service_data: Dict[str, Any]):
            """Register a service."""
            from .service_discovery import ServiceInstance
            
            instance = ServiceInstance(
                service_name=service_data["name"],
                instance_id=service_data.get("instance_id", str(uuid.uuid4())),
                host=service_data["host"],
                port=service_data["port"],
                metadata=service_data.get("metadata", {})
            )
            
            await self.service_discovery.register_service(instance)
            return {"status": "registered", "instance_id": instance.instance_id}
    
    async def start_server(self):
        """Start the FastAPI server."""
        try:
            # Start components
            await self.api_gateway.start_server()
            await self.webhook_server.start_server()
            await self.service_discovery.start()
            
            # Configure uvicorn
            config = uvicorn.Config(
                app=self.app,
                host=self.gateway_config.host,
                port=self.gateway_config.port,
                log_level="info",
                access_log=True
            )
            
            self.server = uvicorn.Server(config)
            
            # Start server in background task
            self.server_task = asyncio.create_task(self.server.serve())
            
            logger.info(f"FastAPI server started on {self.gateway_config.host}:{self.gateway_config.port}")
            
        except Exception as e:
            logger.error(f"Failed to start FastAPI server: {e}")
            raise
    
    async def stop_server(self):
        """Stop the FastAPI server."""
        try:
            if self.server:
                self.server.should_exit = True
                
            if self.server_task:
                self.server_task.cancel()
                try:
                    await self.server_task
                except asyncio.CancelledError:
                    pass
            
            # Stop components
            await self.api_gateway.stop_server()
            await self.webhook_server.stop_server()
            await self.service_discovery.stop()
            
            logger.info("FastAPI server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping FastAPI server: {e}")
            raise
    
    def register_webhook_handler(self, event_type: str, handler):
        """Register a webhook handler."""
        self.webhook_server.register_handler(event_type, handler)
    
    def register_api_route(self, path: str, method: str, handler):
        """Register an API route."""
        self.api_gateway.register_route(path, method, handler)
    
    def register_service_route(self, path_prefix: str, service_name: str):
        """Register a service route for proxying."""
        self.api_gateway.register_service_route(path_prefix, service_name)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            gateway_health = await self.api_gateway.health_check()
            webhook_health = await self.webhook_server.health_check()
            service_discovery_health = await self.service_discovery.health_check()
            
            overall_healthy = all([
                gateway_health.get("status") == "healthy",
                webhook_health.get("status") == "healthy",
                service_discovery_health.get("status") == "healthy"
            ])
            
            return {
                "status": "healthy" if overall_healthy else "degraded",
                "server_running": self.server_task is not None and not self.server_task.done(),
                "components": {
                    "api_gateway": gateway_health,
                    "webhook_server": webhook_health,
                    "service_discovery": service_discovery_health
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


async def create_server(gateway_config: ApiGatewayConfig, webhook_config: WebhookConfig) -> FastAPIServer:
    """
    Create and configure FastAPI server.
    
    Args:
        gateway_config: API gateway configuration
        webhook_config: Webhook configuration
        
    Returns:
        Configured FastAPI server instance
    """
    server = FastAPIServer(gateway_config, webhook_config)
    return server


async def main():
    """Main entry point for running the server standalone."""
    from .models import ApiGatewayConfig, WebhookConfig
    
    # Default configurations
    gateway_config = ApiGatewayConfig(
        host="0.0.0.0",
        port=8000,
        api_prefix="/api/v1",
        enable_cors=True,
        cors_origins=["*"]
    )
    
    webhook_config = WebhookConfig(
        host="0.0.0.0",
        port=8001,
        endpoint_prefix="/webhooks"
    )
    
    server = await create_server(gateway_config, webhook_config)
    
    try:
        await server.start_server()
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        await server.stop_server()


if __name__ == "__main__":
    asyncio.run(main())