"""
REST API for Service Discovery System

Provides HTTP endpoints for service registration, discovery, and management.
Supports external access to the service discovery functionality.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from .service_discovery import ServiceDiscovery, ServiceInstance

logger = logging.getLogger(__name__)


# Pydantic models for API request/response
class ServiceInstanceRequest(BaseModel):
    """Request model for service registration."""
    service_id: str = Field(..., description="Unique service identifier")
    service_name: str = Field(..., description="Service name")
    host: str = Field(..., description="Service host/IP")
    port: int = Field(..., ge=1, le=65535, description="Service port")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Service metadata")
    health_check_url: Optional[str] = Field(
        None, description="Health check endpoint URL")
    tags: List[str] = Field(default_factory=list, description="Service tags")
    version: str = Field(default="1.0.0", description="Service version")


class ServiceInstanceResponse(BaseModel):
    """Response model for service information."""
    service_id: str
    service_name: str
    host: str
    port: int
    metadata: Dict[str, Any]
    health_check_url: Optional[str]
    tags: List[str]
    version: str
    status: str
    registered_at: str
    last_heartbeat: str


class ServiceDiscoveryResponse(BaseModel):
    """Response model for service discovery."""
    services: List[ServiceInstanceResponse]
    total_count: int


class SystemInfoResponse(BaseModel):
    """Response model for system information."""
    total_instances: int
    healthy_instances: int
    unique_services: int
    service_names: List[str]
    running: bool
    health_check_interval: int


class ServiceDiscoveryAPI:
    """
    REST API wrapper for Service Discovery system.

    Provides HTTP endpoints for external systems to interact with
    service discovery functionality.
    """

    def __init__(
            self,
            service_discovery: ServiceDiscovery,
            host: str = "0.0.0.0",
            port: int = 8000):
        """
        Initialize Service Discovery API.

        Args:
            service_discovery: ServiceDiscovery instance
            host: API server host
            port: API server port
        """
        self.service_discovery = service_discovery
        self.host = host
        self.port = port
        self.app = FastAPI(
            title="Service Discovery API",
            description="REST API for service registration, discovery, and health monitoring",
            version="1.0.0")
        self.server = None

        # Setup routes
        self._setup_routes()

        logger.info(f"ServiceDiscoveryAPI initialized on {host}:{port}")

    def _setup_routes(self) -> None:
        """Setup API routes."""

        @self.app.get("/health", response_model=Dict[str, str])
        async def health_check():
            """API health check endpoint."""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat()}

        @self.app.post("/services/register", response_model=Dict[str, Any])
        async def register_service(request: ServiceInstanceRequest):
            """Register a new service instance."""
            try:
                instance = ServiceInstance(
                    service_id=request.service_id,
                    service_name=request.service_name,
                    host=request.host,
                    port=request.port,
                    metadata=request.metadata,
                    health_check_url=request.health_check_url,
                    tags=request.tags,
                    version=request.version
                )

                success = await self.service_discovery.register_service(instance)

                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to register service"
                    )

                return {
                    "message": "Service registered successfully",
                    "service_id": request.service_id,
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"Error registering service: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Registration failed: {str(e)}"
                )

        @self.app.delete("/services/{service_id}",
                         response_model=Dict[str, Any])
        async def deregister_service(service_id: str):
            """Deregister a service instance."""
            try:
                success = await self.service_discovery.deregister_service(service_id)

                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Service not found"
                    )

                return {
                    "message": "Service deregistered successfully",
                    "service_id": service_id,
                    "timestamp": datetime.now().isoformat()
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error deregistering service: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Deregistration failed: {str(e)}"
                )

        @self.app.get("/services/discover/{service_name}",
                      response_model=ServiceDiscoveryResponse)
        async def discover_services(
                service_name: str,
                healthy_only: bool = True):
            """Discover services by name."""
            try:
                instances = await self.service_discovery.discover_services(service_name, healthy_only)

                service_responses = []
                for instance in instances:
                    # Get registration info for status and timestamps
                    registration = self.service_discovery.services.get(
                        instance.service_id)
                    if registration:
                        service_responses.append(
                            ServiceInstanceResponse(
                                service_id=instance.service_id,
                                service_name=instance.service_name,
                                host=instance.host,
                                port=instance.port,
                                metadata=instance.metadata,
                                health_check_url=instance.health_check_url,
                                tags=instance.tags,
                                version=instance.version,
                                status=registration.status.value,
                                registered_at=registration.registered_at.isoformat(),
                                last_heartbeat=registration.last_heartbeat.isoformat()))

                return ServiceDiscoveryResponse(
                    services=service_responses,
                    total_count=len(service_responses)
                )

            except Exception as e:
                logger.error(f"Error discovering services: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Service discovery failed: {str(e)}"
                )

        @self.app.get("/services/{service_id}",
                      response_model=ServiceInstanceResponse)
        async def get_service(service_id: str):
            """Get service by ID."""
            try:
                instance = await self.service_discovery.get_service_by_id(service_id)

                if not instance:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Service not found"
                    )

                registration = self.service_discovery.services.get(service_id)

                return ServiceInstanceResponse(
                    service_id=instance.service_id,
                    service_name=instance.service_name,
                    host=instance.host,
                    port=instance.port,
                    metadata=instance.metadata,
                    health_check_url=instance.health_check_url,
                    tags=instance.tags,
                    version=instance.version,
                    status=registration.status.value if registration else "unknown",
                    registered_at=registration.registered_at.isoformat() if registration else "",
                    last_heartbeat=registration.last_heartbeat.isoformat() if registration else "")

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting service: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get service: {str(e)}"
                )

        @self.app.post("/services/{service_id}/heartbeat",
                       response_model=Dict[str, Any])
        async def service_heartbeat(service_id: str):
            """Send heartbeat for a service."""
            try:
                success = await self.service_discovery.heartbeat(service_id)

                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Service not found"
                    )

                return {
                    "message": "Heartbeat received",
                    "service_id": service_id,
                    "timestamp": datetime.now().isoformat()
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error processing heartbeat: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Heartbeat failed: {str(e)}"
                )

        @self.app.get("/services",
                      response_model=Dict[str,
                                          List[ServiceInstanceResponse]])
        async def list_all_services():
            """List all registered services."""
            try:
                services_by_name = await self.service_discovery.list_services()

                result = {}
                for service_name, service_list in services_by_name.items():
                    result[service_name] = [
                        ServiceInstanceResponse(
                            service_id=service_info["instance"]["service_id"],
                            service_name=service_info["instance"]["service_name"],
                            host=service_info["instance"]["host"],
                            port=service_info["instance"]["port"],
                            metadata=service_info["instance"]["metadata"],
                            health_check_url=service_info["instance"]["health_check_url"],
                            tags=service_info["instance"]["tags"],
                            version=service_info["instance"]["version"],
                            status=service_info["status"],
                            registered_at=service_info["registered_at"],
                            last_heartbeat=service_info["last_heartbeat"]
                        )
                        for service_info in service_list
                    ]

                return result

            except Exception as e:
                logger.error(f"Error listing services: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to list services: {str(e)}"
                )

        @self.app.get("/system/info", response_model=SystemInfoResponse)
        async def get_system_info():
            """Get system information and statistics."""
            try:
                info = await self.service_discovery.get_system_info()

                return SystemInfoResponse(
                    total_instances=info["total_instances"],
                    healthy_instances=info["healthy_instances"],
                    unique_services=info["unique_services"],
                    service_names=info["service_names"],
                    running=info["running"],
                    health_check_interval=info["health_check_interval"]
                )

            except Exception as e:
                logger.error(f"Error getting system info: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get system info: {str(e)}"
                )

        @self.app.get("/services/{service_id}/status",
                      response_model=Dict[str, Any])
        async def get_service_status(service_id: str):
            """Get service status."""
            try:
                status_result = await self.service_discovery.get_service_status(service_id)

                if status_result is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Service not found"
                    )

                return {
                    "service_id": service_id,
                    "status": status_result.value,
                    "timestamp": datetime.now().isoformat()
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting service status: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get service status: {str(e)}"
                )

        @self.app.get("/services/healthy/{service_name}",
                      response_model=ServiceInstanceResponse)
        async def get_healthy_instance(service_name: str):
            """Get a healthy instance of a service."""
            try:
                instance = await self.service_discovery.get_healthy_instance(service_name)

                if not instance:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="No healthy instances found"
                    )

                registration = self.service_discovery.services.get(
                    instance.service_id)

                return ServiceInstanceResponse(
                    service_id=instance.service_id,
                    service_name=instance.service_name,
                    host=instance.host,
                    port=instance.port,
                    metadata=instance.metadata,
                    health_check_url=instance.health_check_url,
                    tags=instance.tags,
                    version=instance.version,
                    status=registration.status.value if registration else "unknown",
                    registered_at=registration.registered_at.isoformat() if registration else "",
                    last_heartbeat=registration.last_heartbeat.isoformat() if registration else "")

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting healthy instance: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get healthy instance: {str(e)}"
                )

    async def start_server(self) -> None:
        """Start the API server."""
        try:
            logger.info(
                f"Starting Service Discovery API server on {
                    self.host}:{
                    self.port}")

            # Start the service discovery system if not already running
            if not self.service_discovery._running:
                await self.service_discovery.start()

            # Configure uvicorn server
            config = uvicorn.Config(
                app=self.app,
                host=self.host,
                port=self.port,
                log_level="info"
            )
            self.server = uvicorn.Server(config)

            # Start server (non-blocking)
            await self.server.serve()

        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            raise

    async def stop_server(self) -> None:
        """Stop the API server."""
        try:
            if self.server:
                logger.info("Stopping Service Discovery API server")
                self.server.should_exit = True
                await self.server.shutdown()
                self.server = None

            # Stop the service discovery system
            await self.service_discovery.stop()

        except Exception as e:
            logger.error(f"Error stopping API server: {e}")
            raise


# Convenience function for creating and running the API
async def create_service_discovery_api(
    config: Dict[str, Any] = None,
    api_host: str = "0.0.0.0",
    api_port: int = 8000
) -> ServiceDiscoveryAPI:
    """
    Create and initialize a Service Discovery API instance.

    Args:
        config: Service discovery configuration
        api_host: API server host
        api_port: API server port

    Returns:
        ServiceDiscoveryAPI instance
    """
    service_discovery = ServiceDiscovery(config or {})
    api = ServiceDiscoveryAPI(service_discovery, api_host, api_port)
    return api


if __name__ == "__main__":
    # Example of how to run the API standalone
    async def main():
        api = await create_service_discovery_api()
        await api.start_server()

    asyncio.run(main())
