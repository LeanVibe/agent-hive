"""
Comprehensive tests for unified security middleware
=================================================

Tests performance, security, and integration with existing systems.
"""

import asyncio
import json
import time
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
import redis.asyncio as redis

from config.unified_security_config import UnifiedSecurityConfig, DEVELOPMENT_CONFIG
from security.unified_security_middleware import UnifiedSecurityMiddleware, SecurityContext
from external_api.auth_middleware import Permission
from external_api.models import ApiRequest


class TestUnifiedSecurityMiddleware:
    """Test suite for unified security middleware"""
    
    @pytest.fixture
    async def mock_redis(self):
        """Mock Redis client"""
        redis_mock = AsyncMock()
        redis_mock.ping.return_value = True
        redis_mock.get.return_value = None
        redis_mock.set.return_value = True
        redis_mock.incr.return_value = 1
        redis_mock.expire.return_value = True
        redis_mock.hgetall.return_value = {}
        redis_mock.hset.return_value = True
        redis_mock.lpush.return_value = True
        redis_mock.ltrim.return_value = True
        redis_mock.zcard.return_value = 0
        redis_mock.zadd.return_value = True
        redis_mock.zremrangebyscore.return_value = True
        return redis_mock
    
    @pytest.fixture
    def test_config(self):
        """Test configuration"""
        config = DEVELOPMENT_CONFIG
        config.rate_limiting.connection_timeout_ms = 5
        config.rate_limiting.response_timeout_ms = 5
        config.redis.socket_timeout = 0.005
        return config
    
    @pytest.fixture
    async def middleware(self, test_config, mock_redis):
        """Create middleware instance"""
        middleware = UnifiedSecurityMiddleware(test_config)
        middleware.redis_client = mock_redis
        await middleware.initialize()
        return middleware
    
    @pytest.fixture
    def app(self, middleware):
        """Create FastAPI app with middleware"""
        app = FastAPI()
        
        @app.middleware("http")
        async def add_security_middleware(request: Request, call_next):
            return await middleware(request, call_next)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        @app.get("/admin")
        async def admin_endpoint():
            return {"message": "admin access"}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return TestClient(app)


class TestPerformanceTargets:
    """Test performance targets (<10ms)"""
    
    @pytest.mark.asyncio
    async def test_middleware_initialization_performance(self, test_config, mock_redis):
        """Test middleware initialization time"""
        start_time = time.time()
        
        middleware = UnifiedSecurityMiddleware(test_config)
        middleware.redis_client = mock_redis
        await middleware.initialize()
        
        init_time = (time.time() - start_time) * 1000
        assert init_time < 100, f"Initialization took {init_time}ms (should be <100ms)"
    
    @pytest.mark.asyncio
    async def test_fast_security_checks_performance(self, middleware):
        """Test fast security checks performance"""
        # Create mock request
        request = Mock()
        request.headers = {"Content-Length": "1000"}
        request.client = Mock()
        request.client.host = "192.168.1.1"
        
        context = SecurityContext(ip_address="192.168.1.1")
        
        start_time = time.time()
        result = await middleware._fast_security_checks(request, context)
        check_time = (time.time() - start_time) * 1000
        
        assert check_time < 3, f"Fast security checks took {check_time}ms (should be <3ms)"
        assert result is None  # Should pass
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_performance(self, middleware):
        """Test rate limit check performance"""
        # Create mock request
        request = Mock()
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        
        context = SecurityContext(ip_address="192.168.1.1", user_role="user")
        
        start_time = time.time()
        result = await middleware._check_rate_limits(request, context)
        check_time = (time.time() - start_time) * 1000
        
        assert check_time < 3, f"Rate limit check took {check_time}ms (should be <3ms)"
        assert result is None  # Should pass
    
    @pytest.mark.asyncio
    async def test_authentication_performance(self, middleware):
        """Test authentication performance"""
        # Create mock request
        request = Mock()
        request.headers = {"Authorization": "Bearer valid-token"}
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        request.client = Mock()
        request.client.host = "192.168.1.1"
        
        context = SecurityContext(ip_address="192.168.1.1")
        
        start_time = time.time()
        result = await middleware._authenticate_request(request, context)
        auth_time = (time.time() - start_time) * 1000
        
        assert auth_time < 3, f"Authentication took {auth_time}ms (should be <3ms)"
    
    @pytest.mark.asyncio
    async def test_full_request_processing_performance(self, client):
        """Test full request processing performance"""
        # Warm up
        client.get("/test")
        
        # Measure performance
        start_time = time.time()
        response = client.get("/test")
        total_time = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert total_time < 10, f"Full request processing took {total_time}ms (should be <10ms)"
        
        # Check processing time header
        processing_time = response.headers.get("X-Processing-Time")
        if processing_time:
            time_ms = float(processing_time.replace("ms", ""))
            assert time_ms < 10, f"Reported processing time {time_ms}ms (should be <10ms)"


class TestSecurityFeatures:
    """Test security features"""
    
    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self, middleware, mock_redis):
        """Test rate limiting enforcement"""
        # Mock rate limit exceeded
        mock_redis.zcard.return_value = 200  # Exceed limit
        
        request = Mock()
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        
        context = SecurityContext(ip_address="192.168.1.1", user_role="user")
        
        result = await middleware._check_rate_limits(request, context)
        
        assert result is not None
        assert result.status_code == 429
    
    @pytest.mark.asyncio
    async def test_ip_blacklisting(self, middleware, mock_redis):
        """Test IP blacklisting"""
        # Mock blacklisted IP
        mock_redis.get.return_value = "blocked"
        
        request = Mock()
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"
        
        context = SecurityContext(ip_address="192.168.1.1")
        
        result = await middleware._fast_security_checks(request, context)
        
        assert result is not None
        assert result.status_code == 403
    
    @pytest.mark.asyncio
    async def test_payload_size_validation(self, middleware):
        """Test payload size validation"""
        request = Mock()
        request.headers = {"Content-Length": "50000000"}  # 50MB
        request.client = Mock()
        request.client.host = "192.168.1.1"
        
        context = SecurityContext(ip_address="192.168.1.1")
        
        result = await middleware._fast_security_checks(request, context)
        
        assert result is not None
        assert result.status_code == 413
    
    @pytest.mark.asyncio
    async def test_role_based_rate_limiting(self, middleware):
        """Test role-based rate limiting"""
        # Test admin gets higher limits
        request = Mock()
        request.url = Mock()
        request.url.path = "/test"
        
        # Admin context
        admin_context = SecurityContext(
            ip_address="192.168.1.1",
            user_role="admin",
            authenticated=True
        )
        
        # User context
        user_context = SecurityContext(
            ip_address="192.168.1.2",
            user_role="user",
            authenticated=True
        )
        
        # Check both get different limits
        admin_result = await middleware._check_rate_limits(request, admin_context)
        user_result = await middleware._check_rate_limits(request, user_context)
        
        # Both should pass initially
        assert admin_result is None
        assert user_result is None
        
        # Admin should have higher remaining count
        assert admin_context.rate_limit_remaining >= user_context.rate_limit_remaining
    
    @pytest.mark.asyncio
    async def test_security_headers_added(self, client):
        """Test security headers are added"""
        response = client.get("/test")
        
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-Security-Score" in response.headers
        assert "X-Processing-Time" in response.headers


class TestAuthenticationIntegration:
    """Test authentication integration"""
    
    @pytest.mark.asyncio
    async def test_api_key_authentication(self, middleware):
        """Test API key authentication"""
        # Setup API key in auth middleware
        api_key = middleware.auth_middleware.create_api_key(
            "test-user",
            [Permission.READ, Permission.WRITE]
        )
        
        request = Mock()
        request.headers = {"X-API-Key": api_key}
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        request.client = Mock()
        request.client.host = "192.168.1.1"
        
        context = SecurityContext(ip_address="192.168.1.1")
        
        result = await middleware._authenticate_request(request, context)
        
        assert result is None  # Should pass
        assert context.authenticated is True
        assert context.user_id == "test-user"
        assert context.user_role == "user"
    
    @pytest.mark.asyncio
    async def test_jwt_authentication(self, middleware):
        """Test JWT authentication"""
        # Create JWT token
        token = middleware.auth_middleware.create_jwt_token(
            "test-user",
            [Permission.READ, Permission.ADMIN]
        )
        
        request = Mock()
        request.headers = {"Authorization": f"Bearer {token}"}
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        request.client = Mock()
        request.client.host = "192.168.1.1"
        
        context = SecurityContext(ip_address="192.168.1.1")
        
        result = await middleware._authenticate_request(request, context)
        
        assert result is None  # Should pass
        assert context.authenticated is True
        assert context.user_id == "test-user"
        assert context.user_role == "admin"  # Should have admin role
    
    @pytest.mark.asyncio
    async def test_unauthenticated_access_to_protected_path(self, middleware):
        """Test unauthenticated access to protected path"""
        # Configure path protection
        middleware.auth_middleware.set_path_permissions("/admin", [Permission.ADMIN])
        
        request = Mock()
        request.headers = {}
        request.url = Mock()
        request.url.path = "/admin"
        request.method = "GET"
        request.client = Mock()
        request.client.host = "192.168.1.1"
        
        context = SecurityContext(ip_address="192.168.1.1")
        
        result = await middleware._authenticate_request(request, context)
        
        assert result is not None
        assert result.status_code == 401


class TestRedisIntegration:
    """Test Redis integration"""
    
    @pytest.mark.asyncio
    async def test_redis_connection_optimization(self, test_config):
        """Test Redis connection optimization"""
        middleware = UnifiedSecurityMiddleware(test_config)
        
        # Check connection pool settings
        assert test_config.redis.socket_timeout <= 0.01
        assert test_config.redis.socket_connect_timeout <= 0.01
        assert test_config.redis.connection_pool_size >= 10
    
    @pytest.mark.asyncio
    async def test_redis_failover_handling(self, middleware, mock_redis):
        """Test Redis failover handling"""
        # Mock Redis failure
        mock_redis.ping.side_effect = redis.ConnectionError("Redis down")
        
        request = Mock()
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        
        context = SecurityContext(ip_address="192.168.1.1")
        
        # Should fail open if configured
        if middleware.config.rate_limiting.fail_open:
            result = await middleware._check_rate_limits(request, context)
            assert result is None  # Should pass even with Redis down
    
    @pytest.mark.asyncio
    async def test_security_event_logging(self, middleware, mock_redis):
        """Test security event logging to Redis"""
        request = Mock()
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/test"
        
        response = Mock()
        response.status_code = 200
        
        context = SecurityContext(
            ip_address="192.168.1.1",
            user_id="test-user",
            authenticated=True
        )
        
        await middleware._log_security_event(request, response, context)
        
        # Verify Redis logging was called
        mock_redis.lpush.assert_called()
        mock_redis.ltrim.assert_called()
    
    @pytest.mark.asyncio
    async def test_user_session_management(self, middleware, mock_redis):
        """Test user session management"""
        context = SecurityContext(
            ip_address="192.168.1.1",
            user_id="test-user",
            authenticated=True
        )
        
        await middleware._update_user_session(context)
        
        # Verify session data was stored
        mock_redis.hset.assert_called()
        mock_redis.expire.assert_called()


class TestConfigurationIntegration:
    """Test configuration integration"""
    
    def test_environment_specific_configs(self):
        """Test environment-specific configurations"""
        # Development config
        dev_config = DEVELOPMENT_CONFIG
        assert dev_config.authentication.require_https is False
        assert dev_config.validation.strict_mode is False
        
        # Production config would have stricter settings
        prod_config = UnifiedSecurityConfig()
        prod_config.environment = "production"
        prod_config._apply_production_optimizations()
        
        assert prod_config.authentication.require_https is True
        assert prod_config.validation.strict_mode is True
    
    def test_performance_target_validation(self):
        """Test performance target validation"""
        config = UnifiedSecurityConfig()
        
        # Should pass with optimized settings
        config.rate_limiting.connection_timeout_ms = 5
        config.rate_limiting.response_timeout_ms = 5
        config.redis.socket_timeout = 0.005
        
        assert config.is_performance_optimized() is True
        
        # Should fail with slow settings
        config.rate_limiting.connection_timeout_ms = 15
        assert config.is_performance_optimized() is False
    
    def test_endpoint_specific_rate_limits(self):
        """Test endpoint-specific rate limits"""
        config = UnifiedSecurityConfig()
        
        # Configure endpoint-specific limits
        config.rate_limiting.endpoint_limits = {
            "/api/upload": {"max_requests": 10, "window_seconds": 300},
            "/api/auth": {"max_requests": 5, "window_seconds": 60}
        }
        
        upload_config = config.get_rate_limit_config_for_endpoint("/api/upload")
        auth_config = config.get_rate_limit_config_for_endpoint("/api/auth")
        
        assert upload_config["max_requests"] == 10
        assert upload_config["window_seconds"] == 300
        assert auth_config["max_requests"] == 5
        assert auth_config["window_seconds"] == 60
    
    def test_role_based_rate_multipliers(self):
        """Test role-based rate multipliers"""
        config = UnifiedSecurityConfig()
        
        # Test admin gets 10x multiplier
        admin_config = config.get_rate_limit_config_for_endpoint("/test", "admin")
        user_config = config.get_rate_limit_config_for_endpoint("/test", "user")
        
        assert admin_config["max_requests"] == user_config["max_requests"] * 10


class TestMetricsAndMonitoring:
    """Test metrics and monitoring"""
    
    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, middleware):
        """Test performance metrics collection"""
        # Simulate some requests
        await middleware._update_metrics(5.0, True)
        await middleware._update_metrics(8.0, True)
        await middleware._update_metrics(12.0, False)  # Slow request
        
        stats = await middleware.get_security_stats()
        
        assert stats["performance"]["total_requests"] == 3
        assert stats["performance"]["avg_processing_time_ms"] > 0
        assert "performance_target_met" in stats["performance"]
    
    @pytest.mark.asyncio
    async def test_security_metrics_tracking(self, middleware):
        """Test security metrics tracking"""
        # Update various security metrics
        middleware.performance_metrics["rate_limit_hits"] = 5
        middleware.performance_metrics["auth_failures"] = 2
        middleware.performance_metrics["ddos_detections"] = 1
        
        await middleware._update_metrics(5.0, True)
        stats = await middleware.get_security_stats()
        
        assert stats["security"]["rate_limit_hits"] == 5
        assert stats["security"]["auth_failures"] == 2
        assert stats["security"]["ddos_detections"] == 1
    
    @pytest.mark.asyncio
    async def test_configuration_reporting(self, middleware):
        """Test configuration reporting"""
        stats = await middleware.get_security_stats()
        
        assert "configuration" in stats
        assert "performance_optimized" in stats["configuration"]
        assert "security_level" in stats["configuration"]
        assert "environment" in stats["configuration"]


class TestLoadAndStress:
    """Load and stress tests"""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_performance(self, middleware):
        """Test performance under concurrent load"""
        async def make_request():
            request = Mock()
            request.url = Mock()
            request.url.path = "/test"
            request.method = "GET"
            request.client = Mock()
            request.client.host = "192.168.1.1"
            
            context = SecurityContext(ip_address="192.168.1.1")
            
            start_time = time.time()
            await middleware._check_rate_limits(request, context)
            return (time.time() - start_time) * 1000
        
        # Run 100 concurrent requests
        tasks = [make_request() for _ in range(100)]
        times = await asyncio.gather(*tasks)
        
        # All should complete within performance target
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        assert avg_time < 5, f"Average time {avg_time}ms (should be <5ms)"
        assert max_time < 10, f"Max time {max_time}ms (should be <10ms)"
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, middleware):
        """Test memory usage under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate many requests
        for i in range(1000):
            request = Mock()
            request.url = Mock()
            request.url.path = f"/test/{i}"
            request.method = "GET"
            request.client = Mock()
            request.client.host = f"192.168.1.{i % 255}"
            
            context = SecurityContext(ip_address=f"192.168.1.{i % 255}")
            await middleware._check_rate_limits(request, context)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable
        assert memory_increase < 100, f"Memory increased by {memory_increase}MB"


# Performance benchmarks
@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """Performance benchmarks"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_benchmark(self, middleware, benchmark):
        """Benchmark rate limit checking"""
        request = Mock()
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        
        context = SecurityContext(ip_address="192.168.1.1")
        
        result = await benchmark(middleware._check_rate_limits, request, context)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_auth_benchmark(self, middleware, benchmark):
        """Benchmark authentication"""
        request = Mock()
        request.headers = {"X-API-Key": "test-key"}
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        request.client = Mock()
        request.client.host = "192.168.1.1"
        
        context = SecurityContext(ip_address="192.168.1.1")
        
        await benchmark(middleware._authenticate_request, request, context)
    
    @pytest.mark.asyncio
    async def test_full_middleware_benchmark(self, client, benchmark):
        """Benchmark full middleware processing"""
        def make_request():
            return client.get("/test")
        
        response = benchmark(make_request)
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])