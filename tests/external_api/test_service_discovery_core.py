"""
Tests for Service Discovery Core functionality.
"""

import pytest
import asyncio
from datetime import datetime

from external_api.service_discovery_core import (
    ServiceDiscoveryCore,
    ServiceInstance,
    ServiceRegistration,
    ServiceStatus
)


class TestServiceDiscoveryCore:
    """Test suite for ServiceDiscoveryCore."""
    
    @pytest.fixture
    def service_discovery(self):
        """Create ServiceDiscoveryCore instance."""
        return ServiceDiscoveryCore()
    
    @pytest.fixture
    def sample_service(self):
        """Create sample service instance."""
        return ServiceInstance(
            service_id="test-service-001",
            service_name="test-service",
            host="localhost",
            port=8080,
            metadata={"version": "1.0.0", "environment": "test"},
            tags=["web", "api"],
            version="1.0.0"
        )
    
    @pytest.mark.asyncio
    async def test_core_initialization(self, service_discovery):
        """Test service discovery core initialization."""
        assert service_discovery.services == {}
        assert service_discovery._running is False
    
    @pytest.mark.asyncio
    async def test_start_stop(self, service_discovery):
        """Test starting and stopping service discovery."""
        # Start
        await service_discovery.start()
        assert service_discovery._running is True
        
        # Start again (should not error)
        await service_discovery.start()
        assert service_discovery._running is True
        
        # Stop
        await service_discovery.stop()
        assert service_discovery._running is False
        
        # Stop again (should not error)
        await service_discovery.stop()
        assert service_discovery._running is False
    
    @pytest.mark.asyncio
    async def test_register_service(self, service_discovery, sample_service):
        """Test service registration."""
        result = await service_discovery.register_service(sample_service)
        assert result is True
        
        # Verify service is registered
        assert sample_service.service_id in service_discovery.services
        registration = service_discovery.services[sample_service.service_id]
        assert registration.instance.service_name == "test-service"
        assert registration.status == ServiceStatus.HEALTHY
        assert isinstance(registration.registered_at, datetime)
    
    @pytest.mark.asyncio
    async def test_deregister_service(self, service_discovery, sample_service):
        """Test service deregistration."""
        # Register first
        await service_discovery.register_service(sample_service)
        assert sample_service.service_id in service_discovery.services
        
        # Deregister
        result = await service_discovery.deregister_service(sample_service.service_id)
        assert result is True
        assert sample_service.service_id not in service_discovery.services
    
    @pytest.mark.asyncio
    async def test_deregister_nonexistent_service(self, service_discovery):
        """Test deregistering non-existent service."""
        result = await service_discovery.deregister_service("nonexistent-service")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_discover_services(self, service_discovery):
        """Test service discovery."""
        # Register multiple services
        services = [
            ServiceInstance("svc1", "user-service", "host1", 8080),
            ServiceInstance("svc2", "user-service", "host2", 8080),
            ServiceInstance("svc3", "order-service", "host3", 8080)
        ]
        
        for service in services:
            await service_discovery.register_service(service)
        
        # Discover user services
        user_services = await service_discovery.discover_services("user-service")
        assert len(user_services) == 2
        assert all(s.service_name == "user-service" for s in user_services)
        
        # Discover order services
        order_services = await service_discovery.discover_services("order-service")
        assert len(order_services) == 1
        assert order_services[0].service_name == "order-service"
        
        # Discover non-existent service
        missing_services = await service_discovery.discover_services("missing-service")
        assert len(missing_services) == 0
    
    @pytest.mark.asyncio
    async def test_get_service_by_id(self, service_discovery, sample_service):
        """Test getting service by ID."""
        # Service not registered
        result = await service_discovery.get_service_by_id(sample_service.service_id)
        assert result is None
        
        # Register and test
        await service_discovery.register_service(sample_service)
        result = await service_discovery.get_service_by_id(sample_service.service_id)
        assert result is not None
        assert result.service_id == sample_service.service_id
        assert result.service_name == sample_service.service_name
    
    @pytest.mark.asyncio
    async def test_get_service_status(self, service_discovery, sample_service):
        """Test getting service status."""
        # Service not registered
        status = await service_discovery.get_service_status(sample_service.service_id)
        assert status is None
        
        # Register and test
        await service_discovery.register_service(sample_service)
        status = await service_discovery.get_service_status(sample_service.service_id)
        assert status == ServiceStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_heartbeat(self, service_discovery, sample_service):
        """Test heartbeat functionality."""
        # Service not registered
        result = await service_discovery.heartbeat(sample_service.service_id)
        assert result is False
        
        # Register and test heartbeat
        await service_discovery.register_service(sample_service)
        result = await service_discovery.heartbeat(sample_service.service_id)
        assert result is True
        
        # Verify heartbeat updated
        registration = service_discovery.services[sample_service.service_id]
        assert registration.last_heartbeat is not None
    
    @pytest.mark.asyncio
    async def test_list_services(self, service_discovery):
        """Test listing all services."""
        # Empty initially
        services = await service_discovery.list_services()
        assert services == {}
        
        # Register services
        service1 = ServiceInstance("svc1", "user-service", "host1", 8080)
        service2 = ServiceInstance("svc2", "user-service", "host2", 8080)
        service3 = ServiceInstance("svc3", "order-service", "host3", 8080)
        
        await service_discovery.register_service(service1)
        await service_discovery.register_service(service2)
        await service_discovery.register_service(service3)
        
        # List services
        services = await service_discovery.list_services()
        assert len(services) == 2  # 2 unique service names
        assert "user-service" in services
        assert "order-service" in services
        assert len(services["user-service"]) == 2
        assert len(services["order-service"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_stats(self, service_discovery):
        """Test getting service statistics."""
        # Initially empty
        stats = service_discovery.get_stats()
        assert stats["total_instances"] == 0
        assert stats["healthy_instances"] == 0
        assert stats["unique_services"] == 0
        assert stats["service_names"] == []
        assert stats["running"] is False
        
        # Start and register services
        await service_discovery.start()
        
        service1 = ServiceInstance("svc1", "user-service", "host1", 8080)
        service2 = ServiceInstance("svc2", "order-service", "host2", 8080)
        
        await service_discovery.register_service(service1)
        await service_discovery.register_service(service2)
        
        stats = service_discovery.get_stats()
        assert stats["total_instances"] == 2
        assert stats["healthy_instances"] == 2
        assert stats["unique_services"] == 2
        assert set(stats["service_names"]) == {"user-service", "order-service"}
        assert stats["running"] is True
    
    def test_service_instance_dataclass(self):
        """Test ServiceInstance dataclass."""
        instance = ServiceInstance(
            service_id="test-id",
            service_name="test-service",
            host="localhost",
            port=8080
        )
        
        assert instance.service_id == "test-id"
        assert instance.service_name == "test-service"
        assert instance.host == "localhost"
        assert instance.port == 8080
        assert instance.metadata == {}
        assert instance.tags == []
        assert instance.version == "1.0.0"
    
    def test_service_registration_dataclass(self):
        """Test ServiceRegistration dataclass."""
        instance = ServiceInstance("test-id", "test-service", "localhost", 8080)
        now = datetime.now()
        
        registration = ServiceRegistration(
            instance=instance,
            registered_at=now,
            last_heartbeat=now,
            status=ServiceStatus.HEALTHY
        )
        
        assert registration.instance == instance
        assert registration.registered_at == now
        assert registration.last_heartbeat == now
        assert registration.status == ServiceStatus.HEALTHY
        
        # Test to_dict
        data = registration.to_dict()
        assert "instance" in data
        assert "registered_at" in data
        assert "last_heartbeat" in data
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_service_status_enum(self):
        """Test ServiceStatus enum."""
        assert ServiceStatus.HEALTHY.value == "healthy"
        assert ServiceStatus.UNHEALTHY.value == "unhealthy"
        assert ServiceStatus.STARTING.value == "starting"
        assert ServiceStatus.STOPPING.value == "stopping"
        assert ServiceStatus.UNKNOWN.value == "unknown"