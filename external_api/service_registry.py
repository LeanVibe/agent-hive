"""
Enhanced Service Registry with Persistent Storage

Provides persistent service registration with database storage, advanced health
monitoring, and event-driven service lifecycle management.
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import json
import pickle

from .service_discovery import ServiceInstance, ServiceStatus, ServiceRegistration
from .circuit_breaker import CircuitBreakerManager, CircuitBreakerConfig


logger = logging.getLogger(__name__)


class ServiceLifecycleEvent(Enum):
    """Service lifecycle events."""
    REGISTERED = "registered"
    DEREGISTERED = "deregistered"
    HEALTH_CHANGED = "health_changed"
    UPDATED = "updated"
    EXPIRED = "expired"


@dataclass
class ServiceEvent:
    """Service event information."""
    event_id: str
    event_type: ServiceLifecycleEvent
    service_id: str
    service_name: str
    timestamp: datetime
    details: Dict[str, Any]
    source: str = "service_registry"


@dataclass
class ServiceRegistryConfig:
    """Service registry configuration."""
    database_path: str = "service_registry.db"
    backup_interval: int = 300  # 5 minutes
    cleanup_interval: int = 60   # 1 minute
    event_retention_hours: int = 24
    enable_persistence: bool = True
    enable_circuit_breakers: bool = True
    health_check_interval: int = 30
    service_ttl: int = 300  # 5 minutes default TTL


class PersistentServiceRegistry:
    """
    Enhanced service registry with persistent storage and advanced features.
    
    Features:
    - SQLite database persistence
    - Event-driven architecture
    - Automatic backup and recovery
    - Circuit breaker integration
    - Advanced health monitoring
    - Service dependency tracking
    - Configuration management
    """
    
    def __init__(self, config: Optional[ServiceRegistryConfig] = None):
        """Initialize persistent service registry."""
        self.config = config or ServiceRegistryConfig()
        
        # Core data structures
        self.services: Dict[str, ServiceRegistration] = {}
        self.service_events: List[ServiceEvent] = []
        self.service_watchers: Dict[str, List[Callable]] = {}
        self.service_dependencies: Dict[str, Set[str]] = {}
        
        # Database connection
        self.db_path = self.config.database_path
        self.db_connection: Optional[sqlite3.Connection] = None
        
        # Circuit breaker management
        if self.config.enable_circuit_breakers:
            cb_config = CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=60,
                success_threshold=2
            )
            self.circuit_breaker_manager = CircuitBreakerManager(cb_config)
        else:
            self.circuit_breaker_manager = None
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._backup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Metrics
        self.metrics = {
            "total_registrations": 0,
            "total_deregistrations": 0,
            "total_health_checks": 0,
            "total_events": 0,
            "backup_count": 0,
            "cleanup_count": 0
        }
        
        logger.info("PersistentServiceRegistry initialized")
    
    async def start(self) -> None:
        """Start the service registry."""
        if self._running:
            return
        
        # Initialize database
        if self.config.enable_persistence:
            await self._initialize_database()
            await self._load_from_database()
        
        # Start background tasks
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        if self.config.enable_persistence:
            self._backup_task = asyncio.create_task(self._backup_loop())
        
        logger.info("Service registry started")
    
    async def stop(self) -> None:
        """Stop the service registry."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._backup_task:
            self._backup_task.cancel()
        
        # Wait for tasks to complete
        tasks = [task for task in [self._cleanup_task, self._backup_task] if task]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Final backup
        if self.config.enable_persistence:
            await self._backup_to_database()
        
        # Close database connection
        if self.db_connection:
            self.db_connection.close()
        
        logger.info("Service registry stopped")
    
    async def register_service(self, service_instance: ServiceInstance,
                             dependencies: Optional[List[str]] = None,
                             metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Register a service with enhanced features."""
        try:
            # Create registration
            enhanced_metadata = service_instance.metadata.copy()
            if metadata:
                enhanced_metadata.update(metadata)
            
            # Update service instance with enhanced metadata
            enhanced_instance = ServiceInstance(
                service_id=service_instance.service_id,
                service_name=service_instance.service_name,
                host=service_instance.host,
                port=service_instance.port,
                metadata=enhanced_metadata,
                health_check_url=service_instance.health_check_url,
                tags=service_instance.tags,
                version=service_instance.version
            )
            
            registration = ServiceRegistration(
                instance=enhanced_instance,
                registered_at=datetime.utcnow(),
                last_heartbeat=datetime.utcnow(),
                status=ServiceStatus.STARTING,
                ttl=self.config.service_ttl
            )
            
            # Store registration
            self.services[service_instance.service_id] = registration
            
            # Track dependencies
            if dependencies:
                self.service_dependencies[service_instance.service_id] = set(dependencies)
            
            # Create circuit breaker if enabled
            if self.circuit_breaker_manager:
                await self.circuit_breaker_manager.get_or_create(
                    f"service_{service_instance.service_id}"
                )
            
            # Emit event
            await self._emit_event(
                ServiceLifecycleEvent.REGISTERED,
                service_instance.service_id,
                service_instance.service_name,
                {
                    "host": service_instance.host,
                    "port": service_instance.port,
                    "dependencies": dependencies or [],
                    "metadata": enhanced_metadata
                }
            )
            
            # Notify watchers
            await self._notify_watchers(
                service_instance.service_name,
                "registered",
                enhanced_instance
            )
            
            # Persist to database
            if self.config.enable_persistence:
                await self._save_service_to_db(registration)
            
            self.metrics["total_registrations"] += 1
            
            logger.info(f"Registered service {service_instance.service_id} "
                       f"({service_instance.service_name}) with {len(dependencies or [])} dependencies")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service {service_instance.service_id}: {e}")
            return False
    
    async def deregister_service(self, service_id: str, reason: str = "Manual deregistration") -> bool:
        """Deregister a service."""
        try:
            if service_id not in self.services:
                logger.warning(f"Service {service_id} not found for deregistration")
                return False
            
            registration = self.services[service_id]
            service_instance = registration.instance
            
            # Update status
            registration.status = ServiceStatus.STOPPING
            
            # Remove from memory
            del self.services[service_id]
            
            # Clean up dependencies
            self.service_dependencies.pop(service_id, None)
            
            # Remove circuit breaker
            if self.circuit_breaker_manager:
                await self.circuit_breaker_manager.remove(f"service_{service_id}")
            
            # Emit event
            await self._emit_event(
                ServiceLifecycleEvent.DEREGISTERED,
                service_id,
                service_instance.service_name,
                {"reason": reason}
            )
            
            # Notify watchers
            await self._notify_watchers(
                service_instance.service_name,
                "deregistered",
                service_instance
            )
            
            # Remove from database
            if self.config.enable_persistence:
                await self._remove_service_from_db(service_id)
            
            self.metrics["total_deregistrations"] += 1
            
            logger.info(f"Deregistered service {service_id}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deregister service {service_id}: {e}")
            return False
    
    async def update_service(self, service_id: str, updates: Dict[str, Any]) -> bool:
        """Update service information."""
        try:
            if service_id not in self.services:
                return False
            
            registration = self.services[service_id]
            old_metadata = registration.instance.metadata.copy()
            
            # Apply updates
            if "metadata" in updates:
                registration.instance.metadata.update(updates["metadata"])
            
            if "tags" in updates:
                registration.instance.tags = updates["tags"]
            
            if "health_check_url" in updates:
                registration.instance.health_check_url = updates["health_check_url"]
            
            # Emit event
            await self._emit_event(
                ServiceLifecycleEvent.UPDATED,
                service_id,
                registration.instance.service_name,
                {
                    "updates": updates,
                    "old_metadata": old_metadata,
                    "new_metadata": registration.instance.metadata
                }
            )
            
            # Persist changes
            if self.config.enable_persistence:
                await self._save_service_to_db(registration)
            
            logger.info(f"Updated service {service_id} with {len(updates)} changes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update service {service_id}: {e}")
            return False
    
    async def discover_services(self, service_name: str, 
                              include_unhealthy: bool = False,
                              tags: Optional[List[str]] = None) -> List[ServiceInstance]:
        """Discover services with advanced filtering."""
        try:
            instances = []
            
            for registration in self.services.values():
                instance = registration.instance
                
                # Match service name
                if instance.service_name != service_name:
                    continue
                
                # Health filter
                if not include_unhealthy and registration.status not in [
                    ServiceStatus.HEALTHY, ServiceStatus.STARTING
                ]:
                    continue
                
                # Tag filter
                if tags:
                    if not all(tag in instance.tags for tag in tags):
                        continue
                
                instances.append(instance)
            
            logger.debug(f"Discovered {len(instances)} instances of {service_name}")
            return instances
            
        except Exception as e:
            logger.error(f"Error discovering services for {service_name}: {e}")
            return []
    
    async def get_service_health(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive service health information."""
        try:
            if service_id not in self.services:
                return None
            
            registration = self.services[service_id]
            instance = registration.instance
            
            # Get circuit breaker status
            circuit_breaker_status = None
            if self.circuit_breaker_manager:
                cb_name = f"service_{service_id}"
                if cb_name in self.circuit_breaker_manager.circuit_breakers:
                    cb = self.circuit_breaker_manager.circuit_breakers[cb_name]
                    circuit_breaker_status = await cb.get_status()
            
            # Calculate uptime
            uptime_seconds = (datetime.utcnow() - registration.registered_at).total_seconds()
            
            # Check dependencies
            dependency_health = {}
            if service_id in self.service_dependencies:
                for dep_service_id in self.service_dependencies[service_id]:
                    if dep_service_id in self.services:
                        dep_registration = self.services[dep_service_id]
                        dependency_health[dep_service_id] = {
                            "status": dep_registration.status.value,
                            "healthy": dep_registration.status == ServiceStatus.HEALTHY
                        }
                    else:
                        dependency_health[dep_service_id] = {
                            "status": "not_found",
                            "healthy": False
                        }
            
            return {
                "service_id": service_id,
                "service_name": instance.service_name,
                "status": registration.status.value,
                "host": instance.host,
                "port": instance.port,
                "health_check_url": instance.health_check_url,
                "uptime_seconds": uptime_seconds,
                "registered_at": registration.registered_at.isoformat(),
                "last_heartbeat": registration.last_heartbeat.isoformat(),
                "ttl_seconds": registration.ttl,
                "circuit_breaker": circuit_breaker_status,
                "dependencies": dependency_health,
                "metadata": instance.metadata,
                "tags": instance.tags
            }
            
        except Exception as e:
            logger.error(f"Error getting health for service {service_id}: {e}")
            return None
    
    async def get_service_events(self, service_id: Optional[str] = None,
                               event_type: Optional[ServiceLifecycleEvent] = None,
                               limit: int = 100) -> List[ServiceEvent]:
        """Get service events with filtering."""
        try:
            events = self.service_events
            
            # Filter by service ID
            if service_id:
                events = [e for e in events if e.service_id == service_id]
            
            # Filter by event type
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            
            # Sort by timestamp (newest first) and limit
            events = sorted(events, key=lambda x: x.timestamp, reverse=True)[:limit]
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting service events: {e}")
            return []
    
    async def get_registry_stats(self) -> Dict[str, Any]:
        """Get comprehensive registry statistics."""
        try:
            total_services = len(self.services)
            healthy_services = sum(
                1 for reg in self.services.values()
                if reg.status == ServiceStatus.HEALTHY
            )
            
            # Service name distribution
            service_names = {}
            for registration in self.services.values():
                name = registration.instance.service_name
                service_names[name] = service_names.get(name, 0) + 1
            
            # Circuit breaker stats
            circuit_breaker_stats = None
            if self.circuit_breaker_manager:
                circuit_breaker_stats = await self.circuit_breaker_manager.get_summary_stats()
            
            # Event statistics
            event_types = {}
            for event in self.service_events[-1000:]:  # Last 1000 events
                event_types[event.event_type.value] = event_types.get(event.event_type.value, 0) + 1
            
            return {
                "total_services": total_services,
                "healthy_services": healthy_services,
                "unhealthy_services": total_services - healthy_services,
                "unique_service_names": len(service_names),
                "service_distribution": service_names,
                "total_dependencies": sum(len(deps) for deps in self.service_dependencies.values()),
                "metrics": self.metrics,
                "circuit_breakers": circuit_breaker_stats,
                "recent_events": event_types,
                "configuration": {
                    "database_path": self.config.database_path,
                    "persistence_enabled": self.config.enable_persistence,
                    "circuit_breakers_enabled": self.config.enable_circuit_breakers,
                    "service_ttl": self.config.service_ttl,
                    "cleanup_interval": self.config.cleanup_interval
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting registry stats: {e}")
            return {"error": str(e)}
    
    async def backup_registry(self, backup_path: Optional[str] = None) -> bool:
        """Create manual backup of registry."""
        try:
            if not backup_path:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                backup_path = f"service_registry_backup_{timestamp}.json"
            
            backup_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "services": {},
                "dependencies": {},
                "events": [],
                "metrics": self.metrics
            }
            
            # Serialize services
            for service_id, registration in self.services.items():
                backup_data["services"][service_id] = {
                    "instance": asdict(registration.instance),
                    "registered_at": registration.registered_at.isoformat(),
                    "last_heartbeat": registration.last_heartbeat.isoformat(),
                    "status": registration.status.value,
                    "ttl": registration.ttl
                }
            
            # Serialize dependencies
            for service_id, deps in self.service_dependencies.items():
                backup_data["dependencies"][service_id] = list(deps)
            
            # Serialize recent events
            for event in self.service_events[-1000:]:  # Last 1000 events
                backup_data["events"].append({
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "service_id": event.service_id,
                    "service_name": event.service_name,
                    "timestamp": event.timestamp.isoformat(),
                    "details": event.details,
                    "source": event.source
                })
            
            # Write backup
            with open(backup_path, 'w') as f:
                f.write(json.dumps(backup_data, indent=2))
            
            self.metrics["backup_count"] += 1
            logger.info(f"Registry backup created: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create registry backup: {e}")
            return False
    
    # Private methods
    
    async def _initialize_database(self) -> None:
        """Initialize SQLite database."""
        try:
            self.db_connection = sqlite3.connect(self.db_path)
            cursor = self.db_connection.cursor()
            
            # Create services table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    service_id TEXT PRIMARY KEY,
                    service_name TEXT NOT NULL,
                    host TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    metadata TEXT,
                    health_check_url TEXT,
                    tags TEXT,
                    version TEXT,
                    registered_at TEXT,
                    last_heartbeat TEXT,
                    status TEXT,
                    ttl INTEGER
                )
            """)
            
            # Create events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS service_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT,
                    source TEXT
                )
            """)
            
            # Create dependencies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS service_dependencies (
                    service_id TEXT,
                    dependency_id TEXT,
                    PRIMARY KEY (service_id, dependency_id)
                )
            """)
            
            self.db_connection.commit()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _load_from_database(self) -> None:
        """Load services from database."""
        try:
            if not self.db_connection:
                return
            
            cursor = self.db_connection.cursor()
            
            # Load services
            cursor.execute("SELECT * FROM services")
            rows = cursor.fetchall()
            
            for row in rows:
                (service_id, service_name, host, port, metadata_json, health_check_url,
                 tags_json, version, registered_at_str, last_heartbeat_str, status_str, ttl) = row
                
                # Parse JSON fields
                metadata = json.loads(metadata_json) if metadata_json else {}
                tags = json.loads(tags_json) if tags_json else []
                
                # Create service instance
                instance = ServiceInstance(
                    service_id=service_id,
                    service_name=service_name,
                    host=host,
                    port=port,
                    metadata=metadata,
                    health_check_url=health_check_url,
                    tags=tags,
                    version=version
                )
                
                # Create registration
                registration = ServiceRegistration(
                    instance=instance,
                    registered_at=datetime.fromisoformat(registered_at_str),
                    last_heartbeat=datetime.fromisoformat(last_heartbeat_str),
                    status=ServiceStatus(status_str),
                    ttl=ttl
                )
                
                self.services[service_id] = registration
            
            # Load dependencies
            cursor.execute("SELECT * FROM service_dependencies")
            dep_rows = cursor.fetchall()
            
            for service_id, dependency_id in dep_rows:
                if service_id not in self.service_dependencies:
                    self.service_dependencies[service_id] = set()
                self.service_dependencies[service_id].add(dependency_id)
            
            logger.info(f"Loaded {len(self.services)} services from database")
            
        except Exception as e:
            logger.error(f"Failed to load from database: {e}")
    
    async def _save_service_to_db(self, registration: ServiceRegistration) -> None:
        """Save service registration to database."""
        try:
            if not self.db_connection:
                return
            
            cursor = self.db_connection.cursor()
            instance = registration.instance
            
            cursor.execute("""
                INSERT OR REPLACE INTO services 
                (service_id, service_name, host, port, metadata, health_check_url, 
                 tags, version, registered_at, last_heartbeat, status, ttl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                instance.service_id,
                instance.service_name,
                instance.host,
                instance.port,
                json.dumps(instance.metadata),
                instance.health_check_url,
                json.dumps(instance.tags),
                instance.version,
                registration.registered_at.isoformat(),
                registration.last_heartbeat.isoformat(),
                registration.status.value,
                registration.ttl
            ))
            
            self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"Failed to save service to database: {e}")
    
    async def _remove_service_from_db(self, service_id: str) -> None:
        """Remove service from database."""
        try:
            if not self.db_connection:
                return
            
            cursor = self.db_connection.cursor()
            cursor.execute("DELETE FROM services WHERE service_id = ?", (service_id,))
            cursor.execute("DELETE FROM service_dependencies WHERE service_id = ? OR dependency_id = ?", 
                         (service_id, service_id))
            self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"Failed to remove service from database: {e}")
    
    async def _backup_to_database(self) -> None:
        """Backup current state to database."""
        if not self.config.enable_persistence or not self.db_connection:
            return
        
        try:
            # This would typically sync in-memory state to database
            # For now, individual operations handle persistence
            logger.debug("Database backup completed")
            
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
    
    async def _emit_event(self, event_type: ServiceLifecycleEvent, service_id: str,
                         service_name: str, details: Dict[str, Any]) -> None:
        """Emit service lifecycle event."""
        try:
            event = ServiceEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                service_id=service_id,
                service_name=service_name,
                timestamp=datetime.utcnow(),
                details=details
            )
            
            self.service_events.append(event)
            self.metrics["total_events"] += 1
            
            # Keep only recent events to prevent memory issues
            if len(self.service_events) > 10000:
                self.service_events = self.service_events[-5000:]
            
            # Save event to database
            if self.config.enable_persistence and self.db_connection:
                cursor = self.db_connection.cursor()
                cursor.execute("""
                    INSERT INTO service_events 
                    (event_id, event_type, service_id, service_name, timestamp, details, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    event.event_type.value,
                    event.service_id,
                    event.service_name,
                    event.timestamp.isoformat(),
                    json.dumps(event.details),
                    event.source
                ))
                self.db_connection.commit()
            
            logger.debug(f"Emitted event: {event_type.value} for service {service_id}")
            
        except Exception as e:
            logger.error(f"Failed to emit event: {e}")
    
    async def _notify_watchers(self, service_name: str, event: str, instance: ServiceInstance) -> None:
        """Notify service watchers."""
        if service_name not in self.service_watchers:
            return
        
        for callback in self.service_watchers[service_name]:
            try:
                await callback(event, instance)
            except Exception as e:
                logger.error(f"Watcher callback error: {e}")
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup of expired services and events."""
        while self._running:
            try:
                await self._cleanup_expired_services()
                await self._cleanup_old_events()
                self.metrics["cleanup_count"] += 1
                await asyncio.sleep(self.config.cleanup_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(self.config.cleanup_interval)
    
    async def _backup_loop(self) -> None:
        """Background backup loop."""
        while self._running:
            try:
                await self._backup_to_database()
                await asyncio.sleep(self.config.backup_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Backup loop error: {e}")
                await asyncio.sleep(self.config.backup_interval)
    
    async def _cleanup_expired_services(self) -> None:
        """Clean up expired services."""
        try:
            current_time = datetime.utcnow()
            expired_services = []
            
            for service_id, registration in self.services.items():
                time_since_heartbeat = (current_time - registration.last_heartbeat).total_seconds()
                
                if time_since_heartbeat > registration.ttl:
                    expired_services.append(service_id)
            
            # Remove expired services
            for service_id in expired_services:
                logger.warning(f"Service {service_id} expired, removing from registry")
                await self.deregister_service(service_id, "TTL expired")
                await self._emit_event(
                    ServiceLifecycleEvent.EXPIRED,
                    service_id,
                    self.services.get(service_id, {}).get("service_name", "unknown"),
                    {"reason": "TTL expired"}
                )
            
        except Exception as e:
            logger.error(f"Error cleaning up expired services: {e}")
    
    async def _cleanup_old_events(self) -> None:
        """Clean up old events."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=self.config.event_retention_hours)
            
            # Clean memory events
            self.service_events = [
                event for event in self.service_events
                if event.timestamp > cutoff_time
            ]
            
            # Clean database events
            if self.config.enable_persistence and self.db_connection:
                cursor = self.db_connection.cursor()
                cursor.execute(
                    "DELETE FROM service_events WHERE timestamp < ?",
                    (cutoff_time.isoformat(),)
                )
                self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"Error cleaning up old events: {e}")