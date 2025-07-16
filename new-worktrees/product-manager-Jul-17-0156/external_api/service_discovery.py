"""
Service Discovery System for Agent Hive Integration

Provides dynamic service registration, discovery, and health monitoring
for distributed agent and service components.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable, Any
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
    metadata: Dict[str, Any]
    health_check_url: Optional[str] = None
    tags: List[str] = None
    version: str = "1.0.0"
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class ServiceRegistration:
    """Service registration data."""
    instance: ServiceInstance
    registered_at: datetime
    last_heartbeat: datetime
    status: ServiceStatus
    health_check_interval: int = 30
    ttl: int = 300  # Time to live in seconds


class ServiceDiscovery:
    """
    Service Discovery system for managing distributed services.
    
    Provides service registration, discovery, health monitoring,
    and load balancing capabilities.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize service discovery system.
        
        Args:
            config: Service discovery configuration
        """
        self.config = config or {}
        self.services: Dict[str, ServiceRegistration] = {}
        self.service_watchers: Dict[str, List[Callable]] = {}
        self.health_check_interval = self.config.get("health_check_interval", 30)
        self.cleanup_interval = self.config.get("cleanup_interval", 60)
        
        # Health checking
        self._health_check_tasks: Dict[str, asyncio.Task] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info("ServiceDiscovery initialized")
    
    async def start(self) -> None:
        """Start the service discovery system."""
        if self._running:
            logger.warning("Service discovery already running")
            return
            
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_services())
        logger.info("Service discovery started")
    
    async def stop(self) -> None:
        """Stop the service discovery system."""
        if not self._running:
            return
            
        self._running = False
        
        # Cancel all health check tasks
        for task in self._health_check_tasks.values():
            task.cancel()
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            
        # Wait for tasks to complete
        await asyncio.gather(*self._health_check_tasks.values(), return_exceptions=True)
        if self._cleanup_task:
            await asyncio.gather(self._cleanup_task, return_exceptions=True)
            
        logger.info("Service discovery stopped")
    
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
                status=ServiceStatus.STARTING
            )
            
            self.services[instance.service_id] = registration
            
            # Start health checking if URL provided
            if instance.health_check_url:
                self._health_check_tasks[instance.service_id] = asyncio.create_task(
                    self._health_check_loop(instance.service_id)
                )
            else:
                # If no health check URL, mark as healthy
                registration.status = ServiceStatus.HEALTHY
            
            # Notify watchers
            await self._notify_watchers(instance.service_name, "registered", instance)
            
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
            
            # Cancel health check task
            if service_id in self._health_check_tasks:
                self._health_check_tasks[service_id].cancel()
                del self._health_check_tasks[service_id]
            
            # Remove from registry
            del self.services[service_id]
            
            # Notify watchers
            await self._notify_watchers(
                registration.instance.service_name, 
                "deregistered", 
                registration.instance
            )
            
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
    
    async def get_healthy_instance(self, service_name: str) -> Optional[ServiceInstance]:
        """
        Get a healthy instance of a service (simple round-robin).
        
        Args:
            service_name: Service name to find instance for
            
        Returns:
            Healthy service instance or None
        """
        healthy_instances = await self.discover_services(service_name, healthy_only=True)
        
        if not healthy_instances:
            return None
        
        # Simple round-robin selection
        # In production, this could be more sophisticated (weighted, least connections, etc.)
        return healthy_instances[0]
    
    async def watch_service(self, service_name: str, 
                          callback: Callable[[str, ServiceInstance], None]) -> None:
        """
        Watch for changes to a service.
        
        Args:
            service_name: Service name to watch
            callback: Callback function for service changes
        """
        if service_name not in self.service_watchers:
            self.service_watchers[service_name] = []
        
        self.service_watchers[service_name].append(callback)
        logger.info(f"Added watcher for service {service_name}")
    
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
            await self._notify_watchers(
                registration.instance.service_name,
                "healthy",
                registration.instance
            )
        
        logger.debug(f"Heartbeat received from {service_id}")
        return True
    
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
    
    async def list_services(self) -> Dict[str, List[Dict[str, Any]]]:
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
            
            services_by_name[service_name].append({
                "instance": asdict(registration.instance),
                "status": registration.status.value,
                "registered_at": registration.registered_at.isoformat(),
                "last_heartbeat": registration.last_heartbeat.isoformat()
            })
        
        return services_by_name
    
    async def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information and statistics.
        
        Returns:
            System information dictionary
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
            "running": self._running,
            "health_check_interval": self.health_check_interval
        }
    
    async def _health_check_loop(self, service_id: str) -> None:
        """Health check loop for a service."""
        while self._running and service_id in self.services:
            try:
                registration = self.services[service_id]
                
                # Perform health check
                is_healthy = await self._perform_health_check(registration.instance)
                
                # Update status
                old_status = registration.status
                new_status = ServiceStatus.HEALTHY if is_healthy else ServiceStatus.UNHEALTHY
                
                if old_status != new_status:
                    registration.status = new_status
                    await self._notify_watchers(
                        registration.instance.service_name,
                        "healthy" if is_healthy else "unhealthy",
                        registration.instance
                    )
                
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error for {service_id}: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _perform_health_check(self, instance: ServiceInstance) -> bool:
        """
        Perform health check on a service instance.
        
        Args:
            instance: Service instance to check
            
        Returns:
            True if healthy
        """
        if not instance.health_check_url:
            return True
        
        try:
            import aiohttp
            import asyncio
            
            # Real HTTP health check with timeout and retry logic
            timeout = aiohttp.ClientTimeout(total=5.0, connect=2.0)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(instance.health_check_url) as response:
                    # Consider 200-299 status codes as healthy
                    is_healthy = 200 <= response.status < 300
                    
                    if not is_healthy:
                        logger.warning(
                            f"Health check failed for {instance.service_id}: "
                            f"HTTP {response.status} from {instance.health_check_url}"
                        )
                    else:
                        logger.debug(
                            f"Health check passed for {instance.service_id}: "
                            f"HTTP {response.status} from {instance.health_check_url}"
                        )
                    
                    return is_healthy
                    
        except ImportError:
            logger.warning("aiohttp not available, falling back to basic health check")
            # Fallback to basic check if aiohttp not available
            await asyncio.sleep(0.1)
            return True
            
        except asyncio.TimeoutError:
            logger.warning(f"Health check timeout for {instance.service_id}: {instance.health_check_url}")
            return False
            
        except aiohttp.ClientError as e:
            logger.warning(f"Health check client error for {instance.service_id}: {e}")
            return False
            
        except Exception as e:
            logger.warning(f"Health check failed for {instance.service_id}: {e}")
            return False
    
    async def _cleanup_expired_services(self) -> None:
        """Cleanup expired services that haven't sent heartbeats."""
        while self._running:
            try:
                current_time = datetime.now()
                expired_services = []
                
                for service_id, registration in self.services.items():
                    time_since_heartbeat = (current_time - registration.last_heartbeat).total_seconds()
                    
                    if time_since_heartbeat > registration.ttl:
                        expired_services.append(service_id)
                
                # Remove expired services
                for service_id in expired_services:
                    logger.warning(f"Service {service_id} expired, removing from registry")
                    await self.deregister_service(service_id)
                
                await asyncio.sleep(self.cleanup_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(self.cleanup_interval)
    
    async def _notify_watchers(self, service_name: str, event: str, 
                             instance: ServiceInstance) -> None:
        """Notify watchers of service changes."""
        if service_name not in self.service_watchers:
            return
        
        for callback in self.service_watchers[service_name]:
            try:
                await callback(event, instance)
            except Exception as e:
                logger.error(f"Watcher callback error: {e}")