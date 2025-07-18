#!/usr/bin/env python3
"""
Security Integration Test
========================

Test script to validate security middleware integration and performance.
"""

import asyncio
import time
import json
from unittest.mock import Mock, AsyncMock

# Add current directory to path
import sys
sys.path.append('.')

from config.unified_security_config import UnifiedSecurityConfig, get_security_config
from security.unified_security_middleware import UnifiedSecurityMiddleware, SecurityContext
from external_api.auth_middleware import Permission


async def test_config_integration():
    """Test unified security configuration"""
    print("🔧 Testing unified security configuration...")
    
    # Test development config
    dev_config = get_security_config("development")
    assert dev_config.is_performance_optimized(), "Development config should be performance optimized"
    assert dev_config.rate_limiting.connection_timeout_ms <= 10, "Connection timeout should be ≤10ms"
    assert dev_config.rate_limiting.response_timeout_ms <= 10, "Response timeout should be ≤10ms"
    
    # Test production config
    prod_config = get_security_config("production")
    assert prod_config.is_performance_optimized(), "Production config should be performance optimized"
    assert prod_config.authentication.require_https, "Production should require HTTPS"
    
    # Test role-based rate limiting
    admin_config = dev_config.get_rate_limit_config_for_endpoint("/test", "admin")
    user_config = dev_config.get_rate_limit_config_for_endpoint("/test", "user")
    assert admin_config["max_requests"] > user_config["max_requests"], "Admin should have higher limits"
    
    print("✅ Configuration integration tests passed")


async def test_middleware_performance():
    """Test middleware performance targets"""
    print("⚡ Testing middleware performance...")
    
    # Create mock Redis client
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.incr.return_value = 1
    mock_redis.expire.return_value = True
    mock_redis.hgetall.return_value = {}
    mock_redis.hset.return_value = True
    mock_redis.lpush.return_value = True
    mock_redis.ltrim.return_value = True
    mock_redis.zcard.return_value = 5  # Current usage
    mock_redis.zadd.return_value = True
    mock_redis.zremrangebyscore.return_value = True
    
    # Initialize middleware
    config = get_security_config("development")
    middleware = UnifiedSecurityMiddleware(config)
    middleware.redis_client = mock_redis
    await middleware.initialize()
    
    # Test fast security checks
    request = Mock()
    request.headers = {"Content-Length": "1000"}
    request.client = Mock()
    request.client.host = "192.168.1.1"
    
    context = SecurityContext(ip_address="192.168.1.1")
    
    start_time = time.time()
    result = await middleware._fast_security_checks(request, context)
    fast_check_time = (time.time() - start_time) * 1000
    
    assert fast_check_time < 3, f"Fast security checks took {fast_check_time:.2f}ms (should be <3ms)"
    print(f"  ✅ Fast security checks: {fast_check_time:.2f}ms")
    
    # Test rate limiting performance
    request.url = Mock()
    request.url.path = "/test"
    request.method = "GET"
    
    context = SecurityContext(ip_address="192.168.1.1", user_role="user")
    
    start_time = time.time()
    result = await middleware._check_rate_limits(request, context)
    rate_limit_time = (time.time() - start_time) * 1000
    
    assert rate_limit_time < 3, f"Rate limiting took {rate_limit_time:.2f}ms (should be <3ms)"
    print(f"  ✅ Rate limiting: {rate_limit_time:.2f}ms")
    
    # Test authentication performance
    request.headers = {"X-API-Key": "test-key"}
    
    # Create API key for testing
    api_key = middleware.auth_middleware.create_api_key(
        "test-user",
        [Permission.READ, Permission.WRITE]
    )
    request.headers = {"X-API-Key": api_key}
    
    start_time = time.time()
    result = await middleware._authenticate_request(request, context)
    auth_time = (time.time() - start_time) * 1000
    
    assert auth_time < 3, f"Authentication took {auth_time:.2f}ms (should be <3ms)"
    print(f"  ✅ Authentication: {auth_time:.2f}ms")
    
    print("✅ Performance tests passed - all operations <3ms")


async def test_security_features():
    """Test security features"""
    print("🔒 Testing security features...")
    
    # Create mock Redis client
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.incr.return_value = 1
    mock_redis.expire.return_value = True
    mock_redis.hgetall.return_value = {}
    mock_redis.hset.return_value = True
    mock_redis.lpush.return_value = True
    mock_redis.ltrim.return_value = True
    mock_redis.zcard.return_value = 5
    mock_redis.zadd.return_value = True
    mock_redis.zremrangebyscore.return_value = True
    
    # Initialize middleware
    config = get_security_config("development")
    middleware = UnifiedSecurityMiddleware(config)
    middleware.redis_client = mock_redis
    await middleware.initialize()
    
    # Test IP blacklisting
    mock_redis.get.return_value = "blocked"
    
    request = Mock()
    request.headers = {}
    request.client = Mock()
    request.client.host = "192.168.1.1"
    
    context = SecurityContext(ip_address="192.168.1.1")
    
    result = await middleware._fast_security_checks(request, context)
    assert result is not None, "Blacklisted IP should be blocked"
    assert result.status_code == 403, "Should return 403 for blacklisted IP"
    print("  ✅ IP blacklisting works")
    
    # Test rate limiting
    mock_redis.get.return_value = None  # Not blacklisted
    mock_redis.zcard.return_value = 200  # Exceed limit
    
    request.url = Mock()
    request.url.path = "/test"
    request.method = "GET"
    
    context = SecurityContext(ip_address="192.168.1.1", user_role="user")
    
    result = await middleware._check_rate_limits(request, context)
    assert result is not None, "Rate limit should be enforced"
    assert result.status_code == 429, "Should return 429 for rate limit exceeded"
    print("  ✅ Rate limiting works")
    
    # Test authentication
    request.headers = {}
    request.url.path = "/admin"  # Protected path
    
    # Set up path protection
    middleware.auth_middleware.set_path_permissions("/admin", [Permission.ADMIN])
    
    context = SecurityContext(ip_address="192.168.1.1")
    
    result = await middleware._authenticate_request(request, context)
    assert result is not None, "Protected path should require authentication"
    assert result.status_code == 401, "Should return 401 for unauthenticated access"
    print("  ✅ Path protection works")
    
    print("✅ Security features tests passed")


async def test_role_based_features():
    """Test role-based security features"""
    print("👥 Testing role-based features...")
    
    # Create mock Redis client
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.incr.return_value = 1
    mock_redis.expire.return_value = True
    mock_redis.hgetall.return_value = {}
    mock_redis.hset.return_value = True
    mock_redis.lpush.return_value = True
    mock_redis.ltrim.return_value = True
    mock_redis.zcard.return_value = 5
    mock_redis.zadd.return_value = True
    mock_redis.zremrangebyscore.return_value = True
    
    # Initialize middleware
    config = get_security_config("development")
    middleware = UnifiedSecurityMiddleware(config)
    middleware.redis_client = mock_redis
    await middleware.initialize()
    
    # Test admin authentication
    admin_token = middleware.auth_middleware.create_jwt_token(
        "admin-user",
        [Permission.READ, Permission.WRITE, Permission.ADMIN]
    )
    
    request = Mock()
    request.headers = {"Authorization": f"Bearer {admin_token}"}
    request.url = Mock()
    request.url.path = "/admin"
    request.method = "GET"
    request.client = Mock()
    request.client.host = "192.168.1.1"
    
    context = SecurityContext(ip_address="192.168.1.1")
    
    result = await middleware._authenticate_request(request, context)
    assert result is None, "Admin should be authenticated"
    assert context.user_role == "admin", "Should have admin role"
    print("  ✅ Admin authentication works")
    
    # Test regular user authentication
    user_token = middleware.auth_middleware.create_jwt_token(
        "regular-user",
        [Permission.READ, Permission.WRITE]
    )
    
    request.headers = {"Authorization": f"Bearer {user_token}"}
    context = SecurityContext(ip_address="192.168.1.1")
    
    result = await middleware._authenticate_request(request, context)
    assert result is None, "User should be authenticated"
    assert context.user_role == "user", "Should have user role"
    print("  ✅ User authentication works")
    
    # Test role-based rate limiting
    admin_context = SecurityContext(ip_address="192.168.1.1", user_role="admin")
    user_context = SecurityContext(ip_address="192.168.1.2", user_role="user")
    
    request.url.path = "/test"
    
    await middleware._check_rate_limits(request, admin_context)
    await middleware._check_rate_limits(request, user_context)
    
    # Admin should have higher remaining count due to multiplier
    assert admin_context.rate_limit_remaining >= user_context.rate_limit_remaining, \
        "Admin should have higher rate limits"
    print("  ✅ Role-based rate limiting works")
    
    print("✅ Role-based features tests passed")


async def test_metrics_and_monitoring():
    """Test metrics and monitoring"""
    print("📊 Testing metrics and monitoring...")
    
    # Create mock Redis client
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.hgetall.return_value = {
        "total_requests": "100",
        "avg_processing_time_ms": "5.2",
        "rate_limit_hits": "10",
        "auth_failures": "5"
    }
    mock_redis.hset.return_value = True
    
    # Initialize middleware
    config = get_security_config("development")
    middleware = UnifiedSecurityMiddleware(config)
    middleware.redis_client = mock_redis
    await middleware.initialize()
    
    # Test metrics collection
    await middleware._update_metrics(5.0, True)
    await middleware._update_metrics(8.0, True)
    
    # Test stats retrieval
    stats = await middleware.get_security_stats()
    
    assert "performance" in stats, "Stats should include performance metrics"
    assert "security" in stats, "Stats should include security metrics"
    assert "configuration" in stats, "Stats should include configuration info"
    
    assert stats["performance"]["total_requests"] == 100, "Should report total requests"
    assert stats["performance"]["avg_processing_time_ms"] == 5.2, "Should report avg processing time"
    assert stats["security"]["rate_limit_hits"] == 10, "Should report rate limit hits"
    
    print("  ✅ Metrics collection works")
    print("  ✅ Stats retrieval works")
    print("✅ Metrics and monitoring tests passed")


async def test_concurrent_performance():
    """Test concurrent performance"""
    print("🚀 Testing concurrent performance...")
    
    # Create mock Redis client
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.incr.return_value = 1
    mock_redis.expire.return_value = True
    mock_redis.hgetall.return_value = {}
    mock_redis.hset.return_value = True
    mock_redis.lpush.return_value = True
    mock_redis.ltrim.return_value = True
    mock_redis.zcard.return_value = 5
    mock_redis.zadd.return_value = True
    mock_redis.zremrangebyscore.return_value = True
    
    # Initialize middleware
    config = get_security_config("development")
    middleware = UnifiedSecurityMiddleware(config)
    middleware.redis_client = mock_redis
    await middleware.initialize()
    
    async def make_request():
        """Make a single request and measure time"""
        request = Mock()
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        request.client = Mock()
        request.client.host = "192.168.1.1"
        
        context = SecurityContext(ip_address="192.168.1.1", user_role="user")
        
        start_time = time.time()
        await middleware._check_rate_limits(request, context)
        return (time.time() - start_time) * 1000
    
    # Run 50 concurrent requests
    tasks = [make_request() for _ in range(50)]
    times = await asyncio.gather(*tasks)
    
    avg_time = sum(times) / len(times)
    max_time = max(times)
    
    assert avg_time < 5, f"Average time {avg_time:.2f}ms should be <5ms"
    assert max_time < 10, f"Max time {max_time:.2f}ms should be <10ms"
    
    print(f"  ✅ Concurrent performance: avg={avg_time:.2f}ms, max={max_time:.2f}ms")
    print("✅ Concurrent performance tests passed")


async def main():
    """Run all tests"""
    print("🔐 Security Middleware Integration Tests")
    print("=" * 50)
    
    try:
        await test_config_integration()
        await test_middleware_performance()
        await test_security_features()
        await test_role_based_features()
        await test_metrics_and_monitoring()
        await test_concurrent_performance()
        
        print("\n🎉 All tests passed!")
        print("✅ Unified security middleware integration successful")
        print("✅ Performance targets met (<10ms)")
        print("✅ Security features working correctly")
        print("✅ Role-based access control functional")
        print("✅ Metrics and monitoring operational")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)