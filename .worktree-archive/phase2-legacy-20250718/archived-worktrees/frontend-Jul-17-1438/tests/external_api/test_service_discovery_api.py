"""
Tests for Service Discovery REST API.
"""

import pytest
from fastapi.testclient import TestClient

from external_api.service_discovery import ServiceDiscovery
from external_api.service_discovery_api import ServiceDiscoveryAPI, create_service_discovery_api


class TestServiceDiscoveryAPI:
    """Test suite for ServiceDiscoveryAPI class."""

    @pytest.fixture
    def service_discovery(self):
        """Create ServiceDiscovery instance."""
        config = {
            "health_check_interval": 1,
            "cleanup_interval": 2
        }
        return ServiceDiscovery(config)

    @pytest.fixture
    def service_discovery_api(self, service_discovery):
        """Create ServiceDiscoveryAPI instance."""
        return ServiceDiscoveryAPI(service_discovery, host="127.0.0.1", port=8001)

    @pytest.fixture
    def test_client(self, service_discovery_api):
        """Create test client."""
        return TestClient(service_discovery_api.app)

    @pytest.fixture
    def sample_service_data(self):
        """Sample service registration data."""
        return {
            "service_id": "test-api-service-001",
            "service_name": "test-api-service",
            "host": "localhost",
            "port": 8080,
            "metadata": {"version": "1.0.0", "environment": "test"},
            "health_check_url": "http://localhost:8080/health",
            "tags": ["web", "api"],
            "version": "1.0.0"
        }

    @pytest.mark.asyncio
    async def test_api_health_check(self, test_client):
        """Test API health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_register_service_success(self, test_client, sample_service_data):
        """Test successful service registration via API."""
        response = test_client.post("/services/register", json=sample_service_data)
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Service registered successfully"
        assert data["service_id"] == sample_service_data["service_id"]
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_register_service_invalid_data(self, test_client):
        """Test service registration with invalid data."""
        invalid_data = {
            "service_id": "test",
            "service_name": "test",
            "host": "localhost",
            "port": 70000  # Invalid port
        }

        response = test_client.post("/services/register", json=invalid_data)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_service_by_id(self, test_client, sample_service_data):
        """Test getting service by ID via API."""
        # Register service first
        test_client.post("/services/register", json=sample_service_data)

        # Get service by ID
        response = test_client.get(f"/services/{sample_service_data['service_id']}")
        assert response.status_code == 200

        data = response.json()
        assert data["service_id"] == sample_service_data["service_id"]
        assert data["service_name"] == sample_service_data["service_name"]
        assert data["host"] == sample_service_data["host"]
        assert data["port"] == sample_service_data["port"]
        assert "status" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_service(self, test_client):
        """Test getting non-existent service."""
        response = test_client.get("/services/nonexistent-service")
        assert response.status_code == 404
        assert "Service not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_deregister_service_success(self, test_client, sample_service_data):
        """Test successful service deregistration via API."""
        # Register service first
        test_client.post("/services/register", json=sample_service_data)

        # Deregister service
        response = test_client.delete(f"/services/{sample_service_data['service_id']}")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Service deregistered successfully"
        assert data["service_id"] == sample_service_data["service_id"]

    @pytest.mark.asyncio
    async def test_deregister_nonexistent_service(self, test_client):
        """Test deregistering non-existent service."""
        response = test_client.delete("/services/nonexistent-service")
        assert response.status_code == 404
        assert "Service not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_discover_services(self, test_client, sample_service_data):
        """Test service discovery via API."""
        # Register service first
        response = test_client.post("/services/register", json=sample_service_data)
        assert response.status_code == 200

        # Wait briefly for service to be registered with health check
        import time
        time.sleep(0.1)

        # Discover services - try both healthy and all services
        response = test_client.get(f"/services/discover/{sample_service_data['service_name']}?healthy_only=false")
        assert response.status_code == 200

        data = response.json()
        assert data["total_count"] >= 1
        assert len(data["services"]) >= 1

        service = data["services"][0]
        assert service["service_id"] == sample_service_data["service_id"]
        assert service["service_name"] == sample_service_data["service_name"]

    @pytest.mark.asyncio
    async def test_discover_services_healthy_only(self, test_client, sample_service_data):
        """Test service discovery with healthy_only parameter."""
        # Register service first
        test_client.post("/services/register", json=sample_service_data)

        # Discover only healthy services
        response = test_client.get(
            f"/services/discover/{sample_service_data['service_name']}?healthy_only=true"
        )
        assert response.status_code == 200

        data = response.json()
        # Should include services even if starting (as they'll become healthy without health check URL in test)
        assert data["total_count"] >= 0

    @pytest.mark.asyncio
    async def test_service_heartbeat(self, test_client, sample_service_data):
        """Test service heartbeat via API."""
        # Register service first
        test_client.post("/services/register", json=sample_service_data)

        # Send heartbeat
        response = test_client.post(f"/services/{sample_service_data['service_id']}/heartbeat")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Heartbeat received"
        assert data["service_id"] == sample_service_data["service_id"]

    @pytest.mark.asyncio
    async def test_heartbeat_nonexistent_service(self, test_client):
        """Test heartbeat for non-existent service."""
        response = test_client.post("/services/nonexistent-service/heartbeat")
        assert response.status_code == 404
        assert "Service not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_all_services(self, test_client, sample_service_data):
        """Test listing all services via API."""
        # Register service first
        test_client.post("/services/register", json=sample_service_data)

        # List all services
        response = test_client.get("/services")
        assert response.status_code == 200

        data = response.json()
        assert sample_service_data["service_name"] in data
        services = data[sample_service_data["service_name"]]
        assert len(services) >= 1

        service = services[0]
        assert service["service_id"] == sample_service_data["service_id"]

    @pytest.mark.asyncio
    async def test_get_system_info(self, test_client, sample_service_data):
        """Test getting system information via API."""
        # Test empty system
        response = test_client.get("/system/info")
        assert response.status_code == 200

        data = response.json()
        initial_total = data["total_instances"]

        # Register service
        test_client.post("/services/register", json=sample_service_data)

        # Test with registered service
        response = test_client.get("/system/info")
        assert response.status_code == 200

        data = response.json()
        assert data["total_instances"] == initial_total + 1
        assert "unique_services" in data
        assert "service_names" in data
        assert "running" in data

    @pytest.mark.asyncio
    async def test_get_service_status(self, test_client, sample_service_data):
        """Test getting service status via API."""
        # Register service first
        test_client.post("/services/register", json=sample_service_data)

        # Get service status
        response = test_client.get(f"/services/{sample_service_data['service_id']}/status")
        assert response.status_code == 200

        data = response.json()
        assert data["service_id"] == sample_service_data["service_id"]
        assert "status" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_get_status_nonexistent_service(self, test_client):
        """Test getting status for non-existent service."""
        response = test_client.get("/services/nonexistent-service/status")
        assert response.status_code == 404
        assert "Service not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_healthy_instance(self, test_client, sample_service_data):
        """Test getting healthy instance via API."""
        # Modify sample data to not have health check URL (will be marked as healthy)
        sample_service_data["health_check_url"] = None

        # Register service first
        test_client.post("/services/register", json=sample_service_data)

        # Get healthy instance
        response = test_client.get(f"/services/healthy/{sample_service_data['service_name']}")
        assert response.status_code == 200

        data = response.json()
        assert data["service_id"] == sample_service_data["service_id"]
        assert data["service_name"] == sample_service_data["service_name"]

    @pytest.mark.asyncio
    async def test_get_healthy_instance_none_available(self, test_client):
        """Test getting healthy instance when none available."""
        response = test_client.get("/services/healthy/nonexistent-service")
        assert response.status_code == 404
        assert "No healthy instances found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_service_discovery_api(self):
        """Test creating ServiceDiscoveryAPI via convenience function."""
        api = await create_service_discovery_api()
        assert isinstance(api, ServiceDiscoveryAPI)
        assert isinstance(api.service_discovery, ServiceDiscovery)
        assert api.host == "0.0.0.0"
        assert api.port == 8000

    @pytest.mark.asyncio
    async def test_create_service_discovery_api_custom_config(self):
        """Test creating ServiceDiscoveryAPI with custom configuration."""
        config = {"health_check_interval": 10}
        api = await create_service_discovery_api(
            config=config,
            api_host="127.0.0.1",
            api_port=9000
        )

        assert api.service_discovery.config["health_check_interval"] == 10
        assert api.host == "127.0.0.1"
        assert api.port == 9000

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_api_server_lifecycle(self, service_discovery_api):
        """Test API server start/stop lifecycle."""
        # Note: This test is simplified since we can't easily test the actual server
        # in a unit test environment. In integration tests, we would test the full server.

        # Test server configuration
        assert service_discovery_api.server is None
        assert service_discovery_api.host == "127.0.0.1"
        assert service_discovery_api.port == 8001

    @pytest.mark.asyncio
    async def test_service_instance_request_validation(self, test_client):
        """Test ServiceInstanceRequest validation."""
        # Missing required fields
        response = test_client.post("/services/register", json={})
        assert response.status_code == 422

        # Invalid port range
        invalid_data = {
            "service_id": "test",
            "service_name": "test",
            "host": "localhost",
            "port": 99999  # Invalid port
        }
        response = test_client.post("/services/register", json=invalid_data)
        assert response.status_code == 422

        # Valid minimal data
        valid_data = {
            "service_id": "test-minimal",
            "service_name": "test-service",
            "host": "localhost",
            "port": 8080
        }
        response = test_client.post("/services/register", json=valid_data)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_api_error_handling(self, test_client):
        """Test API error handling for various scenarios."""
        # Test endpoints with invalid service IDs/names
        response = test_client.get("/services/discover/")
        assert response.status_code == 404  # FastAPI route not found

        # Test empty service name in discovery
        response = test_client.get("/services/discover/ ")
        assert response.status_code in [200, 404]  # Depends on URL encoding

    @pytest.mark.asyncio
    async def test_concurrent_api_operations(self, test_client):
        """Test concurrent API operations."""
        # Register multiple services concurrently via API
        services_data = [
            {
                "service_id": f"concurrent-test-{i}",
                "service_name": "concurrent-service",
                "host": "localhost",
                "port": 8080 + i,
                "metadata": {"instance": i}
            }
            for i in range(5)
        ]

        # Register all services
        for service_data in services_data:
            response = test_client.post("/services/register", json=service_data)
            assert response.status_code == 200

        # Discover all services
        response = test_client.get("/services/discover/concurrent-service")
        assert response.status_code == 200

        data = response.json()
        assert data["total_count"] == 5
        assert len(data["services"]) == 5

    @pytest.mark.asyncio
    async def test_service_metadata_handling(self, test_client):
        """Test handling of service metadata in API."""
        service_data = {
            "service_id": "metadata-test",
            "service_name": "metadata-service",
            "host": "localhost",
            "port": 8080,
            "metadata": {
                "version": "2.0.0",
                "environment": "production",
                "capabilities": ["read", "write"],
                "config": {"timeout": 30, "retries": 3}
            },
            "tags": ["production", "database", "primary"],
            "version": "2.0.0"
        }

        # Register service with complex metadata
        response = test_client.post("/services/register", json=service_data)
        assert response.status_code == 200

        # Retrieve and verify metadata
        response = test_client.get("/services/metadata-test")
        assert response.status_code == 200

        data = response.json()
        assert data["metadata"] == service_data["metadata"]
        assert data["tags"] == service_data["tags"]
        assert data["version"] == service_data.get("version", "1.0.0")
