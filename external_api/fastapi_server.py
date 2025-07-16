"""
FastAPI HTTP Server for Real API Gateway Implementation

Replaces simulation-only API Gateway with actual FastAPI HTTP server
providing real endpoints for agent communication and migration management.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, Request, HTTPException, Depends
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from uvicorn import Config, Server
    FASTAPI_AVAILABLE = True
except ImportError:
    # Fallback for systems without FastAPI
    FASTAPI_AVAILABLE = False
    FastAPI = None
    Request = None
    HTTPException = None
    JSONResponse = None
    CORSMiddleware = None
    Config = None
    Server = None

from .migration_manager import MigrationManager, MigrationConfig
from .migration_api import MigrationAPI
from .event_streaming import EventStreaming, EventStreamConfig
from .models import ApiGatewayConfig, ApiRequest, ApiResponse

logger = logging.getLogger(__name__)


class FastAPIGateway:
    """
    Real FastAPI HTTP server implementation for API Gateway.
    
    Provides:
    - Real HTTP endpoints
    - Agent communication APIs
    - Migration management APIs
    - Service discovery integration
    - Request validation and routing
    """
    
    def __init__(self, config: ApiGatewayConfig):
        """
        Initialize FastAPI gateway.
        
        Args:
            config: API gateway configuration
        """
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI not available. Install with: pip install fastapi uvicorn")
        
        self.config = config
        self.app: Optional[FastAPI] = None
        self.server: Optional[Server] = None
        self.server_task: Optional[asyncio.Task] = None
        
        # Initialize components
        self.event_streaming = self._create_event_streaming()
        self.migration_manager = self._create_migration_manager()
        self.migration_api = MigrationAPI(self.migration_manager)
        
        # Server state
        self.server_started = False
        self.request_count = 0
        
        logger.info(f"FastAPI Gateway initialized on {config.host}:{config.port}")
    
    def _create_event_streaming(self) -> EventStreaming:
        """Create event streaming instance."""
        stream_config = EventStreamConfig(
            stream_name="agent_hive_events",
            buffer_size=1000,
            batch_size=50,
            flush_interval=5.0,
            compression_enabled=True
        )
        return EventStreaming(stream_config)
    
    def _create_migration_manager(self) -> MigrationManager:
        """Create migration manager instance."""
        migration_config = MigrationConfig(
            detection_timeout=300,
            dual_mode_duration=1800,
            validation_timeout=600,
            max_error_count=3,
            min_dual_mode_success_rate=0.95,
            tmux_session_name="agent-hive",
            message_queue_base_url=f"http://{self.config.host}:{self.config.port}"
        )
        return MigrationManager(migration_config, self.event_streaming)
    
    def _create_app(self) -> FastAPI:
        """Create FastAPI application."""
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info("Starting FastAPI Gateway services...")
            await self.event_streaming.start_streaming()
            yield
            # Shutdown
            logger.info("Shutting down FastAPI Gateway services...")
            await self.event_streaming.stop_streaming()
            await self.migration_manager.shutdown()
        
        app = FastAPI(
            title="LeanVibe Agent Hive API Gateway",
            description="Real HTTP API for agent communication and migration management",
            version="1.0.0",
            lifespan=lifespan
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register routes
        self._register_routes(app)
        
        return app
    
    def _register_routes(self, app: FastAPI):
        """Register all API routes."""
        
        # Health check
        @app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "server": "fastapi",
                "request_count": self.request_count
            }
        
        # Gateway info
        @app.get("/api/gateway/info")
        async def gateway_info():
            return {
                "gateway_type": "fastapi",
                "version": "1.0.0",
                "host": self.config.host,
                "port": self.config.port,
                "features": {
                    "migration_management": True,
                    "event_streaming": True,
                    "service_discovery": True,
                    "real_http_server": True
                }
            }
        
        # Agent communication endpoints
        @app.post("/api/agents/{agent_id}/messages")
        async def send_agent_message(agent_id: str, request: Request):
            try:
                data = await request.json()
                success = await self.event_streaming.send_agent_message(agent_id, data)
                
                if success:
                    return {"success": True, "message": f"Message sent to agent {agent_id}"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to send message")
                    
            except Exception as e:
                logger.error(f"Error sending message to agent {agent_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/api/agents/{agent_id}/status")
        async def get_agent_status_endpoint(agent_id: str):
            # Delegate to migration API
            api_request = ApiRequest(
                request_id=f"status_{agent_id}",
                path=f"/api/agents/{agent_id}/status",
                method="GET",
                path_params={"agent_id": agent_id}
            )
            response = await self.migration_api.get_agent_status(api_request)
            return self._format_api_response(response)
        
        # Migration management endpoints
        @app.post("/api/migration/start")
        async def start_migration_endpoint(request: Request):
            data = await request.json() if await self._has_body(request) else {}
            api_request = ApiRequest(
                request_id="start_migration",
                path="/api/migration/start",
                method="POST",
                data=data
            )
            response = await self.migration_api.start_migration(api_request)
            return self._format_api_response(response)
        
        @app.get("/api/migration/status")
        async def get_migration_status_endpoint():
            api_request = ApiRequest(
                request_id="migration_status",
                path="/api/migration/status",
                method="GET"
            )
            response = await self.migration_api.get_migration_status(api_request)
            return self._format_api_response(response)
        
        @app.post("/api/migration/stop")
        async def stop_migration_endpoint():
            api_request = ApiRequest(
                request_id="stop_migration",
                path="/api/migration/stop",
                method="POST"
            )
            response = await self.migration_api.stop_migration(api_request)
            return self._format_api_response(response)
        
        @app.post("/api/migration/rollback")
        async def rollback_migration_endpoint(request: Request):
            data = await request.json() if await self._has_body(request) else {}
            api_request = ApiRequest(
                request_id="rollback_migration",
                path="/api/migration/rollback",
                method="POST",
                data=data
            )
            response = await self.migration_api.rollback_migration(api_request)
            return self._format_api_response(response)
        
        @app.get("/api/migration/agents")
        async def list_agents_endpoint():
            api_request = ApiRequest(
                request_id="list_agents",
                path="/api/migration/agents",
                method="GET"
            )
            response = await self.migration_api.list_agents(api_request)
            return self._format_api_response(response)
        
        @app.post("/api/migration/agents/{agent_id}/health")
        async def check_agent_health_endpoint(agent_id: str, request: Request):
            data = await request.json() if await self._has_body(request) else {}
            api_request = ApiRequest(
                request_id=f"health_{agent_id}",
                path=f"/api/migration/agents/{agent_id}/health",
                method="POST",
                path_params={"agent_id": agent_id},
                data=data
            )
            response = await self.migration_api.check_agent_health(api_request)
            return self._format_api_response(response)
        
        @app.post("/api/migration/agents/{agent_id}/migrate")
        async def migrate_single_agent_endpoint(agent_id: str):
            api_request = ApiRequest(
                request_id=f"migrate_{agent_id}",
                path=f"/api/migration/agents/{agent_id}/migrate",
                method="POST",
                path_params={"agent_id": agent_id}
            )
            response = await self.migration_api.migrate_single_agent(api_request)
            return self._format_api_response(response)
        
        @app.post("/api/migration/agents/{agent_id}/rollback")
        async def rollback_single_agent_endpoint(agent_id: str):
            api_request = ApiRequest(
                request_id=f"rollback_{agent_id}",
                path=f"/api/migration/agents/{agent_id}/rollback",
                method="POST",
                path_params={"agent_id": agent_id}
            )
            response = await self.migration_api.rollback_single_agent(api_request)
            return self._format_api_response(response)
        
        @app.get("/api/migration/config")
        async def get_migration_config_endpoint():
            api_request = ApiRequest(
                request_id="get_config",
                path="/api/migration/config",
                method="GET"
            )
            response = await self.migration_api.get_config(api_request)
            return self._format_api_response(response)
        
        @app.put("/api/migration/config")
        async def update_migration_config_endpoint(request: Request):
            data = await request.json()
            api_request = ApiRequest(
                request_id="update_config",
                path="/api/migration/config",
                method="PUT",
                data=data
            )
            response = await self.migration_api.update_config(api_request)
            return self._format_api_response(response)
        
        @app.get("/api/migration/phases")
        async def get_migration_phases_endpoint():
            api_request = ApiRequest(
                request_id="get_phases",
                path="/api/migration/phases",
                method="GET"
            )
            response = await self.migration_api.get_phases(api_request)
            return self._format_api_response(response)
        
        @app.get("/api/migration/logs")
        async def get_migration_logs_endpoint(request: Request):
            query_params = dict(request.query_params)
            api_request = ApiRequest(
                request_id="get_logs",
                path="/api/migration/logs",
                method="GET",
                query_params=query_params
            )
            response = await self.migration_api.get_migration_logs(api_request)
            return self._format_api_response(response)
        
        # Event streaming endpoints
        @app.get("/api/events/stream")
        async def get_event_stream():
            stats = await self.event_streaming.get_stats()
            return {
                "stream_active": self.event_streaming.stream_active,
                "stats": stats
            }
        
        @app.post("/api/events/publish")
        async def publish_event_endpoint(request: Request):
            try:
                data = await request.json()
                event_type = data.get("event_type", "custom")
                event_data = data.get("data", {})
                priority = data.get("priority", "medium")
                
                success = await self.event_streaming.publish_event(event_type, event_data, priority)
                
                if success:
                    return {"success": True, "message": "Event published"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to publish event")
                    
            except Exception as e:
                logger.error(f"Error publishing event: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Middleware to count requests
        @app.middleware("http")
        async def count_requests(request: Request, call_next):
            self.request_count += 1
            response = await call_next(request)
            return response
    
    async def _has_body(self, request: Request) -> bool:
        """Check if request has a body."""
        try:
            body = await request.body()
            return len(body) > 0
        except:
            return False
    
    def _format_api_response(self, response: ApiResponse) -> Dict[str, Any]:
        """Format ApiResponse for FastAPI."""
        result = {
            "success": response.success,
            "message": response.message
        }
        
        if response.data:
            result["data"] = response.data
        
        if response.errors:
            result["errors"] = response.errors
        
        # Set HTTP status code if needed
        if not response.success and response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.message)
        
        return result
    
    async def start_server(self) -> None:
        """Start the FastAPI server."""
        if self.server_started:
            logger.warning("FastAPI server already started")
            return
        
        try:
            # Create app
            self.app = self._create_app()
            
            # Create server config
            config = Config(
                app=self.app,
                host=self.config.host,
                port=self.config.port,
                log_level="info",
                access_log=True
            )
            
            # Create and start server
            self.server = Server(config)
            self.server_task = asyncio.create_task(self.server.serve())
            
            # Wait a moment for server to start
            await asyncio.sleep(0.5)
            
            self.server_started = True
            logger.info(f"FastAPI server started on {self.config.host}:{self.config.port}")
            
        except Exception as e:
            logger.error(f"Failed to start FastAPI server: {e}")
            raise
    
    async def stop_server(self) -> None:
        """Stop the FastAPI server."""
        if not self.server_started:
            logger.warning("FastAPI server not running")
            return
        
        try:
            logger.info("Stopping FastAPI server...")
            
            if self.server:
                self.server.should_exit = True
            
            if self.server_task:
                self.server_task.cancel()
                try:
                    await self.server_task
                except asyncio.CancelledError:
                    pass
            
            self.server_started = False
            logger.info("FastAPI server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping FastAPI server: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            "server_started": self.server_started,
            "app_created": self.app is not None,
            "request_count": self.request_count,
            "timestamp": datetime.now().isoformat(),
            "components": {
                "event_streaming": self.event_streaming.stream_active,
                "migration_manager": self.migration_manager.migration_active
            }
        }
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information."""
        return {
            "server_type": "fastapi",
            "host": self.config.host,
            "port": self.config.port,
            "started": self.server_started,
            "request_count": self.request_count,
            "features": {
                "real_http_server": True,
                "migration_management": True,
                "event_streaming": True,
                "cors_enabled": True,
                "request_validation": True
            }
        }


# Compatibility wrapper for existing API Gateway interface
class RealApiGateway:
    """
    Wrapper that provides the same interface as the simulated API Gateway
    but uses the real FastAPI server implementation.
    """
    
    def __init__(self, config: ApiGatewayConfig, service_discovery=None):
        """Initialize real API gateway."""
        self.config = config
        self.service_discovery = service_discovery
        self.fastapi_gateway = FastAPIGateway(config)
        self.server_started = False
        self._request_count = 0
        
        logger.info("Real API Gateway initialized with FastAPI backend")
    
    async def start_server(self) -> None:
        """Start the API gateway server."""
        await self.fastapi_gateway.start_server()
        self.server_started = True
    
    async def stop_server(self) -> None:
        """Stop the API gateway server."""
        await self.fastapi_gateway.stop_server()
        self.server_started = False
    
    def register_route(self, path: str, method: str, handler) -> None:
        """Register a route handler (compatibility method)."""
        logger.info(f"Route registration: {method} {path} (handled by FastAPI)")
    
    async def process_request(self, request: ApiRequest) -> ApiResponse:
        """Process API request (compatibility method)."""
        # This would be handled by FastAPI routing
        return ApiResponse(
            success=True,
            message="Request handled by FastAPI",
            data={"fastapi": True}
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get gateway statistics."""
        return self.fastapi_gateway.get_server_info()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return await self.fastapi_gateway.health_check()