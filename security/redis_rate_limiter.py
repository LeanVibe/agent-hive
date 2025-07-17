"""
Redis-backed Rate Limiting Middleware
====================================

Implements distributed rate limiting with Redis backend using sliding window algorithm.
Supports multiple rate limit types, IP whitelisting/blacklisting, and real-time monitoring.
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import ipaddress
import hashlib

import redis.asyncio as redis
from pydantic import BaseModel, validator

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """Rate limit enforcement types"""
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    TOKEN_BUCKET = "token_bucket"


class RateLimitAction(Enum):
    """Actions to take when rate limit is exceeded"""
    BLOCK = "block"
    DELAY = "delay"
    CAPTCHA = "captcha"
    LOG_ONLY = "log_only"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting rules"""
    key_prefix: str
    max_requests: int
    window_seconds: int
    limit_type: RateLimitType = RateLimitType.SLIDING_WINDOW
    action: RateLimitAction = RateLimitAction.BLOCK
    whitelist_ips: List[str] = None
    blacklist_ips: List[str] = None
    burst_allowance: int = 0
    grace_period: int = 0


class RateLimitResult(BaseModel):
    """Result of rate limit check"""
    allowed: bool
    requests_remaining: int
    reset_time: float
    retry_after: Optional[int] = None
    blocked_reason: Optional[str] = None
    current_usage: int = 0


class RedisRateLimiter:
    """Redis-backed distributed rate limiter with sliding window algorithm"""
    
    def __init__(self, redis_client: redis.Redis, config: RateLimitConfig):
        self.redis = redis_client
        self.config = config
        self.whitelist_networks = self._parse_networks(config.whitelist_ips or [])
        self.blacklist_networks = self._parse_networks(config.blacklist_ips or [])
        
    def _parse_networks(self, ip_list: List[str]) -> List[ipaddress.IPv4Network]:
        """Parse IP addresses and CIDR ranges into network objects"""
        networks = []
        for ip_str in ip_list:
            try:
                if '/' in ip_str:
                    networks.append(ipaddress.ip_network(ip_str, strict=False))
                else:
                    networks.append(ipaddress.ip_network(f"{ip_str}/32", strict=False))
            except ipaddress.AddressValueError:
                logger.warning(f"Invalid IP address/range: {ip_str}")
        return networks
    
    def _is_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted"""
        if not self.whitelist_networks:
            return False
        
        try:
            ip_addr = ipaddress.ip_address(ip)
            return any(ip_addr in network for network in self.whitelist_networks)
        except ipaddress.AddressValueError:
            return False
    
    def _is_blacklisted(self, ip: str) -> bool:
        """Check if IP is blacklisted"""
        if not self.blacklist_networks:
            return False
        
        try:
            ip_addr = ipaddress.ip_address(ip)
            return any(ip_addr in network for network in self.blacklist_networks)
        except ipaddress.AddressValueError:
            return False
    
    def _generate_key(self, identifier: str, endpoint: str = None) -> str:
        """Generate Redis key for rate limiting"""
        base_key = f"{self.config.key_prefix}:{identifier}"
        if endpoint:
            base_key += f":{endpoint}"
        return base_key
    
    async def _sliding_window_check(self, key: str, current_time: float) -> Tuple[bool, int, float]:
        """Implement sliding window rate limiting algorithm"""
        pipe = self.redis.pipeline()
        
        # Remove expired entries
        window_start = current_time - self.config.window_seconds
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests in window
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(current_time): current_time})
        
        # Set expiry for cleanup
        pipe.expire(key, self.config.window_seconds + 1)
        
        results = await pipe.execute()
        current_count = results[1]
        
        # Check if limit exceeded
        allowed = current_count < self.config.max_requests
        requests_remaining = max(0, self.config.max_requests - current_count - 1)
        
        # Calculate reset time (start of next window)
        reset_time = current_time + self.config.window_seconds
        
        return allowed, requests_remaining, reset_time
    
    async def _fixed_window_check(self, key: str, current_time: float) -> Tuple[bool, int, float]:
        """Implement fixed window rate limiting algorithm"""
        window_start = int(current_time // self.config.window_seconds) * self.config.window_seconds
        window_key = f"{key}:{window_start}"
        
        pipe = self.redis.pipeline()
        pipe.incr(window_key)
        pipe.expire(window_key, self.config.window_seconds)
        results = await pipe.execute()
        
        current_count = results[0]
        allowed = current_count <= self.config.max_requests
        requests_remaining = max(0, self.config.max_requests - current_count)
        reset_time = window_start + self.config.window_seconds
        
        return allowed, requests_remaining, reset_time
    
    async def _token_bucket_check(self, key: str, current_time: float) -> Tuple[bool, int, float]:
        """Implement token bucket rate limiting algorithm"""
        bucket_key = f"{key}:bucket"
        
        # Get current bucket state
        bucket_data = await self.redis.hgetall(bucket_key)
        
        if bucket_data:
            tokens = float(bucket_data.get('tokens', 0))
            last_refill = float(bucket_data.get('last_refill', current_time))
        else:
            tokens = self.config.max_requests
            last_refill = current_time
        
        # Calculate tokens to add based on time elapsed
        time_elapsed = current_time - last_refill
        tokens_to_add = time_elapsed * (self.config.max_requests / self.config.window_seconds)
        tokens = min(self.config.max_requests, tokens + tokens_to_add)
        
        # Check if request can be processed
        if tokens >= 1:
            tokens -= 1
            allowed = True
        else:
            allowed = False
        
        # Update bucket state
        await self.redis.hset(bucket_key, mapping={
            'tokens': tokens,
            'last_refill': current_time
        })
        await self.redis.expire(bucket_key, self.config.window_seconds * 2)
        
        requests_remaining = int(tokens)
        reset_time = current_time + ((1 - tokens) / (self.config.max_requests / self.config.window_seconds))
        
        return allowed, requests_remaining, reset_time
    
    async def check_rate_limit(self, identifier: str, endpoint: str = None, 
                              current_time: float = None) -> RateLimitResult:
        """Check if request should be rate limited"""
        if current_time is None:
            current_time = time.time()
        
        # Check whitelist first
        if self._is_whitelisted(identifier):
            return RateLimitResult(
                allowed=True,
                requests_remaining=self.config.max_requests,
                reset_time=current_time + self.config.window_seconds
            )
        
        # Check blacklist
        if self._is_blacklisted(identifier):
            return RateLimitResult(
                allowed=False,
                requests_remaining=0,
                reset_time=current_time + self.config.window_seconds,
                blocked_reason="IP blacklisted"
            )
        
        key = self._generate_key(identifier, endpoint)
        
        # Apply rate limiting algorithm
        try:
            if self.config.limit_type == RateLimitType.SLIDING_WINDOW:
                allowed, remaining, reset_time = await self._sliding_window_check(key, current_time)
            elif self.config.limit_type == RateLimitType.FIXED_WINDOW:
                allowed, remaining, reset_time = await self._fixed_window_check(key, current_time)
            elif self.config.limit_type == RateLimitType.TOKEN_BUCKET:
                allowed, remaining, reset_time = await self._token_bucket_check(key, current_time)
            else:
                raise ValueError(f"Unsupported rate limit type: {self.config.limit_type}")
            
            # Get current usage for monitoring
            if self.config.limit_type == RateLimitType.SLIDING_WINDOW:
                current_usage = await self.redis.zcard(key)
            else:
                current_usage = self.config.max_requests - remaining
            
            result = RateLimitResult(
                allowed=allowed,
                requests_remaining=remaining,
                reset_time=reset_time,
                current_usage=current_usage
            )
            
            if not allowed:
                result.retry_after = int(reset_time - current_time)
                result.blocked_reason = "Rate limit exceeded"
            
            return result
            
        except Exception as e:
            logger.error(f"Rate limit check failed for {identifier}: {e}")
            # Fail open - allow request if Redis is down
            return RateLimitResult(
                allowed=True,
                requests_remaining=self.config.max_requests,
                reset_time=current_time + self.config.window_seconds
            )
    
    async def get_usage_stats(self, identifier: str, endpoint: str = None) -> Dict[str, Any]:
        """Get current usage statistics for monitoring"""
        key = self._generate_key(identifier, endpoint)
        current_time = time.time()
        
        try:
            if self.config.limit_type == RateLimitType.SLIDING_WINDOW:
                window_start = current_time - self.config.window_seconds
                await self.redis.zremrangebyscore(key, 0, window_start)
                current_usage = await self.redis.zcard(key)
            else:
                # For fixed window and token bucket, estimate usage
                current_usage = 0
            
            return {
                'identifier': identifier,
                'endpoint': endpoint,
                'current_usage': current_usage,
                'max_requests': self.config.max_requests,
                'window_seconds': self.config.window_seconds,
                'usage_percentage': (current_usage / self.config.max_requests) * 100,
                'rate_limit_type': self.config.limit_type.value,
                'timestamp': current_time
            }
        except Exception as e:
            logger.error(f"Failed to get usage stats for {identifier}: {e}")
            return {
                'identifier': identifier,
                'endpoint': endpoint,
                'error': str(e),
                'timestamp': current_time
            }
    
    async def reset_rate_limit(self, identifier: str, endpoint: str = None) -> bool:
        """Reset rate limit for a specific identifier"""
        key = self._generate_key(identifier, endpoint)
        
        try:
            # Delete all rate limit data for this identifier
            await self.redis.delete(key)
            if self.config.limit_type == RateLimitType.TOKEN_BUCKET:
                await self.redis.delete(f"{key}:bucket")
            
            logger.info(f"Rate limit reset for {identifier}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset rate limit for {identifier}: {e}")
            return False


class RateLimitMiddleware:
    """FastAPI middleware for rate limiting"""
    
    def __init__(self, redis_client: redis.Redis, configs: Dict[str, RateLimitConfig]):
        self.redis = redis_client
        self.limiters = {
            name: RedisRateLimiter(redis_client, config)
            for name, config in configs.items()
        }
        self.default_limiter = list(self.limiters.values())[0] if self.limiters else None
    
    async def __call__(self, request, call_next):
        """Process request through rate limiting"""
        # Extract client IP
        client_ip = self._get_client_ip(request)
        
        # Determine which limiter to use
        limiter = self._get_limiter_for_request(request)
        
        if limiter:
            # Check rate limit
            result = await limiter.check_rate_limit(
                identifier=client_ip,
                endpoint=request.url.path
            )
            
            if not result.allowed:
                # Rate limit exceeded
                return await self._create_rate_limit_response(result)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        if limiter and 'result' in locals():
            response.headers["X-RateLimit-Limit"] = str(limiter.config.max_requests)
            response.headers["X-RateLimit-Remaining"] = str(result.requests_remaining)
            response.headers["X-RateLimit-Reset"] = str(int(result.reset_time))
        
        return response
    
    def _get_client_ip(self, request) -> str:
        """Extract client IP from request"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        return request.client.host if request.client else "unknown"
    
    def _get_limiter_for_request(self, request) -> Optional[RedisRateLimiter]:
        """Determine which rate limiter to use for this request"""
        # Simple path-based selection - can be enhanced
        path = request.url.path
        
        # Check for specific endpoint limiters
        for name, limiter in self.limiters.items():
            if name in path:
                return limiter
        
        # Return default limiter
        return self.default_limiter
    
    async def _create_rate_limit_response(self, result: RateLimitResult):
        """Create response for rate limited requests"""
        from fastapi import HTTPException
        from fastapi.responses import JSONResponse
        
        headers = {
            "X-RateLimit-Limit": "0",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(result.reset_time))
        }
        
        if result.retry_after:
            headers["Retry-After"] = str(result.retry_after)
        
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": result.blocked_reason or "Too many requests",
                "retry_after": result.retry_after
            },
            headers=headers
        )


# Example usage and configuration
DEFAULT_RATE_LIMIT_CONFIGS = {
    "api": RateLimitConfig(
        key_prefix="api_rate_limit",
        max_requests=100,
        window_seconds=60,
        limit_type=RateLimitType.SLIDING_WINDOW,
        action=RateLimitAction.BLOCK
    ),
    "auth": RateLimitConfig(
        key_prefix="auth_rate_limit",
        max_requests=10,
        window_seconds=60,
        limit_type=RateLimitType.FIXED_WINDOW,
        action=RateLimitAction.BLOCK
    ),
    "upload": RateLimitConfig(
        key_prefix="upload_rate_limit",
        max_requests=5,
        window_seconds=300,
        limit_type=RateLimitType.TOKEN_BUCKET,
        action=RateLimitAction.DELAY
    )
}