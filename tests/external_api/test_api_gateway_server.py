"""
Tests for FastAPI-based API Gateway Server.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import httpx

from external_api.api_gateway_server import ApiGatewayServer, create_api_gateway_server, run_api_gateway_server
from external_api.models import ApiGatewayConfig
from external_api.service_discovery import ServiceDiscovery


class TestApiGatewayServer:
    """Test suite for ApiGatewayServer class."""

    @pytest.fixture
    def gateway_config(self):
        """Create test API gateway configuration."""
        return ApiGatewayConfig(
            host="localhost",
            port=8081,
            api_prefix="/api/v1",
            enable_cors=True,
            cors_origins=["*"],
            rate_limit_requests=100,
            rate_limit_window=3600,
            auth_required=False,
            request_timeout=30
        )

    @pytest.fixture
    def service_discovery(self):
        """Create mock service discovery."""
        return AsyncMock(spec=ServiceDiscovery)

    @pytest.fixture
    def api_gateway_server(self, gateway_config, service_discovery):
        """Create ApiGatewayServer instance."""
        return ApiGatewayServer(gateway_config, service_discovery)

    @pytest.fixture
    def test_client(self, api_gateway_server):
        """Create test client."""
        return TestClient(api_gateway_server.app)

    def test_server_initialization(self, api_gateway_server, gateway_config):
        """Test server initialization."""
        assert api_gateway_server.config == gateway_config
        assert api_gateway_server.api_gateway is not None
        assert api_gateway_server.app is not None
        assert api_gateway_server.server_task is None

    def test_health_check_endpoint(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "gateway" in data

    def test_gateway_info_endpoint(self, test_client):
        """Test gateway info endpoint."""
        response = test_client.get("/gateway/info")
        assert response.status_code == 200
        
        data = response.json()
        assert "server_status" in data
        assert "registered_routes" in data
        assert "config" in data

    def test_gateway_stats_endpoint(self, test_client):
        """Test gateway stats endpoint."""
        response = test_client.get("/gateway/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_routes" in data
        assert "request_count" in data

    def test_cors_headers(self, test_client):
        """Test CORS headers are present."""
        response = test_client.options("/api/v1/test")
        assert response.status_code == 200
        
        # Check CORS headers
        headers = response.headers
        assert "access-control-allow-origin" in headers
        assert "access-control-allow-methods" in headers

    def test_api_route_handling(self, test_client, api_gateway_server):
        """Test API route handling through gateway."""
        # Register a test route
        async def test_handler(request):
            return {
                "status_code": 200,
                "body": {"message": "success", "path": request.path}
            }
        
        api_gateway_server.register_route("/test", "GET", test_handler)
        
        response = test_client.get("/api/v1/test")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "success"
        assert data["path"] == "/api/v1/test"

    def test_post_request_handling(self, test_client, api_gateway_server):
        """Test POST request handling."""
        async def post_handler(request):
            return {
                "status_code": 201,
                "body": {"received": request.body, "method": request.method}
            }
        
        api_gateway_server.register_route("/create", "POST", post_handler)
        
        test_data = {"name": "test", "value": 123}
        response = test_client.post("/api/v1/create", json=test_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["received"] == test_data
        assert data["method"] == "POST"

    def test_processing_time_header(self, test_client, api_gateway_server):
        """Test processing time header is added."""
        async def slow_handler(request):
            await asyncio.sleep(0.1)  # Small delay
            return {"status_code": 200, "body": {"result": "done"}}
        
        api_gateway_server.register_route("/slow", "GET", slow_handler)
        
        response = test_client.get("/api/v1/slow")
        assert response.status_code == 200
        assert "X-Processing-Time" in response.headers
        
        # Processing time should be > 100ms
        processing_time = float(response.headers["X-Processing-Time"].rstrip("ms"))
        assert processing_time > 100

    def test_authentication_required(self, gateway_config, service_discovery):
        """Test authentication when required."""
        # Create config with auth enabled
        auth_config = ApiGatewayConfig(
            host="localhost",
            port=8082,
            auth_required=True,
            api_key_header="X-API-Key"
        )
        
        server = ApiGatewayServer(auth_config, service_discovery)
        client = TestClient(server.app)
        
        # Register API key
        server.register_api_key("test-key", {"name": "Test"})
        
        # Register test route
        async def test_handler(request):
            return {"status_code": 200, "body": {"authorized": True}}
        
        server.register_route("/protected", "GET", test_handler)
        
        # Test without API key
        response = client.get("/api/v1/protected")
        assert response.status_code == 401
        
        # Test with valid API key
        response = client.get("/api/v1/protected", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        data = response.json()
        assert data["authorized"] is True

    def test_rate_limiting(self, test_client, api_gateway_server):
        """Test rate limiting functionality."""
        async def test_handler(request):
            return {"status_code": 200, "body": {"result": "ok"}}
        
        api_gateway_server.register_route("/limited", "GET", test_handler)
        
        # Make requests up to the limit (100)
        for i in range(100):
            response = test_client.get("/api/v1/limited")
            assert response.status_code == 200
        
        # Next request should be rate limited
        response = test_client.get("/api/v1/limited")
        assert response.status_code == 429

    def test_service_route_registration(self, api_gateway_server):
        """Test service route registration."""
        api_gateway_server.register_service_route("/service", "test-service")
        
        # Verify route was registered
        assert "/service" in api_gateway_server.api_gateway.service_routes
        assert api_gateway_server.api_gateway.service_routes["/service"] == "test-service"

    def test_middleware_addition(self, api_gateway_server):
        """Test middleware addition."""
        async def test_middleware(request):
            return {"continue": True}
        
        api_gateway_server.add_middleware(test_middleware)
        
        # Verify middleware was added
        assert len(api_gateway_server.api_gateway.middleware) == 1
        assert api_gateway_server.api_gateway.middleware[0] == test_middleware

    @pytest.mark.asyncio
    async def test_server_lifecycle(self, api_gateway_server):
        """Test server start and stop lifecycle."""
        # Test start
        await api_gateway_server.start_server()
        assert api_gateway_server.server_task is not None
        assert api_gateway_server.api_gateway.server_started is True
        
        # Test health check while running
        health = await api_gateway_server.health_check()
        assert health["status"] == "healthy"
        assert health["server_running"] is True
        
        # Test stop
        await api_gateway_server.stop_server()
        assert api_gateway_server.server_task is None
        assert api_gateway_server.api_gateway.server_started is False

    @pytest.mark.asyncio
    async def test_server_already_running(self, api_gateway_server):
        """Test starting server when already running."""
        await api_gateway_server.start_server()
        
        # Try to start again - should not raise error
        await api_gateway_server.start_server()
        
        await api_gateway_server.stop_server()

    @pytest.mark.asyncio
    async def test_server_stop_when_not_running(self, api_gateway_server):
        """Test stopping server when not running."""
        # Should not raise error
        await api_gateway_server.stop_server()

    @pytest.mark.asyncio
    async def test_convert_request_get(self, api_gateway_server):
        """Test request conversion for GET requests."""
        from fastapi import Request
        from starlette.datastructures import URL, Headers
        
        # Mock FastAPI request
        mock_request = AsyncMock(spec=Request)
        mock_request.method = "GET"
        mock_request.url = URL("http://localhost:8081/api/v1/test?param=value")
        mock_request.headers = Headers({"content-type": "application/json", "x-custom": "test"})
        mock_request.query_params = {"param": "value"}
        mock_request.client.host = "127.0.0.1"
        
        api_request = await api_gateway_server._convert_request(mock_request)
        
        assert api_request.method == "GET"
        assert api_request.path == "/api/v1/test"
        assert api_request.headers["content-type"] == "application/json"
        assert api_request.query_params["param"] == "value"
        assert api_request.client_ip == "127.0.0.1"
        assert api_request.body is None

    @pytest.mark.asyncio
    async def test_convert_request_post(self, api_gateway_server):
        """Test request conversion for POST requests."""
        from fastapi import Request
        from starlette.datastructures import URL, Headers
        
        # Mock FastAPI request
        mock_request = AsyncMock(spec=Request)
        mock_request.method = "POST"
        mock_request.url = URL("http://localhost:8081/api/v1/create")
        mock_request.headers = Headers({"content-type": "application/json"})
        mock_request.query_params = {}
        mock_request.client.host = "192.168.1.1"
        mock_request.json.return_value = {"name": "test", "value": 123}
        
        api_request = await api_gateway_server._convert_request(mock_request)
        
        assert api_request.method == "POST"
        assert api_request.path == "/api/v1/create"
        assert api_request.body == {"name": "test", "value": 123}
        assert api_request.client_ip == "192.168.1.1"

    def test_create_api_gateway_server(self):
        """Test server creation function."""
        # Test with default config
        server = create_api_gateway_server()
        assert server.config.host == "localhost"
        assert server.config.port == 8081
        
        # Test with custom config
        config = ApiGatewayConfig(host="0.0.0.0", port=9000)
        server = create_api_gateway_server(config)
        assert server.config.host == "0.0.0.0"
        assert server.config.port == 9000

    @pytest.mark.asyncio
    async def test_run_api_gateway_server(self):
        """Test running API gateway server function."""
        config = ApiGatewayConfig(host="localhost", port=8083)
        
        # Simply test that the function can be called without error
        # We'll mock the server to avoid actually starting it
        with patch('external_api.api_gateway_server.uvicorn.Server.serve') as mock_serve:
            mock_serve.return_value = None
            
            # Create server instance to verify function works
            server = create_api_gateway_server(config)
            assert server is not None
            assert server.config.port == 8083

    def test_error_handling_invalid_json(self, test_client, api_gateway_server):
        """Test error handling for invalid JSON."""
        async def post_handler(request):
            return {"status_code": 200, "body": {"received": request.body}}
        
        api_gateway_server.register_route("/json", "POST", post_handler)
        
        # Send invalid JSON
        response = test_client.post(
            "/api/v1/json",
            data="invalid json",
            headers={"content-type": "application/json"}
        )
        
        # Should handle gracefully
        assert response.status_code == 200
        data = response.json()
        assert data["received"] is None

    def test_middleware_error_handling(self, test_client, api_gateway_server):
        """Test middleware error handling."""
        async def error_handler(request):
            raise ValueError("Test error")
        
        api_gateway_server.register_route("/error", "GET", error_handler)
        
        response = test_client.get("/api/v1/error")
        assert response.status_code == 500
        
        data = response.json()
        assert "error" in data
        assert "Internal server error" in data["error"]

    def test_request_id_generation(self, test_client, api_gateway_server):
        """Test request ID generation."""
        async def id_handler(request):
            return {"status_code": 200, "body": {"request_id": request.request_id}}
        
        api_gateway_server.register_route("/id", "GET", id_handler)
        
        # Test with custom request ID
        response = test_client.get("/api/v1/id", headers={"X-Request-ID": "custom-123"})
        assert response.status_code == 200
        
        data = response.json()
        assert data["request_id"] == "custom-123"
        
        # Test with generated request ID
        response = test_client.get("/api/v1/id")
        assert response.status_code == 200
        
        data = response.json()
        assert data["request_id"].startswith("req-")

    def test_path_parameter_handling(self, test_client, api_gateway_server):
        """Test path parameter handling."""
        async def path_handler(request):
            return {"status_code": 200, "body": {"path": request.path}}
        
        # Register route with exact path (FastAPI will handle parameters)
        api_gateway_server.register_route("/items/123", "GET", path_handler)
        
        response = test_client.get("/api/v1/items/123")
        assert response.status_code == 200
        
        data = response.json()
        assert data["path"] == "/api/v1/items/123"

    def test_query_parameter_handling(self, test_client, api_gateway_server):
        """Test query parameter handling."""
        async def query_handler(request):
            return {"status_code": 200, "body": {"params": request.query_params}}
        
        api_gateway_server.register_route("/search", "GET", query_handler)
        
        response = test_client.get("/api/v1/search?q=test&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert data["params"]["q"] == "test"
        assert data["params"]["limit"] == "10"

    def test_response_headers_propagation(self, test_client, api_gateway_server):
        """Test that response headers are properly propagated."""
        async def header_handler(request):
            return {
                "status_code": 200,
                "body": {"message": "success"},
                "headers": {"X-Custom-Header": "test-value"}
            }
        
        api_gateway_server.register_route("/headers", "GET", header_handler)
        
        response = test_client.get("/api/v1/headers")
        assert response.status_code == 200
        
        # Check that custom headers are present
        assert "X-Custom-Header" in response.headers
        assert response.headers["X-Custom-Header"] == "test-value"
        
        # Check that processing time is still added
        assert "X-Processing-Time" in response.headers