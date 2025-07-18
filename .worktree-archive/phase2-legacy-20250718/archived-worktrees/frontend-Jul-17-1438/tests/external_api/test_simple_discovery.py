"""
Tests for Simple Service Discovery.
"""

import pytest

from external_api.simple_discovery import SimpleServiceDiscovery, Service


class TestSimpleServiceDiscovery:
    """Test suite for SimpleServiceDiscovery."""
    
    @pytest.fixture
    def discovery(self):
        """Create discovery instance."""
        return SimpleServiceDiscovery()
    
    @pytest.fixture
    def sample_service(self):
        """Create sample service."""
        return Service(
            service_id="user-svc-1",
            name="user-service",
            host="localhost",
            port=8080
        )
    
    def test_initialization(self, discovery):
        """Test discovery initialization."""
        assert discovery.services == {}
        assert discovery.registered_at == {}
    
    def test_register_service(self, discovery, sample_service):
        """Test service registration."""
        result = discovery.register(sample_service)
        assert result is True
        assert sample_service.service_id in discovery.services
        assert sample_service.service_id in discovery.registered_at
        
        # Verify service details
        registered = discovery.services[sample_service.service_id]
        assert registered.name == "user-service"
        assert registered.host == "localhost"
        assert registered.port == 8080
        assert registered.status == "healthy"
    
    def test_unregister_service(self, discovery, sample_service):
        """Test service unregistration."""
        # Register first
        discovery.register(sample_service)
        assert sample_service.service_id in discovery.services
        
        # Unregister
        result = discovery.unregister(sample_service.service_id)
        assert result is True
        assert sample_service.service_id not in discovery.services
        assert sample_service.service_id not in discovery.registered_at
    
    def test_unregister_nonexistent(self, discovery):
        """Test unregistering non-existent service."""
        result = discovery.unregister("nonexistent")
        assert result is False
    
    def test_find_by_name(self, discovery):
        """Test finding services by name."""
        # Register multiple services
        service1 = Service("svc1", "user-service", "host1", 8080)
        service2 = Service("svc2", "user-service", "host2", 8080) 
        service3 = Service("svc3", "order-service", "host3", 8080)
        
        discovery.register(service1)
        discovery.register(service2)
        discovery.register(service3)
        
        # Find user services
        user_services = discovery.find_by_name("user-service")
        assert len(user_services) == 2
        assert all(s.name == "user-service" for s in user_services)
        
        # Find order services
        order_services = discovery.find_by_name("order-service")
        assert len(order_services) == 1
        assert order_services[0].name == "order-service"
        
        # Find non-existent
        missing = discovery.find_by_name("missing-service")
        assert len(missing) == 0
    
    def test_get_service(self, discovery, sample_service):
        """Test getting service by ID."""
        # Not found initially
        result = discovery.get_service(sample_service.service_id)
        assert result is None
        
        # Register and find
        discovery.register(sample_service)
        result = discovery.get_service(sample_service.service_id)
        assert result is not None
        assert result.service_id == sample_service.service_id
        assert result.name == sample_service.name
    
    def test_list_all(self, discovery):
        """Test listing all services."""
        # Empty initially
        services = discovery.list_all()
        assert services == []
        
        # Add services
        service1 = Service("svc1", "user-service", "host1", 8080)
        service2 = Service("svc2", "order-service", "host2", 8080)
        
        discovery.register(service1)
        discovery.register(service2)
        
        services = discovery.list_all()
        assert len(services) == 2
        service_ids = [s.service_id for s in services]
        assert "svc1" in service_ids
        assert "svc2" in service_ids
    
    def test_get_stats(self, discovery):
        """Test getting statistics."""
        # Empty stats
        stats = discovery.get_stats()
        assert stats["total_services"] == 0
        assert stats["healthy_services"] == 0
        assert stats["unique_names"] == 0
        
        # Add services
        service1 = Service("svc1", "user-service", "host1", 8080, "healthy")
        service2 = Service("svc2", "user-service", "host2", 8080, "unhealthy")
        service3 = Service("svc3", "order-service", "host3", 8080, "healthy")
        
        discovery.register(service1)
        discovery.register(service2)
        discovery.register(service3)
        
        stats = discovery.get_stats()
        assert stats["total_services"] == 3
        assert stats["healthy_services"] == 2  # Only healthy ones
        assert stats["unique_names"] == 2  # user-service and order-service
    
    def test_service_endpoint(self):
        """Test service endpoint generation."""
        service = Service("test", "test-service", "localhost", 8080)
        assert service.endpoint() == "http://localhost:8080"
        
        service2 = Service("test2", "api", "api.example.com", 443)
        assert service2.endpoint() == "http://api.example.com:443"
    
    def test_service_defaults(self):
        """Test service default values."""
        service = Service("test", "test-service", "localhost", 8080)
        assert service.status == "healthy"  # Default status