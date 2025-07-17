"""
Integration tests for Service Discovery system.
Tests the complete integration between Service Discovery, API Gateway, and client libraries.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from external_api.service_discovery import ServiceDiscovery, ServiceInstance, ServiceStatus
from external_api.service_discovery_api import ServiceDiscoveryAPI, create_service_discovery_api
from external_api.api_gateway import ApiGateway
from external_api.models import ApiGatewayConfig, ApiRequest, ApiResponse
from external_api.client_generators import ClientLibraryFactory, PythonClientGenerator, JavaScriptClientGenerator


class TestServiceDiscoveryIntegration:
    """Integration test suite for Service Discovery system."""

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
    def api_gateway_config(self):
        """Create API Gateway configuration."""
        return ApiGatewayConfig(
            host="127.0.0.1",
            port=8080,
            api_prefix="/api/v1",
            auth_required=False,
            enable_cors=True,
            cors_origins=["*"],
            rate_limit_requests=100,
            rate_limit_window=60,
            request_timeout=30
        )

    @pytest.fixture
    def api_gateway(self, api_gateway_config, service_discovery):
        """Create API Gateway with service discovery integration."""
        return ApiGateway(api_gateway_config, service_discovery)

    @pytest.fixture
    def test_client_api(self, service_discovery_api):
        """Create test client for Service Discovery API."""
        return TestClient(service_discovery_api.app)

    @pytest.fixture
    def sample_services(self):
        """Sample service instances for testing."""
        return [
            ServiceInstance(
                service_id="user-service-001",
                service_name="user-service",
                host="localhost",
                port=8081,
                metadata={"version": "1.0.0", "environment": "test"},
                health_check_url="http://localhost:8081/health",
                tags=["web", "api", "users"],
                version="1.0.0"
            ),
            ServiceInstance(
                service_id="order-service-001",
                service_name="order-service",
                host="localhost",
                port=8082,
                metadata={"version": "2.0.0", "environment": "test"},
                health_check_url="http://localhost:8082/health",
                tags=["web", "api", "orders"],
                version="2.0.0"
            ),
            ServiceInstance(
                service_id="notification-service-001",
                service_name="notification-service",
                host="localhost",
                port=8083,
                metadata={"version": "1.5.0", "environment": "test"},
                tags=["background", "notifications"],  # No health check URL
                version="1.5.0"
            )
        ]

    @pytest.mark.asyncio
    async def test_end_to_end_service_lifecycle(self, service_discovery, sample_services):
        """Test complete service lifecycle from registration to cleanup."""
        await service_discovery.start()

        try:
            # Register multiple services
            for service in sample_services:
                result = await service_discovery.register_service(service)
                assert result is True

            # Verify all services are registered
            all_services = await service_discovery.list_services()
            assert len(all_services) == 3
            assert "user-service" in all_services
            assert "order-service" in all_services
            assert "notification-service" in all_services

            # Test service discovery
            user_services = await service_discovery.discover_services("user-service", healthy_only=False)
            assert len(user_services) == 1
            assert user_services[0].service_id == "user-service-001"

            # Test service status (newly registered services start in 'starting' status)
            service_status = await service_discovery.get_service_status("user-service-001")
            assert service_status is not None

            # Update service to healthy status for testing healthy instance retrieval
            registration = service_discovery.services.get("user-service-001")
            if registration:
                registration.status = ServiceStatus.HEALTHY

            # Test healthy instance retrieval
            healthy_user_service = await service_discovery.get_healthy_instance("user-service")
            assert healthy_user_service is not None
            assert healthy_user_service.service_id == "user-service-001"

            # Test heartbeat functionality
            heartbeat_result = await service_discovery.heartbeat("user-service-001")
            assert heartbeat_result is True

            # Test service deregistration
            deregister_result = await service_discovery.deregister_service("user-service-001")
            assert deregister_result is True

            # Verify service is removed
            user_services_after = await service_discovery.discover_services("user-service")
            assert len(user_services_after) == 0

        finally:
            await service_discovery.stop()

    @pytest.mark.asyncio
    async def test_api_gateway_service_routing(self, api_gateway, service_discovery, sample_services):
        """Test API Gateway routing to services via service discovery."""
        await service_discovery.start()

        try:
            # Register services
            for service in sample_services:
                await service_discovery.register_service(service)

            # Register service routes in API Gateway
            api_gateway.register_service_route("/api/v1/users", "user-service")
            api_gateway.register_service_route("/api/v1/orders", "order-service")

            # Test service route discovery
            user_service_name = api_gateway._find_service_route("/api/v1/users/123")
            assert user_service_name == "user-service"

            order_service_name = api_gateway._find_service_route("/api/v1/orders/456")
            assert order_service_name == "order-service"

            # Test service instance retrieval
            user_instance = await api_gateway.get_service_instance("user-service")
            assert user_instance is not None
            assert user_instance.service_name == "user-service"

            # Test unregistering service routes
            result = api_gateway.unregister_service_route("/api/v1/users")
            assert result is True

            # Verify route is removed
            no_service = api_gateway._find_service_route("/api/v1/users/123")
            assert no_service is None

        finally:
            await service_discovery.stop()

    @pytest.mark.asyncio
    async def test_rest_api_complete_workflow(self, test_client_api, sample_services):
        """Test complete REST API workflow."""
        # Test system info before registration
        response = test_client_api.get("/system/info")
        assert response.status_code == 200
        initial_info = response.json()
        initial_total = initial_info["total_instances"]

        registered_services = []

        try:
            # Register all services via API
            for service in sample_services:
                service_data = {
                    "service_id": service.service_id,
                    "service_name": service.service_name,
                    "host": service.host,
                    "port": service.port,
                    "metadata": service.metadata,
                    "health_check_url": service.health_check_url,
                    "tags": service.tags,
                    "version": service.version
                }

                response = test_client_api.post("/services/register", json=service_data)
                assert response.status_code == 200
                registered_services.append(service.service_id)

            # Verify system info updated
            response = test_client_api.get("/system/info")
            assert response.status_code == 200
            info = response.json()
            assert info["total_instances"] == initial_total + 3
            assert info["unique_services"] == 3
            assert "user-service" in info["service_names"]
            assert "order-service" in info["service_names"]
            assert "notification-service" in info["service_names"]

            # Test service discovery via API
            response = test_client_api.get("/services/discover/user-service")
            assert response.status_code == 200
            discovery_data = response.json()
            assert discovery_data["total_count"] == 1
            assert len(discovery_data["services"]) == 1

            user_service = discovery_data["services"][0]
            assert user_service["service_id"] == "user-service-001"
            assert user_service["service_name"] == "user-service"
            assert user_service["host"] == "localhost"
            assert user_service["port"] == 8081

            # Test getting service by ID via API
            response = test_client_api.get("/services/user-service-001")
            assert response.status_code == 200
            service_data = response.json()
            assert service_data["service_id"] == "user-service-001"
            assert service_data["service_name"] == "user-service"

            # Test heartbeat via API
            response = test_client_api.post("/services/user-service-001/heartbeat")
            assert response.status_code == 200
            heartbeat_data = response.json()
            assert heartbeat_data["message"] == "Heartbeat received"

            # Test listing all services via API
            response = test_client_api.get("/services")
            assert response.status_code == 200
            all_services = response.json()
            assert "user-service" in all_services
            assert "order-service" in all_services
            assert "notification-service" in all_services

            # Test getting healthy instance via API
            response = test_client_api.get("/services/healthy/notification-service")
            assert response.status_code == 200  # Should work since no health check URL means healthy

        finally:
            # Clean up: deregister all services
            for service_id in registered_services:
                response = test_client_api.delete(f"/services/{service_id}")
                # Don't assert success here as some might already be cleaned up

    @patch('aiohttp.ClientSession')
    @pytest.mark.asyncio
    async def test_real_health_checks(self, mock_session, service_discovery):
        """Test real HTTP health checks implementation."""
        await service_discovery.start()

        try:
            # Mock successful health check
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.__aenter__.return_value = mock_response
            mock_session.return_value.__aenter__.return_value.get.return_value = mock_response

            service = ServiceInstance(
                service_id="health-test-001",
                service_name="health-test",
                host="localhost",
                port=8080,
                metadata={},
                health_check_url="http://localhost:8080/health"
            )

            # Test health check directly
            is_healthy = await service_discovery._perform_health_check(service)
            assert is_healthy is True

            # Mock failed health check
            mock_response.status = 500
            is_healthy = await service_discovery._perform_health_check(service)
            assert is_healthy is False

            # Mock timeout
            mock_session.return_value.__aenter__.return_value.get.side_effect = asyncio.TimeoutError()
            is_healthy = await service_discovery._perform_health_check(service)
            assert is_healthy is False

        finally:
            await service_discovery.stop()

    def test_client_library_generation(self):
        """Test multi-language client library generation."""
        api_endpoint = "http://localhost:8000"
        service_name = "test-service"

        # Test Python client generation
        python_generator = PythonClientGenerator()
        python_client = python_generator.generate_client(api_endpoint, service_name)

        assert "class TestServiceClient:" in python_client
        assert "async def discover_instances" in python_client
        assert "async def get_healthy_instance" in python_client
        assert "async def register_instance" in python_client
        assert "http://localhost:8000" in python_client

        # Test JavaScript client generation
        js_generator = JavaScriptClientGenerator()
        js_client = js_generator.generate_client(api_endpoint, service_name)

        assert "class TestServiceClient {" in js_client
        assert "async discoverInstances" in js_client
        assert "async getHealthyInstance" in js_client
        assert "async registerInstance" in js_client
        assert "http://localhost:8000" in js_client

        # Test factory method
        python_client_factory = ClientLibraryFactory.generate_client_library(
            "python", api_endpoint, service_name
        )
        assert "TestServiceClient" in python_client_factory

        js_client_factory = ClientLibraryFactory.generate_client_library(
            "javascript", api_endpoint, service_name
        )
        assert "TestServiceClient" in js_client_factory

        # Test supported languages
        supported = ClientLibraryFactory.get_supported_languages()
        assert "python" in supported
        assert "javascript" in supported
        assert "js" in supported
        assert "node" in supported

    def test_client_library_factory_error_handling(self):
        """Test client library factory error handling."""
        with pytest.raises(ValueError, match="Unsupported language"):
            ClientLibraryFactory.get_generator("unsupported-language")

        with pytest.raises(ValueError, match="Unsupported language"):
            ClientLibraryFactory.generate_client_library(
                "unsupported", "http://localhost:8000", "test-service"
            )

    @pytest.mark.asyncio
    async def test_service_discovery_api_creation(self):
        """Test ServiceDiscoveryAPI creation via convenience function."""
        # Test with default configuration
        api = await create_service_discovery_api()
        assert isinstance(api, ServiceDiscoveryAPI)
        assert api.host == "0.0.0.0"
        assert api.port == 8000

        # Test with custom configuration
        config = {"health_check_interval": 5}
        api_custom = await create_service_discovery_api(
            config=config,
            api_host="127.0.0.1",
            api_port=9000
        )
        assert api_custom.host == "127.0.0.1"
        assert api_custom.port == 9000
        assert api_custom.service_discovery.config["health_check_interval"] == 5

    @pytest.mark.asyncio
    async def test_service_watcher_integration(self, service_discovery, sample_services):
        """Test service watcher functionality in integration."""
        await service_discovery.start()

        events = []

        async def test_watcher(event, instance):
            events.append((event, instance.service_id))

        try:
            # Add watcher
            await service_discovery.watch_service("user-service", test_watcher)

            # Register service (should trigger watcher)
            user_service = sample_services[0]  # user-service
            await service_discovery.register_service(user_service)

            # Send heartbeat (should trigger watcher if service was unhealthy)
            registration = service_discovery.services["user-service-001"]
            registration.status = ServiceStatus.UNHEALTHY  # Simulate unhealthy state

            await service_discovery.heartbeat("user-service-001")

            # Deregister service (should trigger watcher)
            await service_discovery.deregister_service("user-service-001")

            # Check events
            assert len(events) >= 2  # At least registration and deregistration
            assert ("registered", "user-service-001") in events
            assert ("deregistered", "user-service-001") in events

        finally:
            await service_discovery.stop()

    @pytest.mark.asyncio
    async def test_concurrent_operations_integration(self, service_discovery, test_client_api):
        """Test concurrent operations across the entire system."""
        await service_discovery.start()

        try:
            # Create multiple service instances
            services_data = []
            for i in range(10):
                service_data = {
                    "service_id": f"concurrent-service-{i:03d}",
                    "service_name": "concurrent-service",
                    "host": "localhost",
                    "port": 8080 + i,
                    "metadata": {"instance": i, "batch": "concurrent-test"},
                    "tags": ["test", "concurrent"],
                    "version": "1.0.0"
                }
                services_data.append(service_data)

            # Register all services concurrently via API
            registration_tasks = []
            for service_data in services_data:
                # Note: TestClient doesn't support async, so we simulate concurrent registration
                response = test_client_api.post("/services/register", json=service_data)
                assert response.status_code == 200

            # Verify all services are registered
            response = test_client_api.get("/services/discover/concurrent-service")
            assert response.status_code == 200
            discovery_data = response.json()
            assert discovery_data["total_count"] == 10

            # Test concurrent heartbeats
            heartbeat_tasks = []
            for i in range(10):
                service_id = f"concurrent-service-{i:03d}"
                response = test_client_api.post(f"/services/{service_id}/heartbeat")
                assert response.status_code == 200

            # Test concurrent discovery
            discovery_tasks = []
            for _ in range(5):
                response = test_client_api.get("/services/discover/concurrent-service")
                assert response.status_code == 200
                data = response.json()
                assert data["total_count"] == 10

            # Clean up: deregister all services
            for i in range(10):
                service_id = f"concurrent-service-{i:03d}"
                response = test_client_api.delete(f"/services/{service_id}")
                assert response.status_code == 200

        finally:
            await service_discovery.stop()

    @patch('aiohttp.ClientSession')
    @pytest.mark.asyncio
    async def test_api_gateway_service_proxying(self, mock_session, api_gateway, service_discovery, sample_services):
        """Test API Gateway proxying requests to discovered services."""
        await service_discovery.start()

        try:
            # Register service
            user_service = sample_services[0]  # user-service
            await service_discovery.register_service(user_service)

            # Mock HTTP response from target service
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.text.return_value = '{"message": "Hello from user service"}'
            mock_response.__aenter__.return_value = mock_response

            mock_session.return_value.__aenter__.return_value.request.return_value = mock_response

            # Create API request
            api_request = ApiRequest(
                request_id="test-request-001",
                method="GET",
                path="/api/v1/users/123",
                headers={"Content-Type": "application/json"},
                query_params={},
                body=None,
                client_ip="127.0.0.1"
            )

            # Test proxying to service
            result = await api_gateway.proxy_to_service(api_request, "user-service")

            assert result["status_code"] == 200
            assert result["body"]["message"] == "Hello from user service"

            # Verify the correct URL was called
            mock_session.return_value.__aenter__.return_value.request.assert_called_once()
            call_args = mock_session.return_value.__aenter__.return_value.request.call_args
            assert call_args[1]["url"] == "http://localhost:8081/api/v1/users/123"
            assert call_args[1]["method"] == "GET"

        finally:
            await service_discovery.stop()

    @pytest.mark.asyncio
    async def test_error_scenarios_integration(self, service_discovery, test_client_api):
        """Test error scenarios across the integrated system."""
        await service_discovery.start()

        try:
            # Test registering service with invalid data via API
            invalid_service = {
                "service_id": "invalid-service",
                "service_name": "invalid",
                "host": "localhost",
                "port": 99999  # Invalid port
            }

            response = test_client_api.post("/services/register", json=invalid_service)
            assert response.status_code == 422  # Validation error

            # Test operations on non-existent services
            response = test_client_api.get("/services/nonexistent-service")
            assert response.status_code == 404

            response = test_client_api.post("/services/nonexistent-service/heartbeat")
            assert response.status_code == 404

            response = test_client_api.delete("/services/nonexistent-service")
            assert response.status_code == 404

            response = test_client_api.get("/services/discover/nonexistent-service")
            assert response.status_code == 200  # Returns empty list
            data = response.json()
            assert data["total_count"] == 0

            response = test_client_api.get("/services/healthy/nonexistent-service")
            assert response.status_code == 404

        finally:
            await service_discovery.stop()

    @pytest.mark.asyncio
    async def test_system_metrics_and_monitoring(self, service_discovery, test_client_api, sample_services):
        """Test system metrics and monitoring capabilities."""
        await service_discovery.start()

        try:
            # Initial system state
            response = test_client_api.get("/system/info")
            assert response.status_code == 200
            initial_info = response.json()

            # Register services with different health states
            healthy_service = {
                "service_id": "healthy-service-001",
                "service_name": "healthy-service",
                "host": "localhost",
                "port": 8080,
                "metadata": {"type": "healthy"},
                "version": "1.0.0"
                # No health_check_url means it's considered healthy
            }

            unhealthy_service = {
                "service_id": "unhealthy-service-001",
                "service_name": "unhealthy-service",
                "host": "localhost",
                "port": 8081,
                "metadata": {"type": "unhealthy"},
                "health_check_url": "http://localhost:8081/health",  # Will fail health check
                "version": "1.0.0"
            }

            # Register services
            response = test_client_api.post("/services/register", json=healthy_service)
            assert response.status_code == 200

            response = test_client_api.post("/services/register", json=unhealthy_service)
            assert response.status_code == 200

            # Check updated system info
            response = test_client_api.get("/system/info")
            assert response.status_code == 200
            updated_info = response.json()

            assert updated_info["total_instances"] == initial_info["total_instances"] + 2
            assert updated_info["unique_services"] >= 2
            assert "healthy-service" in updated_info["service_names"]
            assert "unhealthy-service" in updated_info["service_names"]

            # Test service status monitoring
            response = test_client_api.get("/services/healthy-service-001/status")
            assert response.status_code == 200
            status_data = response.json()
            assert status_data["service_id"] == "healthy-service-001"
            assert "status" in status_data

            # Test discovery with health filtering
            response = test_client_api.get("/services/discover/healthy-service?healthy_only=true")
            assert response.status_code == 200
            healthy_discovery = response.json()
            assert healthy_discovery["total_count"] >= 1

            # Clean up
            test_client_api.delete("/services/healthy-service-001")
            test_client_api.delete("/services/unhealthy-service-001")

        finally:
            await service_discovery.stop()
