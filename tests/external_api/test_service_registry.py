"""
Tests for Service Registry component.
"""

import pytest
import asyncio
import os
import tempfile
from datetime import datetime, timedelta

pytestmark = pytest.mark.asyncio

from external_api.service_discovery import ServiceInstance, ServiceStatus
from external_api.service_registry import (
    PersistentServiceRegistry,
    ServiceRegistryConfig,
    ServiceLifecycleEvent,
    ServiceEvent
)


class TestPersistentServiceRegistry:
    """Test suite for PersistentServiceRegistry class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def registry_config(self, temp_db_path):
        """Create service registry configuration."""
        return ServiceRegistryConfig(
            database_path=temp_db_path,
            backup_interval=1,
            cleanup_interval=1,
            event_retention_hours=1,
            enable_persistence=True,
            enable_circuit_breakers=True,
            service_ttl=10
        )

    @pytest.fixture
    def service_registry(self, registry_config):
        """Create service registry instance."""
        return PersistentServiceRegistry(registry_config)

    @pytest.fixture
    def sample_service_instance(self):
        """Create sample service instance."""
        return ServiceInstance(
            service_id="test-service-001",
            service_name="test-service",
            host="localhost",
            port=8080,
            metadata={"version": "1.0.0", "environment": "test"},
            health_check_url="http://localhost:8080/health",
            tags=["web", "api"],
            version="1.0.0"
        )

    @pytest.fixture
    def another_service_instance(self):
        """Create another sample service instance."""
        return ServiceInstance(
            service_id="test-service-002",
            service_name="test-service",
            host="localhost",
            port=8081,
            metadata={"version": "1.0.1", "environment": "test"},
            health_check_url="http://localhost:8081/health",
            tags=["web", "api"],
            version="1.0.1"
        )

    async def test_registry_initialization(self, service_registry):
        """Test service registry initialization."""
        assert len(service_registry.services) == 0
        assert len(service_registry.service_events) == 0
        assert not service_registry._running

    async def test_start_stop_registry(self, service_registry):
        """Test starting and stopping registry."""
        # Test start
        await service_registry.start()
        assert service_registry._running is True
        assert service_registry._cleanup_task is not None
        assert service_registry._backup_task is not None

        # Test stop
        await service_registry.stop()
        assert service_registry._running is False

    async def test_register_service_success(self, service_registry, sample_service_instance):
        """Test successful service registration."""
        await service_registry.start()
        
        result = await service_registry.register_service(
            sample_service_instance,
            dependencies=["dependency-service"],
            metadata={"custom": "value"}
        )
        
        assert result is True
        assert sample_service_instance.service_id in service_registry.services
        
        registration = service_registry.services[sample_service_instance.service_id]
        assert registration.instance.service_id == sample_service_instance.service_id
        assert registration.status == ServiceStatus.STARTING
        
        # Check dependencies
        assert sample_service_instance.service_id in service_registry.service_dependencies
        assert "dependency-service" in service_registry.service_dependencies[sample_service_instance.service_id]
        
        # Check events
        assert len(service_registry.service_events) > 0
        assert service_registry.service_events[-1].event_type == ServiceLifecycleEvent.REGISTERED
        
        await service_registry.stop()

    async def test_deregister_service_success(self, service_registry, sample_service_instance):
        """Test successful service deregistration."""
        await service_registry.start()
        
        # Register first
        await service_registry.register_service(sample_service_instance)
        assert sample_service_instance.service_id in service_registry.services
        
        # Deregister
        result = await service_registry.deregister_service(
            sample_service_instance.service_id,
            "Test deregistration"
        )
        
        assert result is True
        assert sample_service_instance.service_id not in service_registry.services
        
        # Check events
        deregister_events = [
            e for e in service_registry.service_events
            if e.event_type == ServiceLifecycleEvent.DEREGISTERED
        ]
        assert len(deregister_events) > 0
        
        await service_registry.stop()

    async def test_deregister_nonexistent_service(self, service_registry):
        """Test deregistering non-existent service."""
        await service_registry.start()
        
        result = await service_registry.deregister_service("nonexistent-service")
        assert result is False
        
        await service_registry.stop()

    async def test_update_service(self, service_registry, sample_service_instance):
        """Test updating service information."""
        await service_registry.start()
        
        # Register service
        await service_registry.register_service(sample_service_instance)
        
        # Update service
        updates = {
            "metadata": {"version": "2.0.0", "new_field": "value"},
            "tags": ["web", "api", "v2"],
            "health_check_url": "http://localhost:8080/v2/health"
        }
        
        result = await service_registry.update_service(
            sample_service_instance.service_id,
            updates
        )
        
        assert result is True
        
        registration = service_registry.services[sample_service_instance.service_id]
        assert registration.instance.metadata["version"] == "2.0.0"
        assert registration.instance.metadata["new_field"] == "value"
        assert "v2" in registration.instance.tags
        assert registration.instance.health_check_url == "http://localhost:8080/v2/health"
        
        # Check events
        update_events = [
            e for e in service_registry.service_events
            if e.event_type == ServiceLifecycleEvent.UPDATED
        ]
        assert len(update_events) > 0
        
        await service_registry.stop()

    async def test_discover_services(self, service_registry, sample_service_instance, another_service_instance):
        """Test service discovery with filtering."""
        await service_registry.start()
        
        # Register services
        await service_registry.register_service(sample_service_instance)
        await service_registry.register_service(another_service_instance)
        
        # Mark one as healthy
        service_registry.services[sample_service_instance.service_id].status = ServiceStatus.HEALTHY
        service_registry.services[another_service_instance.service_id].status = ServiceStatus.UNHEALTHY
        
        # Discover all instances
        all_instances = await service_registry.discover_services("test-service", include_unhealthy=True)
        assert len(all_instances) == 2
        
        # Discover only healthy instances
        healthy_instances = await service_registry.discover_services("test-service", include_unhealthy=False)
        assert len(healthy_instances) == 1
        assert healthy_instances[0].service_id == sample_service_instance.service_id
        
        # Discover by tags
        tagged_instances = await service_registry.discover_services("test-service", tags=["web", "api"])
        assert len(tagged_instances) == 2  # Both have these tags
        
        # Discover by specific tag
        web_instances = await service_registry.discover_services("test-service", tags=["web"])
        assert len(web_instances) == 2
        
        await service_registry.stop()

    async def test_get_service_health(self, service_registry, sample_service_instance):
        """Test getting service health information."""
        await service_registry.start()
        
        # Register service with dependencies
        await service_registry.register_service(
            sample_service_instance,
            dependencies=["dependency-service"]
        )
        
        # Get health info
        health_info = await service_registry.get_service_health(sample_service_instance.service_id)
        
        assert health_info is not None
        assert health_info["service_id"] == sample_service_instance.service_id
        assert health_info["service_name"] == sample_service_instance.service_name
        assert health_info["status"] == ServiceStatus.STARTING.value
        assert "uptime_seconds" in health_info
        assert "dependencies" in health_info
        assert "dependency-service" in health_info["dependencies"]
        assert "circuit_breaker" in health_info
        
        await service_registry.stop()

    async def test_get_service_health_nonexistent(self, service_registry):
        """Test getting health for non-existent service."""
        await service_registry.start()
        
        health_info = await service_registry.get_service_health("nonexistent-service")
        assert health_info is None
        
        await service_registry.stop()

    async def test_get_service_events(self, service_registry, sample_service_instance):
        """Test getting service events with filtering."""
        await service_registry.start()
        
        # Generate events
        await service_registry.register_service(sample_service_instance)
        await service_registry.update_service(sample_service_instance.service_id, {"metadata": {"test": "value"}})
        await service_registry.deregister_service(sample_service_instance.service_id)
        
        # Get all events
        all_events = await service_registry.get_service_events()
        assert len(all_events) >= 3
        
        # Get events for specific service
        service_events = await service_registry.get_service_events(sample_service_instance.service_id)
        assert len(service_events) >= 3
        assert all(e.service_id == sample_service_instance.service_id for e in service_events)
        
        # Get events by type
        register_events = await service_registry.get_service_events(
            event_type=ServiceLifecycleEvent.REGISTERED
        )
        assert len(register_events) >= 1
        assert all(e.event_type == ServiceLifecycleEvent.REGISTERED for e in register_events)
        
        # Test limit
        limited_events = await service_registry.get_service_events(limit=1)
        assert len(limited_events) == 1
        
        await service_registry.stop()

    async def test_get_registry_stats(self, service_registry, sample_service_instance, another_service_instance):
        """Test getting registry statistics."""
        await service_registry.start()
        
        # Register services
        await service_registry.register_service(sample_service_instance)
        await service_registry.register_service(another_service_instance)
        
        # Mark one as healthy
        service_registry.services[sample_service_instance.service_id].status = ServiceStatus.HEALTHY
        
        stats = await service_registry.get_registry_stats()
        
        assert stats["total_services"] == 2
        assert stats["healthy_services"] == 1
        assert stats["unhealthy_services"] == 1
        assert stats["unique_service_names"] == 1
        assert "test-service" in stats["service_distribution"]
        assert stats["service_distribution"]["test-service"] == 2
        assert "metrics" in stats
        assert "circuit_breakers" in stats
        assert "configuration" in stats
        
        await service_registry.stop()

    async def test_backup_registry(self, service_registry, sample_service_instance):
        """Test manual registry backup."""
        await service_registry.start()
        
        # Register service and generate events
        await service_registry.register_service(sample_service_instance)
        
        # Create backup
        backup_path = tempfile.mktemp(suffix='.json')
        try:
            result = await service_registry.backup_registry(backup_path)
            assert result is True
            assert os.path.exists(backup_path)
            
            # Verify backup content
            import json
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
            
            assert "timestamp" in backup_data
            assert "services" in backup_data
            assert "events" in backup_data
            assert sample_service_instance.service_id in backup_data["services"]
            
        finally:
            if os.path.exists(backup_path):
                os.unlink(backup_path)
        
        await service_registry.stop()

    async def test_persistence_database_operations(self, service_registry, sample_service_instance):
        """Test database persistence operations."""
        await service_registry.start()
        
        # Register service (should persist to database)
        await service_registry.register_service(sample_service_instance)
        
        # Stop and restart to test loading from database
        await service_registry.stop()
        
        # Create new registry with same database
        new_registry = PersistentServiceRegistry(service_registry.config)
        await new_registry.start()
        
        # Service should be loaded from database
        assert sample_service_instance.service_id in new_registry.services
        loaded_registration = new_registry.services[sample_service_instance.service_id]
        assert loaded_registration.instance.service_name == sample_service_instance.service_name
        assert loaded_registration.instance.host == sample_service_instance.host
        assert loaded_registration.instance.port == sample_service_instance.port
        
        await new_registry.stop()

    async def test_service_ttl_expiration(self, service_registry, sample_service_instance):
        """Test service TTL expiration and cleanup."""
        # Use short TTL for testing
        service_registry.config.service_ttl = 1  # 1 second
        service_registry.config.cleanup_interval = 0.5  # 0.5 second cleanup
        
        await service_registry.start()
        
        # Register service
        await service_registry.register_service(sample_service_instance)
        assert sample_service_instance.service_id in service_registry.services
        
        # Wait for TTL to expire and cleanup to run
        await asyncio.sleep(2)
        
        # Service should be expired and removed
        assert sample_service_instance.service_id not in service_registry.services
        
        # Check for expiration event
        expire_events = [
            e for e in service_registry.service_events
            if e.event_type == ServiceLifecycleEvent.EXPIRED
        ]
        assert len(expire_events) > 0
        
        await service_registry.stop()

    async def test_event_cleanup(self, service_registry):
        """Test old event cleanup."""
        service_registry.config.event_retention_hours = 0.001  # Very short retention for testing
        
        await service_registry.start()
        
        # Create an old event manually
        old_event = ServiceEvent(
            event_id="old-event",
            event_type=ServiceLifecycleEvent.REGISTERED,
            service_id="test-service",
            service_name="test-service",
            timestamp=datetime.utcnow() - timedelta(hours=1),  # 1 hour ago
            details={}
        )
        service_registry.service_events.append(old_event)
        
        # Wait for cleanup
        await asyncio.sleep(1.5)
        
        # Old event should be cleaned up
        event_ids = [e.event_id for e in service_registry.service_events]
        assert "old-event" not in event_ids
        
        await service_registry.stop()

    async def test_concurrent_operations(self, service_registry):
        """Test concurrent registry operations."""
        await service_registry.start()
        
        # Create multiple service instances
        instances = []
        for i in range(10):
            instance = ServiceInstance(
                service_id=f"service-{i:03d}",
                service_name=f"service-type-{i % 3}",  # 3 different service types
                host="localhost",
                port=8080 + i,
                metadata={"instance": i}
            )
            instances.append(instance)
        
        # Register all concurrently
        register_tasks = [
            service_registry.register_service(instance) 
            for instance in instances
        ]
        results = await asyncio.gather(*register_tasks)
        
        # All should succeed
        assert all(results)
        assert len(service_registry.services) == 10
        
        # Update all concurrently
        update_tasks = [
            service_registry.update_service(instance.service_id, {"metadata": {"updated": True}})
            for instance in instances
        ]
        update_results = await asyncio.gather(*update_tasks)
        
        assert all(update_results)
        
        # Verify updates
        for instance in instances:
            registration = service_registry.services[instance.service_id]
            assert registration.instance.metadata["updated"] is True
        
        await service_registry.stop()

    async def test_circuit_breaker_integration(self, service_registry, sample_service_instance):
        """Test circuit breaker integration."""
        await service_registry.start()
        
        # Register service (should create circuit breaker)
        await service_registry.register_service(sample_service_instance)
        
        # Check circuit breaker was created
        assert service_registry.circuit_breaker_manager is not None
        cb_name = f"service_{sample_service_instance.service_id}"
        assert cb_name in service_registry.circuit_breaker_manager.circuit_breakers
        
        # Get health info should include circuit breaker status
        health_info = await service_registry.get_service_health(sample_service_instance.service_id)
        assert health_info["circuit_breaker"] is not None
        assert "state" in health_info["circuit_breaker"]
        
        await service_registry.stop()

    async def test_registry_without_persistence(self):
        """Test registry with persistence disabled."""
        config = ServiceRegistryConfig(enable_persistence=False)
        registry = PersistentServiceRegistry(config)
        
        await registry.start()
        
        # Should work without database
        instance = ServiceInstance(
            service_id="test-service",
            service_name="test-service",
            host="localhost",
            port=8080,
            metadata={}
        )
        
        result = await registry.register_service(instance)
        assert result is True
        assert instance.service_id in registry.services
        
        await registry.stop()

    async def test_registry_without_circuit_breakers(self):
        """Test registry with circuit breakers disabled."""
        config = ServiceRegistryConfig(enable_circuit_breakers=False)
        registry = PersistentServiceRegistry(config)
        
        await registry.start()
        
        # Should work without circuit breakers
        instance = ServiceInstance(
            service_id="test-service",
            service_name="test-service",
            host="localhost",
            port=8080,
            metadata={}
        )
        
        result = await registry.register_service(instance)
        assert result is True
        
        # Circuit breaker manager should be None
        assert registry.circuit_breaker_manager is None
        
        # Health info should not include circuit breaker
        health_info = await registry.get_service_health(instance.service_id)
        assert health_info["circuit_breaker"] is None
        
        await registry.stop()

    async def test_error_handling(self, service_registry):
        """Test error handling in registry operations."""
        await service_registry.start()
        
        # Test with invalid service data
        result = await service_registry.update_service("nonexistent-service", {"test": "value"})
        assert result is False
        
        # Registry should still be functional
        instance = ServiceInstance(
            service_id="test-service",
            service_name="test-service",
            host="localhost",
            port=8080,
            metadata={}
        )
        
        result = await service_registry.register_service(instance)
        assert result is True
        
        await service_registry.stop()