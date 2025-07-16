"""
Tests for ApiGateway component.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

from external_api.api_gateway import ApiGateway
from external_api.models import (
    ApiGatewayConfig,
    ApiRequest,
    ApiResponse
)


class TestApiGateway:
    """Test suite for ApiGateway class."""
    
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
    def gateway_config_with_auth(self):
        """Create test API gateway configuration with auth enabled."""
        return ApiGatewayConfig(
            host="localhost",
            port=8081,
            api_prefix="/api/v1",
            auth_required=True,
            api_key_header="X-API-Key"
        )
    
    @pytest.fixture
    def api_gateway(self, gateway_config):
        """Create ApiGateway instance."""
        return ApiGateway(gateway_config)
    
    @pytest.fixture
    def auth_gateway(self, gateway_config_with_auth):
        """Create ApiGateway instance with auth."""
        return ApiGateway(gateway_config_with_auth)
    
    @pytest.fixture
    def sample_request(self):
        """Create sample API request."""
        return ApiRequest(
            method="GET",
            path="/api/v1/tasks",
            headers={"Content-Type": "application/json"},
            query_params={"status": "active"},
            body=None,
            timestamp=datetime.now(),
            request_id="req-123",
            client_ip="127.0.0.1"
        )
    
    @pytest.mark.asyncio
    async def test_gateway_initialization(self, api_gateway, gateway_config):
        """Test API gateway initialization."""
        assert api_gateway.config == gateway_config
        assert api_gateway.routes == {}
        assert api_gateway.middleware == []
        assert api_gateway.rate_limiter == {}
        assert api_gateway.api_keys == {}
        assert not api_gateway.server_started
        assert api_gateway._request_count == 0
    
    @pytest.mark.asyncio
    async def test_start_stop_server(self, api_gateway):
        """Test server start and stop functionality."""
        # Test start
        await api_gateway.start_server()
        assert api_gateway.server_started
        
        # Test start when already started
        await api_gateway.start_server()  # Should not raise error
        assert api_gateway.server_started
        
        # Test stop
        await api_gateway.stop_server()
        assert not api_gateway.server_started
        
        # Test stop when not running
        await api_gateway.stop_server()  # Should not raise error
        assert not api_gateway.server_started
    
    @pytest.mark.asyncio
    async def test_register_route(self, api_gateway):
        """Test route registration."""
        async def test_handler(request):
            return {"status_code": 200, "body": {"result": "success"}}
        
        # Test successful registration
        api_gateway.register_route("/test", "GET", test_handler)
        assert "/test" in api_gateway.routes
        assert "GET" in api_gateway.routes["/test"]
        assert api_gateway.routes["/test"]["GET"] == test_handler
        
        # Test non-async handler rejection
        def sync_handler(request):
            return {"status_code": 200, "body": {"result": "success"}}
        
        with pytest.raises(ValueError, match="Handler must be an async function"):
            api_gateway.register_route("/sync", "GET", sync_handler)
    
    @pytest.mark.asyncio
    async def test_unregister_route(self, api_gateway):
        """Test route unregistration."""
        async def test_handler(request):
            return {"status_code": 200, "body": {"result": "success"}}
        
        # Register route first
        api_gateway.register_route("/test", "GET", test_handler)
        api_gateway.register_route("/test", "POST", test_handler)
        
        # Test successful unregistration
        result = api_gateway.unregister_route("/test", "GET")
        assert result is True
        assert "GET" not in api_gateway.routes["/test"]
        assert "POST" in api_gateway.routes["/test"]  # Should still exist
        
        # Unregister last method - should remove path
        result = api_gateway.unregister_route("/test", "POST")
        assert result is True
        assert "/test" not in api_gateway.routes
        
        # Test unregistration of non-existent route
        result = api_gateway.unregister_route("/non_existent", "GET")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_add_middleware(self, api_gateway):
        """Test middleware addition."""
        async def test_middleware(request):
            return {"continue": True}
        
        # Test successful addition
        api_gateway.add_middleware(test_middleware)
        assert len(api_gateway.middleware) == 1
        assert api_gateway.middleware[0] == test_middleware
        
        # Test non-async middleware rejection
        def sync_middleware(request):
            return {"continue": True}
        
        with pytest.raises(ValueError, match="Middleware must be an async function"):
            api_gateway.add_middleware(sync_middleware)
    
    @pytest.mark.asyncio
    async def test_register_api_key(self, auth_gateway):
        """Test API key registration."""
        metadata = {
            "name": "Test API",
            "permissions": ["read", "write"],
            "rate_limit": 1000
        }
        
        auth_gateway.register_api_key("test-key-123", metadata)
        
        assert "test-key-123" in auth_gateway.api_keys
        key_data = auth_gateway.api_keys["test-key-123"]
        assert key_data["name"] == "Test API"
        assert key_data["permissions"] == ["read", "write"]
        assert "created_at" in key_data
        assert key_data["request_count"] == 0
    
    @pytest.mark.asyncio
    async def test_handle_request_success(self, api_gateway, sample_request):
        """Test successful request handling."""
        async def test_handler(request):
            return {
                "status_code": 200,
                "body": {"message": "success", "path": request.path}
            }
        
        api_gateway.register_route("/tasks", "GET", test_handler)
        
        response = await api_gateway.handle_request(sample_request)
        
        assert isinstance(response, ApiResponse)
        assert response.status_code == 200
        assert response.body["message"] == "success"
        assert response.request_id == sample_request.request_id
        assert response.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_handle_request_route_not_found(self, api_gateway, sample_request):
        """Test handling of non-existent routes."""
        response = await api_gateway.handle_request(sample_request)
        
        assert response.status_code == 404
        assert "Route not found" in response.body["error"]
    
    @pytest.mark.asyncio
    async def test_handle_request_authentication_required(self, auth_gateway, sample_request):
        """Test authentication when required."""
        # No API key provided
        response = await auth_gateway.handle_request(sample_request)
        assert response.status_code == 401
        assert "Missing X-API-Key header" in response.body["error"]
        
        # Invalid API key
        sample_request.headers["X-API-Key"] = "invalid-key"
        response = await auth_gateway.handle_request(sample_request)
        assert response.status_code == 401
        assert "Invalid API key" in response.body["error"]
        
        # Valid API key
        auth_gateway.register_api_key("valid-key", {"name": "Test"})
        sample_request.headers["X-API-Key"] = "valid-key"
        
        async def test_handler(request):
            return {"status_code": 200, "body": {"authorized": True}}
        
        auth_gateway.register_route("/tasks", "GET", test_handler)
        response = await auth_gateway.handle_request(sample_request)
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_handle_request_rate_limiting(self, api_gateway, sample_request):
        """Test rate limiting functionality."""
        async def test_handler(request):
            return {"status_code": 200, "body": {"result": "ok"}}
        
        api_gateway.register_route("/tasks", "GET", test_handler)
        
        # Make requests up to limit
        for _ in range(100):  # config.rate_limit_requests = 100
            response = await api_gateway.handle_request(sample_request)
            assert response.status_code == 200
        
        # Next request should be rate limited
        response = await api_gateway.handle_request(sample_request)
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.body["error"]
    
    @pytest.mark.asyncio
    async def test_handle_request_cors_preflight(self, api_gateway):
        """Test CORS preflight handling."""
        options_request = ApiRequest(
            method="OPTIONS",
            path="/api/v1/tasks",
            headers={},
            query_params={},
            body=None,
            timestamp=datetime.now(),
            request_id="options-123",
            client_ip="127.0.0.1"
        )
        
        response = await api_gateway.handle_request(options_request)
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
    
    @pytest.mark.asyncio
    async def test_handle_request_timeout(self, api_gateway, sample_request):
        """Test request timeout handling."""
        async def slow_handler(request):
            await asyncio.sleep(35)  # Longer than config.request_timeout (30)
            return {"status_code": 200, "body": {"result": "done"}}
        
        api_gateway.register_route("/tasks", "GET", slow_handler)
        
        response = await api_gateway.handle_request(sample_request)
        assert response.status_code == 504
        assert "Request timeout" in response.body["error"]
    
    @pytest.mark.asyncio
    async def test_handle_request_handler_error(self, api_gateway, sample_request):
        """Test handler error handling."""
        async def error_handler(request):
            raise ValueError("Test error")
        
        api_gateway.register_route("/tasks", "GET", error_handler)
        
        response = await api_gateway.handle_request(sample_request)
        assert response.status_code == 500
        assert "Internal server error" in response.body["error"]
    
    @pytest.mark.asyncio
    async def test_middleware_processing(self, api_gateway, sample_request):
        """Test middleware processing."""
        middleware_calls = []
        
        async def middleware1(request):
            middleware_calls.append("middleware1")
            return {"continue": True}
        
        async def middleware2(request):
            middleware_calls.append("middleware2")
            return {"continue": True}
        
        async def stopping_middleware(request):
            middleware_calls.append("stopping")
            return {
                "stop_processing": True,
                "status_code": 403,
                "body": {"error": "Forbidden"}
            }
        
        async def test_handler(request):
            middleware_calls.append("handler")
            return {"status_code": 200, "body": {"result": "success"}}
        
        # Test normal middleware flow
        api_gateway.add_middleware(middleware1)
        api_gateway.add_middleware(middleware2)
        api_gateway.register_route("/tasks", "GET", test_handler)
        
        response = await api_gateway.handle_request(sample_request)
        assert response.status_code == 200
        assert middleware_calls == ["middleware1", "middleware2", "handler"]
        
        # Test stopping middleware
        middleware_calls.clear()
        api_gateway.add_middleware(stopping_middleware)
        
        response = await api_gateway.handle_request(sample_request)
        assert response.status_code == 403
        assert middleware_calls == ["middleware1", "middleware2", "stopping"]
    
    @pytest.mark.asyncio
    async def test_find_handler(self, api_gateway):
        """Test route handler finding logic."""
        async def test_handler(request):
            return {"status_code": 200}
        
        api_gateway.register_route("/tasks", "GET", test_handler)
        
        # Test with API prefix
        handler = api_gateway._find_handler("/api/v1/tasks", "GET")
        assert handler == test_handler
        
        # Test without API prefix
        handler = api_gateway._find_handler("/tasks", "GET")
        assert handler == test_handler
        
        # Test non-existent route
        handler = api_gateway._find_handler("/non-existent", "GET")
        assert handler is None
        
        # Test wrong method
        handler = api_gateway._find_handler("/tasks", "POST")
        assert handler is None
    
    @pytest.mark.asyncio
    async def test_get_gateway_info(self, api_gateway):
        """Test gateway information retrieval."""
        async def handler1(request):
            return {}
        
        async def handler2(request):
            return {}
        
        api_gateway.register_route("/route1", "GET", handler1)
        api_gateway.register_route("/route1", "POST", handler2)
        api_gateway.register_route("/route2", "GET", handler1)
        
        info = api_gateway.get_gateway_info()
        
        assert info["server_status"] == "stopped"
        assert len(info["registered_routes"]) == 2
        assert set(info["registered_routes"]["/route1"]) == {"GET", "POST"}
        assert info["registered_routes"]["/route2"] == ["GET"]
        assert info["middleware_count"] == 0
        assert info["total_requests"] == 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, api_gateway):
        """Test health check functionality."""
        # Health check when stopped
        health = await api_gateway.health_check()
        assert health["status"] == "unhealthy"
        assert health["server_running"] is False
        
        # Start server and check again
        await api_gateway.start_server()
        health = await api_gateway.health_check()
        assert health["status"] == "healthy"
        assert health["server_running"] is True
        assert "timestamp" in health
    
    @pytest.mark.asyncio
    async def test_api_gateway_config_validation(self):
        """Test API gateway configuration validation."""
        # Test invalid port
        with pytest.raises(ValueError, match="Port must be between 1-65535"):
            ApiGatewayConfig(port=0)
        
        with pytest.raises(ValueError, match="Port must be between 1-65535"):
            ApiGatewayConfig(port=70000)
        
        # Test invalid timeout
        with pytest.raises(ValueError, match="Request timeout must be positive"):
            ApiGatewayConfig(request_timeout=0)
    
    @pytest.mark.asyncio
    async def test_api_request_validation(self):
        """Test API request validation."""
        # Test valid request
        request = ApiRequest(
            method="GET",
            path="/test",
            headers={},
            query_params={},
            body=None,
            timestamp=datetime.now(),
            request_id="test-123",
            client_ip="127.0.0.1"
        )
        assert request.method == "GET"
        
        # Test invalid method
        with pytest.raises(ValueError, match="Invalid HTTP method"):
            ApiRequest(
                method="INVALID",
                path="/test",
                headers={},
                query_params={},
                body=None,
                timestamp=datetime.now(),
                request_id="test-123",
                client_ip="127.0.0.1"
            )
        
        # Test empty request ID
        with pytest.raises(ValueError, match="Request ID cannot be empty"):
            ApiRequest(
                method="GET",
                path="/test",
                headers={},
                query_params={},
                body=None,
                timestamp=datetime.now(),
                request_id="",
                client_ip="127.0.0.1"
            )
    
    @pytest.mark.asyncio
    async def test_api_response_validation(self):
        """Test API response validation."""
        # Test valid response
        response = ApiResponse(
            status_code=200,
            headers={},
            body={"result": "success"},
            timestamp=datetime.now(),
            processing_time=15.5,
            request_id="test-123"
        )
        assert response.status_code == 200
        
        # Test invalid status code
        with pytest.raises(ValueError, match="Invalid status code"):
            ApiResponse(
                status_code=99,  # Below 100
                headers={},
                body={},
                timestamp=datetime.now(),
                processing_time=10.0,
                request_id="test-123"
            )
        
        # Test negative processing time
        with pytest.raises(ValueError, match="Processing time must be non-negative"):
            ApiResponse(
                status_code=200,
                headers={},
                body={},
                timestamp=datetime.now(),
                processing_time=-5.0,
                request_id="test-123"
            )