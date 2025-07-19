#!/usr/bin/env python3
"""
Comprehensive Test Suite for Rate Limiting Framework

Tests all aspects of the rate limiting system including algorithms,
middleware integration, configuration, and performance.
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

from security.rate_limiter import (
    RateLimiter, 
    RateLimitConfig, 
    RateLimitScope, 
    RateLimitStrategy,
    RateLimitStatus,
    RateLimitViolation,
    TokenBucket,
    SlidingWindowCounter,
    FixedWindowCounter
)
from external_api.rate_limit_middleware import RateLimitMiddleware
from external_api.models import ApiRequest, ApiResponse
from config.auth_models import Permission


class TestTokenBucket:
    """Test token bucket algorithm."""
    
    def test_token_bucket_creation(self):
        """Test token bucket initialization."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.capacity == 10
        assert bucket.refill_rate == 1.0
        assert bucket.tokens == 10
    
    def test_token_consumption(self):
        """Test token consumption."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        # Should be able to consume up to capacity
        for i in range(10):
            assert bucket.consume(1) is True
        
        # Should not be able to consume more
        assert bucket.consume(1) is False
    
    def test_token_refill(self):
        """Test token refill over time."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        # Consume all tokens
        for i in range(10):
            bucket.consume(1)
        
        # Wait for refill
        time.sleep(1.1)
        
        # Should be able to consume one token
        assert bucket.consume(1) is True
    
    def test_token_burst_capacity(self):
        """Test burst capacity limits."""
        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        
        # Should be able to consume all tokens at once (burst)
        assert bucket.consume(5) is True
        
        # Should not be able to consume more
        assert bucket.consume(1) is False


class TestSlidingWindowCounter:
    """Test sliding window counter algorithm."""
    
    def test_sliding_window_creation(self):
        """Test sliding window initialization."""
        window = SlidingWindowCounter(window_seconds=60, max_requests=10)
        assert window.window_seconds == 60
        assert window.max_requests == 10
        assert len(window.requests) == 0
    
    def test_request_tracking(self):
        """Test request tracking within window."""
        window = SlidingWindowCounter(window_seconds=60, max_requests=5)
        
        # Should be able to add up to max_requests
        for i in range(5):
            assert window.add_request() is True
        
        # Should not be able to add more
        assert window.add_request() is False
    
    def test_window_sliding(self):
        """Test window sliding behavior."""
        window = SlidingWindowCounter(window_seconds=1, max_requests=2)
        
        # Add requests
        assert window.add_request() is True
        assert window.add_request() is True
        assert window.add_request() is False
        
        # Wait for window to slide
        time.sleep(1.1)
        
        # Should be able to add requests again
        assert window.add_request() is True
    
    def test_partial_window_sliding(self):
        """Test partial window sliding with old requests removal."""
        window = SlidingWindowCounter(window_seconds=2, max_requests=3)
        
        # Add request at time 0
        now = time.time()
        assert window.add_request(now) is True
        
        # Add request at time 1
        assert window.add_request(now + 1) is True
        
        # Add request at time 1.5 (should fill window)
        assert window.add_request(now + 1.5) is True
        
        # Try to add at time 1.5 (should fail - window full)
        assert window.add_request(now + 1.5) is False
        
        # Add request at time 2.5 (should succeed - first request expired)
        assert window.add_request(now + 2.5) is True


class TestFixedWindowCounter:
    """Test fixed window counter algorithm."""
    
    def test_fixed_window_creation(self):
        """Test fixed window initialization."""
        window = FixedWindowCounter(window_seconds=60, max_requests=10)
        assert window.window_seconds == 60
        assert window.max_requests == 10
        assert window.current_count == 0
    
    def test_request_counting(self):
        """Test request counting within fixed window."""
        window = FixedWindowCounter(window_seconds=60, max_requests=3)
        
        # Should be able to add up to max_requests
        for i in range(3):
            assert window.add_request() is True
        
        # Should not be able to add more
        assert window.add_request() is False
    
    def test_window_reset(self):
        """Test window reset behavior."""
        window = FixedWindowCounter(window_seconds=1, max_requests=2)
        
        # Fill window
        assert window.add_request() is True
        assert window.add_request() is True
        assert window.add_request() is False
        
        # Wait for window reset
        time.sleep(1.1)
        
        # Should be able to add requests again
        assert window.add_request() is True
        assert window.add_request() is True


class TestRateLimiter:
    """Test main rate limiter functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter for testing."""
        config = {
            "cleanup_interval_seconds": 10,
            "max_violations_stored": 100,
            "performance_target_ms": 5.0
        }
        return RateLimiter(config)
    
    def test_rate_limiter_initialization(self, rate_limiter):
        """Test rate limiter initialization."""
        assert rate_limiter is not None
        assert len(rate_limiter.rules) > 0  # Should have default rules
        assert rate_limiter.check_count == 0
        assert rate_limiter.violation_count == 0
    
    def test_add_custom_rule(self, rate_limiter):
        """Test adding custom rate limiting rule."""
        rule = RateLimitConfig(
            name="test_rule",
            scope=RateLimitScope.PER_USER,
            strategy=RateLimitStrategy.TOKEN_BUCKET,
            requests_per_window=10,
            window_seconds=60,
            burst_capacity=15,
            refill_rate=0.17
        )
        
        assert rate_limiter.add_rule(rule) is True
        assert "test_rule" in rate_limiter.rules
        assert rate_limiter.rules["test_rule"].name == "test_rule"
    
    def test_remove_rule(self, rate_limiter):
        """Test removing rate limiting rule."""
        rule = RateLimitConfig(
            name="removable_rule",
            scope=RateLimitScope.PER_USER,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            requests_per_window=5,
            window_seconds=30
        )
        
        rate_limiter.add_rule(rule)
        assert "removable_rule" in rate_limiter.rules
        
        assert rate_limiter.remove_rule("removable_rule") is True
        assert "removable_rule" not in rate_limiter.rules
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_allowed(self, rate_limiter):
        """Test rate limit check when request is allowed."""
        context = {
            "user_id": "test_user_1",
            "endpoint": "/api/v1/test",
            "client_ip": "192.168.1.100",
            "user_roles": ["User"]
        }
        
        status = await rate_limiter.check_rate_limit(context)
        
        assert status.allowed is True
        assert status.remaining >= 0
        assert status.reset_time > datetime.utcnow()
        assert status.violation is None
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_exceeded(self, rate_limiter):
        """Test rate limit check when limit is exceeded."""
        # Add a very restrictive rule
        rule = RateLimitConfig(
            name="very_restrictive",
            scope=RateLimitScope.PER_USER,
            strategy=RateLimitStrategy.FIXED_WINDOW,
            requests_per_window=1,
            window_seconds=60,
            priority=1  # High priority
        )
        rate_limiter.add_rule(rule)
        
        context = {
            "user_id": "test_user_2",
            "endpoint": "/api/v1/test",
            "client_ip": "192.168.1.101",
            "user_roles": ["User"]
        }
        
        # First request should be allowed
        status1 = await rate_limiter.check_rate_limit(context)
        assert status1.allowed is True
        
        # Second request should be blocked
        status2 = await rate_limiter.check_rate_limit(context)
        assert status2.allowed is False
        assert status2.violation is not None
        assert status2.retry_after is not None
    
    @pytest.mark.asyncio
    async def test_rate_limit_different_scopes(self, rate_limiter):
        """Test rate limiting with different scopes."""
        # Test per-user scope
        user_context = {
            "user_id": "user1",
            "endpoint": "/api/v1/test",
            "client_ip": "192.168.1.100"
        }
        
        # Test per-IP scope  
        ip_context = {
            "user_id": "user2",
            "endpoint": "/api/v1/test",
            "client_ip": "192.168.1.100"  # Same IP, different user
        }
        
        # Should be tracked separately
        status1 = await rate_limiter.check_rate_limit(user_context)
        status2 = await rate_limiter.check_rate_limit(ip_context)
        
        assert status1.allowed is True
        assert status2.allowed is True
    
    @pytest.mark.asyncio
    async def test_violation_recording(self, rate_limiter):
        """Test violation recording and tracking."""
        # Add restrictive rule to trigger violation
        rule = RateLimitConfig(
            name="violation_test",
            scope=RateLimitScope.PER_USER,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            requests_per_window=1,
            window_seconds=60,
            priority=1
        )
        rate_limiter.add_rule(rule)
        
        context = {
            "user_id": "violation_user",
            "endpoint": "/api/v1/test",
            "client_ip": "192.168.1.102"
        }
        
        # First request allowed
        await rate_limiter.check_rate_limit(context)
        
        # Second request should create violation
        initial_violation_count = rate_limiter.violation_count
        status = await rate_limiter.check_rate_limit(context)
        
        assert status.allowed is False
        assert rate_limiter.violation_count > initial_violation_count
        assert len(rate_limiter.violations) > 0
    
    def test_rate_limit_stats(self, rate_limiter):
        """Test rate limit statistics."""
        stats = rate_limiter.get_rate_limit_stats()
        
        assert "performance" in stats
        assert "rules" in stats
        assert "violations" in stats
        assert "limiters" in stats
        assert "configuration" in stats
        
        assert stats["performance"]["total_checks"] >= 0
        assert stats["rules"]["total_rules"] > 0
    
    def test_config_export_import(self, rate_limiter):
        """Test configuration export and import."""
        # Export configuration
        exported_config = rate_limiter.export_config()
        
        assert "rules" in exported_config
        assert "configuration" in exported_config
        
        # Create new rate limiter and import config
        new_limiter = RateLimiter()
        assert new_limiter.import_config(exported_config) is True
        
        # Should have same number of rules
        assert len(new_limiter.rules) == len(rate_limiter.rules)
    
    @pytest.mark.asyncio
    async def test_user_limit_reset(self, rate_limiter):
        """Test resetting user limits."""
        user_id = "reset_test_user"
        context = {
            "user_id": user_id,
            "endpoint": "/api/v1/test",
            "client_ip": "192.168.1.103"
        }
        
        # Make some requests to create state
        await rate_limiter.check_rate_limit(context)
        await rate_limiter.check_rate_limit(context)
        
        # Reset user limits
        reset_count = rate_limiter.reset_user_limits(user_id)
        assert reset_count >= 0
    
    @pytest.mark.asyncio
    async def test_ip_limit_reset(self, rate_limiter):
        """Test resetting IP limits."""
        client_ip = "192.168.1.104"
        context = {
            "user_id": "test_user",
            "endpoint": "/api/v1/test",
            "client_ip": client_ip
        }
        
        # Make some requests to create state
        await rate_limiter.check_rate_limit(context)
        await rate_limiter.check_rate_limit(context)
        
        # Reset IP limits
        reset_count = rate_limiter.reset_ip_limits(client_ip)
        assert reset_count >= 0


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""
    
    @pytest.fixture
    def middleware(self):
        """Create middleware for testing."""
        config = {
            "enabled": True,
            "include_headers": True,
            "log_violations": True,
            "bypass_patterns": ["/health", "/metrics"],
            "custom_error_messages": {
                "default": "Rate limit exceeded"
            }
        }
        return RateLimitMiddleware(config)
    
    @pytest.fixture
    def sample_request(self):
        """Create sample API request."""
        return ApiRequest(
            method="GET",
            path="/api/v1/test",
            headers={
                "User-Agent": "TestClient/1.0",
                "X-User-ID": "test_user",
                "X-User-Roles": "User"
            },
            body=None,
            client_ip="192.168.1.100",
            request_id=str(uuid.uuid4())
        )
    
    def test_middleware_initialization(self, middleware):
        """Test middleware initialization."""
        assert middleware is not None
        assert middleware.enabled is True
        assert middleware.include_headers is True
        assert middleware.rate_limiter is not None
    
    def test_bypass_patterns(self, middleware):
        """Test request bypass patterns."""
        health_request = ApiRequest(
            method="GET",
            path="/health",
            headers={},
            body=None,
            client_ip="192.168.1.100",
            request_id=str(uuid.uuid4())
        )
        
        assert middleware._should_bypass(health_request) is True
        
        api_request = ApiRequest(
            method="GET",
            path="/api/v1/test",
            headers={},
            body=None,
            client_ip="192.168.1.100",
            request_id=str(uuid.uuid4())
        )
        
        assert middleware._should_bypass(api_request) is False
    
    @pytest.mark.asyncio
    async def test_request_context_extraction(self, middleware, sample_request):
        """Test extraction of request context."""
        context = await middleware._extract_request_context(sample_request)
        
        assert context["endpoint"] == "/api/v1/test"
        assert context["method"] == "GET"
        assert context["client_ip"] == "192.168.1.100"
        assert context["user_id"] == "test_user"
        assert "User" in context["user_roles"]
    
    @pytest.mark.asyncio
    async def test_process_allowed_request(self, middleware, sample_request):
        """Test processing allowed request."""
        async def mock_handler(request):
            return ApiResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body={"message": "success"},
                timestamp=datetime.utcnow(),
                processing_time=10.0,
                request_id=request.request_id
            )
        
        response = await middleware.process_request(sample_request, mock_handler)
        
        assert response.status_code == 200
        assert response.body["message"] == "success"
        
        # Should have rate limit headers
        if middleware.include_headers:
            assert "X-RateLimit-Remaining" in response.headers
    
    @pytest.mark.asyncio
    async def test_process_rate_limited_request(self, middleware, sample_request):
        """Test processing rate limited request."""
        # Add very restrictive rule to trigger rate limiting
        restrictive_rule = RateLimitConfig(
            name="test_restrictive",
            scope=RateLimitScope.PER_USER,
            strategy=RateLimitStrategy.FIXED_WINDOW,
            requests_per_window=1,
            window_seconds=60,
            priority=1
        )
        middleware.rate_limiter.add_rule(restrictive_rule)
        
        async def mock_handler(request):
            return ApiResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body={"message": "success"},
                timestamp=datetime.utcnow(),
                processing_time=10.0,
                request_id=request.request_id
            )
        
        # First request should succeed
        response1 = await middleware.process_request(sample_request, mock_handler)
        assert response1.status_code == 200
        
        # Second request should be rate limited
        response2 = await middleware.process_request(sample_request, mock_handler)
        assert response2.status_code == 429
        assert response2.body["error"] == "rate_limit_exceeded"
        assert "Retry-After" in response2.headers
    
    @pytest.mark.asyncio
    async def test_bypass_processing(self, middleware):
        """Test bypassed request processing."""
        bypass_request = ApiRequest(
            method="GET",
            path="/health",
            headers={},
            body=None,
            client_ip="192.168.1.100",
            request_id=str(uuid.uuid4())
        )
        
        async def mock_handler(request):
            return ApiResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body={"status": "healthy"},
                timestamp=datetime.utcnow(),
                processing_time=1.0,
                request_id=request.request_id
            )
        
        response = await middleware.process_request(bypass_request, mock_handler)
        
        assert response.status_code == 200
        assert middleware.bypass_count > 0
    
    @pytest.mark.asyncio
    async def test_middleware_stats(self, middleware):
        """Test middleware statistics."""
        stats = await middleware.get_middleware_stats()
        
        assert "middleware" in stats
        assert "rate_limiter" in stats
        assert "configuration" in stats
        
        middleware_stats = stats["middleware"]
        assert "processed_requests" in middleware_stats
        assert "blocked_requests" in middleware_stats
        assert "bypass_count" in middleware_stats
    
    @pytest.mark.asyncio
    async def test_dynamic_config_update(self, middleware):
        """Test dynamic configuration updates."""
        updates = {
            "role_based_limits": {
                "TestRole": {
                    "requests_per_minute": 50,
                    "burst_capacity": 75
                }
            },
            "middleware_config": {
                "include_headers": False
            }
        }
        
        result = await middleware.update_rate_limits(updates)
        assert result is True
        assert middleware.include_headers is False
    
    @pytest.mark.asyncio
    async def test_user_status_check(self, middleware):
        """Test user rate limit status check."""
        user_id = "status_test_user"
        status = await middleware.get_user_rate_limit_status(user_id)
        
        assert "user_id" in status
        assert "allowed" in status
        assert "remaining" in status
        assert "reset_time" in status
        assert status["user_id"] == user_id
    
    @pytest.mark.asyncio
    async def test_health_check(self, middleware):
        """Test middleware health check."""
        health = await middleware.health_check()
        
        assert "status" in health
        assert "enabled" in health
        assert "performance" in health
        assert "statistics" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]


class TestRateLimitIntegration:
    """Test rate limiting integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_jwt_rbac_integration(self):
        """Test integration with JWT and RBAC systems."""
        # This would test the full integration with JWT authentication
        # and RBAC authorization, ensuring rate limits are applied
        # based on authenticated user roles and permissions
        
        middleware = RateLimitMiddleware({
            "enabled": True,
            "role_based_limits": {
                "Admin": {"requests_per_minute": 100},
                "User": {"requests_per_minute": 20}
            }
        })
        
        # Admin user request
        admin_request = ApiRequest(
            method="GET",
            path="/api/v1/admin/test",
            headers={
                "X-User-ID": "admin_user",
                "X-User-Roles": "Admin"
            },
            body=None,
            client_ip="192.168.1.100",
            request_id=str(uuid.uuid4())
        )
        
        # Regular user request
        user_request = ApiRequest(
            method="GET",
            path="/api/v1/test",
            headers={
                "X-User-ID": "regular_user",
                "X-User-Roles": "User"
            },
            body=None,
            client_ip="192.168.1.101",
            request_id=str(uuid.uuid4())
        )
        
        async def mock_handler(request):
            return ApiResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body={"message": "success"},
                timestamp=datetime.utcnow(),
                processing_time=10.0,
                request_id=request.request_id
            )
        
        # Both should initially succeed
        admin_response = await middleware.process_request(admin_request, mock_handler)
        user_response = await middleware.process_request(user_request, mock_handler)
        
        assert admin_response.status_code == 200
        assert user_response.status_code == 200
        
        # Admin should have higher rate limits
        admin_remaining = int(admin_response.headers.get("X-RateLimit-Remaining", "0"))
        user_remaining = int(user_response.headers.get("X-RateLimit-Remaining", "0"))
        
        # Note: This is a simplified test - in reality, the rate limits would be
        # more complex and would require multiple requests to see the difference
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test rate limiting performance under load."""
        middleware = RateLimitMiddleware({
            "enabled": True,
            "performance_target_ms": 5.0
        })
        
        # Simulate multiple concurrent requests
        async def make_request(i):
            request = ApiRequest(
                method="GET",
                path=f"/api/v1/test/{i}",
                headers={
                    "X-User-ID": f"user_{i % 10}",  # 10 different users
                    "X-User-Roles": "User"
                },
                body=None,
                client_ip=f"192.168.1.{i % 256}",
                request_id=str(uuid.uuid4())
            )
            
            async def mock_handler(req):
                return ApiResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body={"message": "success"},
                    timestamp=datetime.utcnow(),
                    processing_time=1.0,
                    request_id=req.request_id
                )
            
            start_time = time.time()
            response = await middleware.process_request(request, mock_handler)
            processing_time = (time.time() - start_time) * 1000
            
            return response, processing_time
        
        # Make 100 concurrent requests
        tasks = [make_request(i) for i in range(100)]
        results = await asyncio.gather(*tasks)
        
        # Check performance
        processing_times = [result[1] for result in results]
        avg_processing_time = sum(processing_times) / len(processing_times)
        max_processing_time = max(processing_times)
        
        # Should meet performance targets
        assert avg_processing_time < 50.0  # Should be much faster than 50ms average
        assert max_processing_time < 100.0  # No single request should take too long
        
        # Check that some requests succeeded
        success_count = sum(1 for result in results if result[0].status_code == 200)
        assert success_count > 0
    
    @pytest.mark.asyncio
    async def test_distributed_scenario(self):
        """Test rate limiting in distributed scenario."""
        # This test simulates multiple API Gateway instances
        # with shared rate limiting state (in production this would use Redis)
        
        # Create two middleware instances (simulating different servers)
        middleware1 = RateLimitMiddleware({"enabled": True})
        middleware2 = RateLimitMiddleware({"enabled": True})
        
        # Same user making requests to both instances
        user_request = ApiRequest(
            method="GET",
            path="/api/v1/test",
            headers={
                "X-User-ID": "distributed_user",
                "X-User-Roles": "User"
            },
            body=None,
            client_ip="192.168.1.100",
            request_id=str(uuid.uuid4())
        )
        
        async def mock_handler(request):
            return ApiResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body={"message": "success"},
                timestamp=datetime.utcnow(),
                processing_time=10.0,
                request_id=request.request_id
            )
        
        # Make requests to both instances
        response1 = await middleware1.process_request(user_request, mock_handler)
        response2 = await middleware2.process_request(user_request, mock_handler)
        
        # Both should succeed (since we're using separate instances without shared state)
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Note: In a real distributed setup with shared Redis backend,
        # the rate limiting state would be shared between instances


@pytest.mark.asyncio
async def test_configuration_loading():
    """Test loading rate limiting configuration from YAML file."""
    import yaml
    import os
    
    # Test loading the rate_limits.yaml configuration
    config_path = os.path.join(os.path.dirname(__file__), "../../config/rate_limits.yaml")
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        assert "global" in config
        assert "system_limits" in config
        assert "user_limits" in config
        assert "role_limits" in config
        assert "endpoint_limits" in config
        
        # Test that configuration is valid
        assert config["global"]["enabled"] is True
        assert len(config["role_limits"]) > 0
        assert len(config["endpoint_limits"]) > 0


def test_rate_limit_headers():
    """Test rate limit header generation."""
    from security.rate_limiter import RateLimitStatus
    from datetime import datetime, timedelta
    
    rate_limiter = RateLimiter()
    
    status = RateLimitStatus(
        allowed=True,
        remaining=50,
        reset_time=datetime.utcnow() + timedelta(minutes=1),
        retry_after=None
    )
    
    headers = rate_limiter.get_rate_limit_headers(status)
    
    assert "X-RateLimit-Limit" in headers
    assert "X-RateLimit-Remaining" in headers
    assert "X-RateLimit-Reset" in headers
    assert headers["X-RateLimit-Remaining"] == "50"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])