"""
Service Discovery System for API Gateway

Provides automatic service discovery, health checking, and dynamic
service registration for the agent-hive orchestration system.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set, Callable
from enum import Enum
from dataclasses import dataclass, asdict
import uuid
import hashlib

from ..advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
from ..advanced_orchestration.models import AgentStatus


logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service status states."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"


class DiscoveryStrategy(Enum):
    """Service discovery strategies."""
    STATIC = "static"
    DYNAMIC = "dynamic"
    HYBRID = "hybrid"
    CONSUL = "consul"
    ETCD = "etcd"


@dataclass
class ServiceInfo:
    """Service information."""
    service_id: str
    service_name: str
    service_type: str
    host: str
    port: int
    endpoints: List[str]
    metadata: Dict[str, Any]
    tags: List[str]
    status: ServiceStatus
    health_check_url: Optional[str] = None
    last_seen: Optional[datetime] = None
    registration_time: Optional[datetime] = None
    agent_id: Optional[str] = None
    version: str = "1.0.0"
    weight: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if self.last_seen:
            data["last_seen"] = self.last_seen.isoformat()
        if self.registration_time:
            data["registration_time"] = self.registration_time.isoformat()
        return data


@dataclass
class HealthCheckConfig:
    """Health check configuration."""
    enabled: bool = True
    interval: int = 30  # seconds
    timeout: int = 5    # seconds
    retries: int = 3
    failure_threshold: int = 3
    success_threshold: int = 1
    endpoint: str = "/health"
    method: str = "GET"
    expected_status: List[int] = None
    
    def __post_init__(self):
        if self.expected_status is None:
            self.expected_status = [200]


class ServiceDiscovery:
    """
    Service discovery system with automatic registration and health checking.
    
    Provides dynamic service discovery, health monitoring, and integration
    with the multi-agent coordination system.
    """
    
    def __init__(self, config: Dict[str, Any], coordinator: Optional[MultiAgentCoordinator] = None):
        """
        Initialize service discovery.
        
        Args:
            config: Service discovery configuration
            coordinator: Optional multi-agent coordinator
        """
        self.config = config
        self.coordinator = coordinator
        self.strategy = DiscoveryStrategy(config.get("strategy", "dynamic"))
        self.services: Dict[str, ServiceInfo] = {}
        self.service_groups: Dict[str, Set[str]] = {}  # {service_name: {service_ids}}
        self.health_checks: Dict[str, HealthCheckConfig] = {}
        self.discovery_listeners: List[Callable] = []
        
        # Health checking
        self.health_check_tasks: Dict[str, asyncio.Task] = {}
        self.health_check_results: Dict[str, List[bool]] = {}
        
        # Service registry cache
        self.registry_cache: Dict[str, Any] = {}
        self.cache_ttl = config.get("cache_ttl", 300)  # 5 minutes
        self.last_cache_update = 0
        
        # Auto-cleanup configuration
        self.cleanup_enabled = config.get("cleanup_enabled", True)
        self.cleanup_interval = config.get("cleanup_interval", 300)  # 5 minutes
        self.service_ttl = config.get("service_ttl", 600)  # 10 minutes
        
        # Running state
        self.running = False
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Stats
        self.stats = {
            "total_services": 0,
            "healthy_services": 0,
            "unhealthy_services": 0,
            "registrations": 0,
            "deregistrations": 0,
            "health_checks": 0,
            "failures": 0
        }
        
        logger.info(f"ServiceDiscovery initialized with strategy: {self.strategy}")
    
    async def start(self) -> None:
        """Start the service discovery system."""
        if self.running:
            logger.warning("Service discovery already running")
            return
        
        self.running = True
        logger.info("Starting service discovery")
        
        # Start cleanup task
        if self.cleanup_enabled:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # If coordinator is available, sync with it
        if self.coordinator:
            await self._sync_with_coordinator()
        
        logger.info("Service discovery started")
    
    async def stop(self) -> None:
        """Stop the service discovery system."""
        if not self.running:
            logger.warning("Service discovery not running")
            return
        
        self.running = False
        logger.info("Stopping service discovery")
        
        # Cancel cleanup task
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all health check tasks
        for task in self.health_check_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.health_check_tasks:
            await asyncio.gather(*self.health_check_tasks.values(), return_exceptions=True)
        
        logger.info("Service discovery stopped")
    
    async def register_service(self, service_info: ServiceInfo, 
                              health_check_config: Optional[HealthCheckConfig] = None) -> bool:
        """
        Register a service with the discovery system.
        
        Args:
            service_info: Service information
            health_check_config: Optional health check configuration
            
        Returns:
            True if registration successful
        """
        try:
            service_id = service_info.service_id
            service_name = service_info.service_name
            
            # Set registration time
            service_info.registration_time = datetime.now()
            service_info.last_seen = datetime.now()
            
            # Store service info
            self.services[service_id] = service_info
            
            # Add to service groups
            if service_name not in self.service_groups:
                self.service_groups[service_name] = set()
            self.service_groups[service_name].add(service_id)
            
            # Set up health checking
            if health_check_config:
                self.health_checks[service_id] = health_check_config
                if health_check_config.enabled:
                    await self._start_health_check(service_id)
            
            # Notify listeners
            await self._notify_listeners("service_registered", service_info)
            
            # Update stats
            self.stats["registrations"] += 1
            self.stats["total_services"] = len(self.services)
            
            logger.info(f"Registered service: {service_name} ({service_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service {service_info.service_id}: {e}")
            return False
    
    async def deregister_service(self, service_id: str) -> bool:
        """
        Deregister a service from the discovery system.
        
        Args:
            service_id: Service ID to deregister
            
        Returns:
            True if deregistration successful
        """
        try:
            if service_id not in self.services:
                logger.warning(f"Service {service_id} not found for deregistration")
                return False
            
            service_info = self.services[service_id]
            service_name = service_info.service_name
            
            # Stop health checking
            await self._stop_health_check(service_id)
            
            # Remove from service groups
            if service_name in self.service_groups:
                self.service_groups[service_name].discard(service_id)
                if not self.service_groups[service_name]:
                    del self.service_groups[service_name]
            
            # Remove service
            del self.services[service_id]
            self.health_checks.pop(service_id, None)
            self.health_check_results.pop(service_id, None)
            
            # Notify listeners
            await self._notify_listeners("service_deregistered", service_info)
            
            # Update stats
            self.stats["deregistrations"] += 1
            self.stats["total_services"] = len(self.services)
            
            logger.info(f"Deregistered service: {service_name} ({service_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deregister service {service_id}: {e}")
            return False
    
    async def discover_services(self, service_name: Optional[str] = None,
                              service_type: Optional[str] = None,
                              tags: Optional[List[str]] = None,
                              status: Optional[ServiceStatus] = None) -> List[ServiceInfo]:
        """
        Discover services based on criteria.
        
        Args:
            service_name: Filter by service name
            service_type: Filter by service type
            tags: Filter by tags
            status: Filter by status
            
        Returns:
            List of matching services
        """
        matching_services = []
        
        for service_info in self.services.values():
            # Filter by service name
            if service_name and service_info.service_name != service_name:
                continue
            
            # Filter by service type
            if service_type and service_info.service_type != service_type:
                continue
            
            # Filter by tags
            if tags and not set(tags).issubset(set(service_info.tags)):
                continue
            
            # Filter by status
            if status and service_info.status != status:
                continue
            
            matching_services.append(service_info)
        
        # Sort by weight (descending) and then by service_id for consistency
        matching_services.sort(key=lambda s: (-s.weight, s.service_id))
        
        return matching_services
    
    async def get_service_health(self, service_id: str) -> Dict[str, Any]:
        """
        Get health status for a service.
        
        Args:
            service_id: Service ID
            
        Returns:
            Health status information
        """
        if service_id not in self.services:
            return {"error": "Service not found"}
        
        service_info = self.services[service_id]
        health_history = self.health_check_results.get(service_id, [])
        
        return {
            "service_id": service_id,
            "service_name": service_info.service_name,
            "status": service_info.status.value,
            "last_seen": service_info.last_seen.isoformat() if service_info.last_seen else None,
            "health_check_enabled": service_id in self.health_checks,
            "health_history": health_history[-10:],  # Last 10 checks
            "success_rate": sum(health_history) / len(health_history) if health_history else 0,
            "consecutive_failures": self._get_consecutive_failures(service_id)
        }
    
    async def update_service_status(self, service_id: str, status: ServiceStatus) -> bool:
        """
        Update service status.
        
        Args:
            service_id: Service ID
            status: New status
            
        Returns:
            True if update successful
        """
        if service_id not in self.services:
            return False
        
        old_status = self.services[service_id].status
        self.services[service_id].status = status
        self.services[service_id].last_seen = datetime.now()
        
        # Update stats
        if old_status != status:
            await self._notify_listeners("service_status_changed", self.services[service_id])
        
        return True
    
    async def add_discovery_listener(self, listener: Callable) -> None:
        """
        Add a discovery event listener.
        
        Args:
            listener: Async function to call on discovery events
        """
        if asyncio.iscoroutinefunction(listener):
            self.discovery_listeners.append(listener)
        else:
            raise ValueError("Listener must be an async function")
    
    async def _start_health_check(self, service_id: str) -> None:
        """Start health checking for a service."""
        if service_id in self.health_check_tasks:
            return
        
        health_config = self.health_checks[service_id]
        if not health_config.enabled:
            return
        
        self.health_check_tasks[service_id] = asyncio.create_task(
            self._health_check_loop(service_id, health_config)
        )
    
    async def _stop_health_check(self, service_id: str) -> None:
        """Stop health checking for a service."""
        if service_id in self.health_check_tasks:
            task = self.health_check_tasks[service_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.health_check_tasks[service_id]
    
    async def _health_check_loop(self, service_id: str, health_config: HealthCheckConfig) -> None:
        """Health check loop for a service."""
        while self.running:
            try:
                # Perform health check
                is_healthy = await self._perform_health_check(service_id, health_config)
                
                # Store result
                if service_id not in self.health_check_results:
                    self.health_check_results[service_id] = []
                
                self.health_check_results[service_id].append(is_healthy)
                
                # Keep only recent results
                if len(self.health_check_results[service_id]) > 100:
                    self.health_check_results[service_id].pop(0)
                
                # Update service status based on health check
                await self._update_service_status_from_health(service_id, is_healthy, health_config)
                
                # Update stats
                self.stats["health_checks"] += 1
                if not is_healthy:
                    self.stats["failures"] += 1
                
                # Wait for next check
                await asyncio.sleep(health_config.interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error for service {service_id}: {e}")
                await asyncio.sleep(health_config.interval)
    
    async def _perform_health_check(self, service_id: str, health_config: HealthCheckConfig) -> bool:
        """
        Perform actual health check.
        
        Args:
            service_id: Service ID
            health_config: Health check configuration
            
        Returns:
            True if healthy
        """
        if service_id not in self.services:
            return False
        
        service_info = self.services[service_id]
        
        # If coordinator is available, check agent health
        if self.coordinator and service_info.agent_id:
            agent_info = await self.coordinator.get_agent_status(service_info.agent_id)
            if agent_info:
                return agent_info.status == AgentStatus.HEALTHY
        
        # Otherwise perform HTTP health check
        try:
            # This is a simplified health check - in production, use proper HTTP client
            # For now, just check if service info is valid
            return (service_info.host and 
                   service_info.port and 
                   service_info.status != ServiceStatus.UNHEALTHY)
        except Exception:
            return False
    
    async def _update_service_status_from_health(self, service_id: str, is_healthy: bool, 
                                               health_config: HealthCheckConfig) -> None:
        """Update service status based on health check result."""
        if service_id not in self.services:
            return
        
        consecutive_failures = self._get_consecutive_failures(service_id)
        consecutive_successes = self._get_consecutive_successes(service_id)
        
        current_status = self.services[service_id].status
        
        # Determine new status
        if is_healthy:
            if current_status == ServiceStatus.UNHEALTHY and consecutive_successes >= health_config.success_threshold:
                await self.update_service_status(service_id, ServiceStatus.HEALTHY)
            elif current_status == ServiceStatus.UNKNOWN:
                await self.update_service_status(service_id, ServiceStatus.HEALTHY)
        else:
            if current_status == ServiceStatus.HEALTHY and consecutive_failures >= health_config.failure_threshold:
                await self.update_service_status(service_id, ServiceStatus.UNHEALTHY)
    
    def _get_consecutive_failures(self, service_id: str) -> int:
        """Get count of consecutive failures."""
        if service_id not in self.health_check_results:
            return 0
        
        results = self.health_check_results[service_id]
        count = 0
        for result in reversed(results):
            if not result:
                count += 1
            else:
                break
        return count
    
    def _get_consecutive_successes(self, service_id: str) -> int:
        """Get count of consecutive successes."""
        if service_id not in self.health_check_results:
            return 0
        
        results = self.health_check_results[service_id]
        count = 0
        for result in reversed(results):
            if result:
                count += 1
            else:
                break
        return count
    
    async def _cleanup_loop(self) -> None:
        """Cleanup loop for stale services."""
        while self.running:
            try:
                await self._cleanup_stale_services()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(self.cleanup_interval)
    
    async def _cleanup_stale_services(self) -> None:
        """Clean up stale services."""
        now = datetime.now()
        stale_threshold = now - timedelta(seconds=self.service_ttl)
        
        stale_services = []
        for service_id, service_info in self.services.items():
            if service_info.last_seen and service_info.last_seen < stale_threshold:
                stale_services.append(service_id)
        
        for service_id in stale_services:
            logger.info(f"Cleaning up stale service: {service_id}")
            await self.deregister_service(service_id)
    
    async def _sync_with_coordinator(self) -> None:
        """Sync services with multi-agent coordinator."""
        if not self.coordinator:
            return
        
        try:
            # Get coordinator state
            coordinator_state = await self.coordinator.get_coordinator_state()
            
            # Register agents as services
            for agent_id, agent_info in coordinator_state.active_agents.items():
                service_info = ServiceInfo(
                    service_id=f"agent-{agent_id}",
                    service_name=f"agent-{agent_info.registration.agent_type}",
                    service_type="agent",
                    host=agent_info.registration.endpoint.get("host", "localhost"),
                    port=agent_info.registration.endpoint.get("port", 8080),
                    endpoints=agent_info.registration.capabilities,
                    metadata={"agent_id": agent_id, "agent_type": agent_info.registration.agent_type},
                    tags=["agent", agent_info.registration.agent_type],
                    status=ServiceStatus.HEALTHY if agent_info.status == AgentStatus.HEALTHY else ServiceStatus.UNHEALTHY,
                    agent_id=agent_id
                )
                
                await self.register_service(service_info, HealthCheckConfig(enabled=True))
            
            logger.info(f"Synced {len(coordinator_state.active_agents)} agents as services")
            
        except Exception as e:
            logger.error(f"Failed to sync with coordinator: {e}")
    
    async def _notify_listeners(self, event_type: str, service_info: ServiceInfo) -> None:
        """Notify discovery listeners of events."""
        for listener in self.discovery_listeners:
            try:
                await listener(event_type, service_info)
            except Exception as e:
                logger.error(f"Error notifying listener: {e}")
    
    # Management and monitoring methods
    
    def get_service_by_id(self, service_id: str) -> Optional[ServiceInfo]:
        """Get service by ID."""
        return self.services.get(service_id)
    
    def get_services_by_name(self, service_name: str) -> List[ServiceInfo]:
        """Get all services with a specific name."""
        if service_name not in self.service_groups:
            return []
        
        return [self.services[service_id] for service_id in self.service_groups[service_name]]
    
    def get_service_names(self) -> List[str]:
        """Get all service names."""
        return list(self.service_groups.keys())
    
    def get_discovery_stats(self) -> Dict[str, Any]:
        """Get discovery statistics."""
        # Update current stats
        healthy_count = sum(1 for s in self.services.values() if s.status == ServiceStatus.HEALTHY)
        unhealthy_count = sum(1 for s in self.services.values() if s.status == ServiceStatus.UNHEALTHY)
        
        self.stats["healthy_services"] = healthy_count
        self.stats["unhealthy_services"] = unhealthy_count
        
        return {
            "strategy": self.strategy.value,
            "running": self.running,
            "total_services": len(self.services),
            "service_groups": len(self.service_groups),
            "active_health_checks": len(self.health_check_tasks),
            "discovery_listeners": len(self.discovery_listeners),
            "coordinator_connected": self.coordinator is not None,
            "stats": self.stats.copy()
        }
    
    def export_service_registry(self) -> Dict[str, Any]:
        """Export service registry for backup or migration."""
        return {
            "timestamp": datetime.now().isoformat(),
            "strategy": self.strategy.value,
            "services": {
                service_id: service_info.to_dict()
                for service_id, service_info in self.services.items()
            },
            "service_groups": {
                name: list(service_ids)
                for name, service_ids in self.service_groups.items()
            },
            "health_checks": {
                service_id: asdict(config)
                for service_id, config in self.health_checks.items()
            }
        }
    
    async def import_service_registry(self, registry_data: Dict[str, Any]) -> bool:
        """Import service registry from backup."""
        try:
            # Clear existing services
            await self.stop()
            self.services.clear()
            self.service_groups.clear()
            self.health_checks.clear()
            
            # Import services
            for service_id, service_data in registry_data.get("services", {}).items():
                service_info = ServiceInfo(
                    service_id=service_data["service_id"],
                    service_name=service_data["service_name"],
                    service_type=service_data["service_type"],
                    host=service_data["host"],
                    port=service_data["port"],
                    endpoints=service_data["endpoints"],
                    metadata=service_data["metadata"],
                    tags=service_data["tags"],
                    status=ServiceStatus(service_data["status"]),
                    health_check_url=service_data.get("health_check_url"),
                    agent_id=service_data.get("agent_id"),
                    version=service_data.get("version", "1.0.0"),
                    weight=service_data.get("weight", 1)
                )
                
                # Parse datetime fields
                if service_data.get("last_seen"):
                    service_info.last_seen = datetime.fromisoformat(service_data["last_seen"])
                if service_data.get("registration_time"):
                    service_info.registration_time = datetime.fromisoformat(service_data["registration_time"])
                
                # Import health check config
                health_config = None
                if service_id in registry_data.get("health_checks", {}):
                    health_data = registry_data["health_checks"][service_id]
                    health_config = HealthCheckConfig(**health_data)
                
                await self.register_service(service_info, health_config)
            
            # Restart discovery
            await self.start()
            
            logger.info(f"Imported {len(self.services)} services from registry")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import service registry: {e}")
            return False