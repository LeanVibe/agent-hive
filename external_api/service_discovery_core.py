"""
Service Discovery Core - Basic service registration and discovery functionality.

This module provides the foundational service discovery capabilities:
- Service registration and deregistration
- Service instance lookup
- Basic service health status tracking
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service health status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"


@dataclass
class ServiceInstance:
    """Service instance information."""
    service_id: str
    service_name: str
    host: str
    port: int
    metadata: Dict[str, str] = None
    tags: List[str] = None
    version: str = "1.0.0"
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = []


@dataclass
class ServiceRegistration:
    """Service registration data."""
    instance: ServiceInstance
    registered_at: datetime
    last_heartbeat: datetime
    status: ServiceStatus
    
    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for serialization."""
        return {
            "instance": asdict(self.instance),
            "registered_at": self.registered_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "status": self.status.value
        }


class ServiceDiscoveryCore:
    """
    Core service discovery functionality.
    
    Provides basic service registration, discovery, and status tracking.
    """
    
    def __init__(self):
        """Initialize service discovery core."""
        self.services: Dict[str, ServiceRegistration] = {}
        self._running = False
        
        logger.info("ServiceDiscoveryCore initialized")
    
    async def start(self) -> None:
        """Start the service discovery system."""
        if self._running:
            logger.warning("Service discovery already running")
            return
            
        self._running = True
        logger.info("Service discovery core started")
    
    async def stop(self) -> None:
        """Stop the service discovery system."""
        if not self._running:
            return
            
        self._running = False
        logger.info("Service discovery core stopped")
    
    async def register_service(self, instance: ServiceInstance) -> bool:
        """
        Register a service instance.
        
        Args:
            instance: Service instance to register
            
        Returns:
            True if registration successful
        """
        try:
            registration = ServiceRegistration(
                instance=instance,
                registered_at=datetime.now(),
                last_heartbeat=datetime.now(),
                status=ServiceStatus.HEALTHY
            )
            
            self.services[instance.service_id] = registration
            
            logger.info(f"Registered service {instance.service_id} ({instance.service_name})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service {instance.service_id}: {e}")
            return False
    
    async def deregister_service(self, service_id: str) -> bool:
        """
        Deregister a service instance.
        
        Args:
            service_id: Service ID to deregister
            
        Returns:
            True if deregistration successful
        """
        try:
            if service_id not in self.services:
                logger.warning(f"Service {service_id} not found for deregistration")
                return False
            
            registration = self.services[service_id]
            registration.status = ServiceStatus.STOPPING
            
            # Remove from registry
            del self.services[service_id]
            
            logger.info(f"Deregistered service {service_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deregister service {service_id}: {e}")
            return False
    
    async def discover_services(self, service_name: str, 
                               healthy_only: bool = True) -> List[ServiceInstance]:
        """
        Discover services by name.
        
        Args:
            service_name: Name of service to discover
            healthy_only: Only return healthy instances
            
        Returns:
            List of matching service instances
        """
        instances = []
        
        for registration in self.services.values():
            if registration.instance.service_name == service_name:
                if healthy_only and registration.status != ServiceStatus.HEALTHY:
                    continue
                instances.append(registration.instance)
        
        logger.debug(f"Discovered {len(instances)} instances of {service_name}")
        return instances
    
    async def get_service_by_id(self, service_id: str) -> Optional[ServiceInstance]:
        """
        Get service instance by ID.
        
        Args:
            service_id: Service ID to lookup
            
        Returns:
            Service instance if found
        """
        registration = self.services.get(service_id)
        return registration.instance if registration else None
    
    async def get_service_status(self, service_id: str) -> Optional[ServiceStatus]:
        """
        Get current status of a service.
        
        Args:
            service_id: Service ID to check
            
        Returns:
            Service status or None if not found
        """
        registration = self.services.get(service_id)
        return registration.status if registration else None
    
    async def list_services(self) -> Dict[str, List[Dict[str, any]]]:
        """
        List all registered services grouped by service name.
        
        Returns:
            Dictionary mapping service names to instance lists
        """
        services_by_name = {}
        
        for registration in self.services.values():
            service_name = registration.instance.service_name
            if service_name not in services_by_name:
                services_by_name[service_name] = []
            
            services_by_name[service_name].append(registration.to_dict())
        
        return services_by_name
    
    async def heartbeat(self, service_id: str) -> bool:
        """
        Send heartbeat for a service.
        
        Args:
            service_id: Service ID sending heartbeat
            
        Returns:
            True if heartbeat accepted
        """
        if service_id not in self.services:
            logger.warning(f"Heartbeat from unknown service {service_id}")
            return False
        
        registration = self.services[service_id]
        registration.last_heartbeat = datetime.now()
        
        # Update status if it was unhealthy
        if registration.status == ServiceStatus.UNHEALTHY:
            registration.status = ServiceStatus.HEALTHY
        
        logger.debug(f"Heartbeat received from {service_id}")
        return True
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get service discovery statistics.
        
        Returns:
            Statistics dictionary
        """
        total_services = len(self.services)
        healthy_services = sum(
            1 for reg in self.services.values() 
            if reg.status == ServiceStatus.HEALTHY
        )
        
        service_names = set(
            reg.instance.service_name for reg in self.services.values()
        )
        
        return {
            "total_instances": total_services,
            "healthy_instances": healthy_services,
            "unique_services": len(service_names),
            "service_names": list(service_names),
            "running": self._running
        }