"""
Tests for Service Discovery component.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.asyncio

from external_api.service_discovery import (
    ServiceDiscovery,
    ServiceInstance,
    ServiceRegistration,
    ServiceStatus
)


class TestServiceDiscovery:
    """Test suite for ServiceDiscovery class."""
    
    @pytest.fixture
    def service_discovery(self):
        """Create ServiceDiscovery instance."""
        config = {
            "health_check_interval": 1,
            "cleanup_interval": 2
        }
        return ServiceDiscovery(config)
    
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
    def sample_service_instance_no_health(self):
        """Create sample service instance without health check."""
        return ServiceInstance(
            service_id="test-service-002",
            service_name="test-service",
            host="localhost",
            port=8081,
            metadata={"version": "1.0.0"},
            tags=["worker"]
        )
    
    async def test_service_discovery_initialization(self, service_discovery):
        """Test service discovery initialization."""
        assert service_discovery.config["health_check_interval"] == 1
        assert service_discovery.config["cleanup_interval"] == 2
        assert service_discovery.services == {}
        assert service_discovery.service_watchers == {}
        assert service_discovery._running is False
    
    async def test_start_stop_service_discovery(self, service_discovery):
        """Test starting and stopping service discovery."""
        # Test start
        await service_discovery.start()
        assert service_discovery._running is True
        assert service_discovery._cleanup_task is not None
        
        # Test start when already running
        await service_discovery.start()  # Should not raise error
        assert service_discovery._running is True
        
        # Test stop
        await service_discovery.stop()
        assert service_discovery._running is False
        
        # Test stop when not running
        await service_discovery.stop()  # Should not raise error
        assert service_discovery._running is False
    
    async def test_register_service_success(self, service_discovery, sample_service_instance):
        """Test successful service registration."""
        result = await service_discovery.register_service(sample_service_instance)
        
        assert result is True
        assert sample_service_instance.service_id in service_discovery.services
        
        registration = service_discovery.services[sample_service_instance.service_id]
        assert registration.instance == sample_service_instance
        assert registration.status == ServiceStatus.STARTING
        assert registration.registered_at is not None
        assert registration.last_heartbeat is not None
    
    async def test_register_service_no_health_check(self, service_discovery, sample_service_instance_no_health):
        """Test service registration without health check."""
        result = await service_discovery.register_service(sample_service_instance_no_health)
        
        assert result is True
        registration = service_discovery.services[sample_service_instance_no_health.service_id]
        assert registration.status == ServiceStatus.HEALTHY  # Should be healthy without health check
    
    async def test_deregister_service_success(self, service_discovery, sample_service_instance):
        """Test successful service deregistration."""
        # Register first
        await service_discovery.register_service(sample_service_instance)
        assert sample_service_instance.service_id in service_discovery.services
        
        # Deregister
        result = await service_discovery.deregister_service(sample_service_instance.service_id)
        
        assert result is True
        assert sample_service_instance.service_id not in service_discovery.services
    
    async def test_deregister_nonexistent_service(self, service_discovery):
        """Test deregistering a non-existent service."""
        result = await service_discovery.deregister_service("non-existent-service")
        assert result is False
    
    async def test_discover_services(self, service_discovery, sample_service_instance, sample_service_instance_no_health):
        """Test service discovery by name."""
        # Register multiple instances of same service
        await service_discovery.register_service(sample_service_instance)
        await service_discovery.register_service(sample_service_instance_no_health)
        
        # Discover all instances
        instances = await service_discovery.discover_services("test-service", healthy_only=False)
        assert len(instances) == 2
        
        # Discover only healthy instances
        instances = await service_discovery.discover_services("test-service", healthy_only=True)
        assert len(instances) == 1  # Only the one without health check is healthy
    
    async def test_get_service_by_id(self, service_discovery, sample_service_instance):
        """Test getting service by ID."""
        # Service not registered
        instance = await service_discovery.get_service_by_id(sample_service_instance.service_id)
        assert instance is None
        
        # Register and get
        await service_discovery.register_service(sample_service_instance)
        instance = await service_discovery.get_service_by_id(sample_service_instance.service_id)
        assert instance == sample_service_instance
    
    async def test_get_healthy_instance(self, service_discovery, sample_service_instance_no_health):
        """Test getting a healthy instance."""
        # No instances
        instance = await service_discovery.get_healthy_instance("test-service")
        assert instance is None
        
        # Register healthy instance
        await service_discovery.register_service(sample_service_instance_no_health)
        instance = await service_discovery.get_healthy_instance("test-service")
        assert instance == sample_service_instance_no_health
    
    async def test_heartbeat_success(self, service_discovery, sample_service_instance):
        """Test successful heartbeat."""
        # Register service
        await service_discovery.register_service(sample_service_instance)
        
        # Send heartbeat
        result = await service_discovery.heartbeat(sample_service_instance.service_id)
        assert result is True
        
        registration = service_discovery.services[sample_service_instance.service_id]
        assert registration.last_heartbeat is not None
    
    async def test_heartbeat_unknown_service(self, service_discovery):
        """Test heartbeat for unknown service."""
        result = await service_discovery.heartbeat("unknown-service")
        assert result is False
    
    async def test_heartbeat_recovery(self, service_discovery, sample_service_instance):
        """Test heartbeat recovery from unhealthy status."""
        # Register and simulate unhealthy status
        await service_discovery.register_service(sample_service_instance)
        registration = service_discovery.services[sample_service_instance.service_id]
        registration.status = ServiceStatus.UNHEALTHY
        
        # Send heartbeat
        result = await service_discovery.heartbeat(sample_service_instance.service_id)
        assert result is True
        assert registration.status == ServiceStatus.HEALTHY
    
    async def test_get_service_status(self, service_discovery, sample_service_instance):
        """Test getting service status."""
        # Non-existent service
        status = await service_discovery.get_service_status("non-existent")
        assert status is None
        
        # Register and get status
        await service_discovery.register_service(sample_service_instance)
        status = await service_discovery.get_service_status(sample_service_instance.service_id)
        assert status == ServiceStatus.STARTING
    
    async def test_list_services(self, service_discovery, sample_service_instance, sample_service_instance_no_health):
        """Test listing all services."""
        # Empty list
        services = await service_discovery.list_services()
        assert services == {}
        
        # Register services
        await service_discovery.register_service(sample_service_instance)
        await service_discovery.register_service(sample_service_instance_no_health)
        
        services = await service_discovery.list_services()
        assert "test-service" in services
        assert len(services["test-service"]) == 2
        
        # Check structure
        service_info = services["test-service"][0]
        assert "instance" in service_info
        assert "status" in service_info
        assert "registered_at" in service_info
        assert "last_heartbeat" in service_info
    
    async def test_get_system_info(self, service_discovery, sample_service_instance, sample_service_instance_no_health):
        """Test getting system information."""
        # Empty system
        info = await service_discovery.get_system_info()
        assert info["total_instances"] == 0
        assert info["healthy_instances"] == 0
        assert info["unique_services"] == 0
        assert info["running"] is False
        
        # Register services
        await service_discovery.register_service(sample_service_instance)
        await service_discovery.register_service(sample_service_instance_no_health)
        
        info = await service_discovery.get_system_info()
        assert info["total_instances"] == 2
        assert info["healthy_instances"] == 1  # Only one without health check is healthy
        assert info["unique_services"] == 1
        assert "test-service" in info["service_names"]
    
    async def test_watch_service(self, service_discovery, sample_service_instance):
        """Test watching service changes."""
        events = []
        
        async def test_callback(event, instance):
            events.append((event, instance.service_id))
        
        # Add watcher
        await service_discovery.watch_service("test-service", test_callback)
        assert "test-service" in service_discovery.service_watchers
        assert len(service_discovery.service_watchers["test-service"]) == 1
        
        # Register service (should trigger callback)
        await service_discovery.register_service(sample_service_instance)
        
        # Check that callback was called
        assert len(events) == 1
        assert events[0][0] == "registered"
        assert events[0][1] == sample_service_instance.service_id
    
    async def test_health_check_loop(self, service_discovery, sample_service_instance):
        """Test health check loop functionality."""
        await service_discovery.start()
        
        # Register service with health check
        await service_discovery.register_service(sample_service_instance)
        
        # Check that health check task is created
        assert sample_service_instance.service_id in service_discovery._health_check_tasks
        
        # Wait a bit for health check to run
        await asyncio.sleep(0.1)
        
        await service_discovery.stop()
    
    async def test_cleanup_expired_services(self, service_discovery, sample_service_instance):
        """Test cleanup of expired services."""
        await service_discovery.start()
        
        # Register service
        await service_discovery.register_service(sample_service_instance)
        
        # Manually set old heartbeat time
        registration = service_discovery.services[sample_service_instance.service_id]
        registration.last_heartbeat = datetime.now() - timedelta(seconds=400)  # Older than TTL
        
        # Wait for cleanup
        await asyncio.sleep(0.1)
        
        await service_discovery.stop()
    
    async def test_perform_health_check(self, service_discovery, sample_service_instance):
        """Test health check performance."""
        # Test with health check URL
        result = await service_discovery._perform_health_check(sample_service_instance)
        assert result is True  # Simulated success
        
        # Test without health check URL
        instance_no_health = ServiceInstance(
            service_id="test-no-health",
            service_name="test",
            host="localhost",
            port=8080,
            metadata={}
        )
        result = await service_discovery._perform_health_check(instance_no_health)
        assert result is True
    
    async def test_service_instance_dataclass(self):
        """Test ServiceInstance dataclass functionality."""
        instance = ServiceInstance(
            service_id="test-001",
            service_name="test-service",
            host="localhost",
            port=8080,
            metadata={"key": "value"}
        )
        
        assert instance.service_id == "test-001"
        assert instance.service_name == "test-service"
        assert instance.host == "localhost"
        assert instance.port == 8080
        assert instance.metadata == {"key": "value"}
        assert instance.tags == []  # Default from __post_init__
        assert instance.version == "1.0.0"
        assert instance.health_check_url is None
    
    async def test_service_registration_dataclass(self, sample_service_instance):
        """Test ServiceRegistration dataclass functionality."""
        registration = ServiceRegistration(
            instance=sample_service_instance,
            registered_at=datetime.now(),
            last_heartbeat=datetime.now(),
            status=ServiceStatus.HEALTHY
        )
        
        assert registration.instance == sample_service_instance
        assert registration.status == ServiceStatus.HEALTHY
        assert registration.health_check_interval == 30
        assert registration.ttl == 300
    
    async def test_service_status_enum(self):
        """Test ServiceStatus enum values."""
        assert ServiceStatus.HEALTHY.value == "healthy"
        assert ServiceStatus.UNHEALTHY.value == "unhealthy"
        assert ServiceStatus.STARTING.value == "starting"
        assert ServiceStatus.STOPPING.value == "stopping"
        assert ServiceStatus.UNKNOWN.value == "unknown"
    
    async def test_concurrent_service_operations(self, service_discovery):
        """Test concurrent service operations."""
        # Create multiple service instances
        instances = [
            ServiceInstance(
                service_id=f"test-{i}",
                service_name="test-service",
                host="localhost",
                port=8080 + i,
                metadata={"instance": i}
            )
            for i in range(10)
        ]
        
        # Register all concurrently
        tasks = [
            service_discovery.register_service(instance) 
            for instance in instances
        ]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(results)
        assert len(service_discovery.services) == 10
        
        # Discover all
        discovered = await service_discovery.discover_services("test-service", healthy_only=False)
        assert len(discovered) == 10
    
    async def test_watcher_error_handling(self, service_discovery, sample_service_instance):
        """Test error handling in watchers."""
        async def failing_callback(event, instance):
            raise Exception("Test error")
        
        # Add failing watcher
        await service_discovery.watch_service("test-service", failing_callback)
        
        # Register service (should not crash despite callback error)
        result = await service_discovery.register_service(sample_service_instance)
        assert result is True
    
    async def test_multiple_watchers(self, service_discovery, sample_service_instance):
        """Test multiple watchers for the same service."""
        events1 = []
        events2 = []
        
        async def callback1(event, instance):
            events1.append(event)
        
        async def callback2(event, instance):
            events2.append(event)
        
        # Add multiple watchers
        await service_discovery.watch_service("test-service", callback1)
        await service_discovery.watch_service("test-service", callback2)
        
        # Register service
        await service_discovery.register_service(sample_service_instance)
        
        # Both callbacks should be called
        assert len(events1) == 1
        assert len(events2) == 1
        assert events1[0] == "registered"
        assert events2[0] == "registered"