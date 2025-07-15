"""
Advanced Rate Limiting and Throttling for API Gateway

Provides sophisticated rate limiting with multiple strategies,
token bucket algorithms, and adaptive throttling.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass
import hashlib

from .models import ApiRequest


logger = logging.getLogger(__name__)


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    ADAPTIVE = "adaptive"


class ThrottleLevel(Enum):
    """Throttling levels."""
    NONE = "none"
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    BLOCKED = "blocked"


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    remaining: int
    reset_time: float
    throttle_level: ThrottleLevel
    retry_after: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    tokens: float
    refill_rate: float
    last_refill: float
    
    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens from bucket."""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self) -> None:
        """Refill tokens based on time elapsed."""
        now = time.time()
        time_elapsed = now - self.last_refill
        tokens_to_add = time_elapsed * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now


class AdvancedRateLimiter:
    """
    Advanced rate limiter with multiple strategies and adaptive throttling.
    
    Supports fixed window, sliding window, token bucket, and leaky bucket
    algorithms with intelligent throttling based on system load.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize advanced rate limiter.
        
        Args:
            config: Rate limiter configuration
        """
        self.config = config
        self.strategy = RateLimitStrategy(config.get("strategy", "token_bucket"))
        self.default_limit = config.get("default_limit", 1000)
        self.window_size = config.get("window_size", 3600)  # 1 hour
        self.enable_adaptive = config.get("enable_adaptive", True)
        
        # Storage for different rate limiting strategies
        self.fixed_windows: Dict[str, Dict[str, Any]] = {}
        self.sliding_windows: Dict[str, List[float]] = {}
        self.token_buckets: Dict[str, TokenBucket] = {}
        self.leaky_buckets: Dict[str, Dict[str, Any]] = {}
        
        # Adaptive throttling
        self.system_load_history: List[float] = []
        self.throttle_levels: Dict[str, ThrottleLevel] = {}
        self.adaptive_config = config.get("adaptive", {
            "load_threshold_light": 0.7,
            "load_threshold_moderate": 0.8,
            "load_threshold_heavy": 0.9,
            "load_threshold_blocked": 0.95
        })
        
        # Per-client rate limits
        self.client_limits: Dict[str, int] = {}
        self.client_strategies: Dict[str, RateLimitStrategy] = {}
        
        # Rate limit bypass for certain clients
        self.bypass_clients: set = set(config.get("bypass_clients", []))
        
        # Monitoring
        self.stats = {
            "requests_allowed": 0,
            "requests_blocked": 0,
            "throttle_events": 0,
            "adaptive_adjustments": 0
        }
        
        logger.info(f"AdvancedRateLimiter initialized with strategy: {self.strategy}")
    
    async def check_rate_limit(self, request: ApiRequest) -> RateLimitResult:
        """
        Check if request should be rate limited.
        
        Args:
            request: API request to check
            
        Returns:
            Rate limit result
        """
        # Get client identifier
        client_id = await self._get_client_id(request)
        
        # Check if client is bypassed
        if client_id in self.bypass_clients:
            return RateLimitResult(
                allowed=True,
                remaining=999999,
                reset_time=time.time() + self.window_size,
                throttle_level=ThrottleLevel.NONE
            )
        
        # Get rate limit configuration for client
        limit = self.client_limits.get(client_id, self.default_limit)
        strategy = self.client_strategies.get(client_id, self.strategy)
        
        # Apply adaptive throttling
        if self.enable_adaptive:
            await self._update_system_load()
            throttle_level = await self._calculate_throttle_level(client_id)
            
            # Adjust limit based on throttle level
            if throttle_level == ThrottleLevel.BLOCKED:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=time.time() + 60,  # 1 minute
                    throttle_level=throttle_level,
                    retry_after=60,
                    error_message="System overloaded. Please try again later."
                )
            elif throttle_level == ThrottleLevel.HEAVY:
                limit = int(limit * 0.2)  # 20% of normal limit
            elif throttle_level == ThrottleLevel.MODERATE:
                limit = int(limit * 0.5)  # 50% of normal limit
            elif throttle_level == ThrottleLevel.LIGHT:
                limit = int(limit * 0.8)  # 80% of normal limit
        else:
            throttle_level = ThrottleLevel.NONE
        
        # Apply rate limiting strategy
        if strategy == RateLimitStrategy.FIXED_WINDOW:
            result = await self._check_fixed_window(client_id, limit)
        elif strategy == RateLimitStrategy.SLIDING_WINDOW:
            result = await self._check_sliding_window(client_id, limit)
        elif strategy == RateLimitStrategy.TOKEN_BUCKET:
            result = await self._check_token_bucket(client_id, limit)
        elif strategy == RateLimitStrategy.LEAKY_BUCKET:
            result = await self._check_leaky_bucket(client_id, limit)
        else:
            result = await self._check_fixed_window(client_id, limit)
        
        # Update result with throttle level
        result.throttle_level = throttle_level
        
        # Update statistics
        if result.allowed:
            self.stats["requests_allowed"] += 1
        else:
            self.stats["requests_blocked"] += 1
        
        return result
    
    async def _get_client_id(self, request: ApiRequest) -> str:
        """Get client identifier for rate limiting."""
        # Try different client identification methods
        
        # 1. API Key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}"
        
        # 2. JWT Token user ID
        auth_context = getattr(request, 'auth_context', {})
        user_id = auth_context.get('user_id')
        if user_id:
            return f"user:{user_id}"
        
        # 3. Client IP
        return f"ip:{request.client_ip}"
    
    async def _check_fixed_window(self, client_id: str, limit: int) -> RateLimitResult:
        """Check rate limit using fixed window algorithm."""
        current_time = time.time()
        window_start = int(current_time // self.window_size) * self.window_size
        
        if client_id not in self.fixed_windows:
            self.fixed_windows[client_id] = {
                "count": 0,
                "window_start": window_start
            }
        
        client_window = self.fixed_windows[client_id]
        
        # Reset window if new window started
        if client_window["window_start"] != window_start:
            client_window["count"] = 0
            client_window["window_start"] = window_start
        
        # Check limit
        if client_window["count"] >= limit:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=window_start + self.window_size,
                throttle_level=ThrottleLevel.NONE,
                retry_after=window_start + self.window_size - current_time
            )
        
        # Increment count
        client_window["count"] += 1
        
        return RateLimitResult(
            allowed=True,
            remaining=limit - client_window["count"],
            reset_time=window_start + self.window_size,
            throttle_level=ThrottleLevel.NONE
        )
    
    async def _check_sliding_window(self, client_id: str, limit: int) -> RateLimitResult:
        """Check rate limit using sliding window algorithm."""
        current_time = time.time()
        window_start = current_time - self.window_size
        
        if client_id not in self.sliding_windows:
            self.sliding_windows[client_id] = []
        
        # Remove old requests
        client_requests = self.sliding_windows[client_id]
        client_requests[:] = [req_time for req_time in client_requests if req_time > window_start]
        
        # Check limit
        if len(client_requests) >= limit:
            oldest_request = min(client_requests)
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=oldest_request + self.window_size,
                throttle_level=ThrottleLevel.NONE,
                retry_after=oldest_request + self.window_size - current_time
            )
        
        # Add current request
        client_requests.append(current_time)
        
        return RateLimitResult(
            allowed=True,
            remaining=limit - len(client_requests),
            reset_time=current_time + self.window_size,
            throttle_level=ThrottleLevel.NONE
        )
    
    async def _check_token_bucket(self, client_id: str, limit: int) -> RateLimitResult:
        """Check rate limit using token bucket algorithm."""
        if client_id not in self.token_buckets:
            self.token_buckets[client_id] = TokenBucket(
                capacity=limit,
                tokens=limit,
                refill_rate=limit / self.window_size,  # tokens per second
                last_refill=time.time()
            )
        
        bucket = self.token_buckets[client_id]
        
        if bucket.consume(1):
            return RateLimitResult(
                allowed=True,
                remaining=int(bucket.tokens),
                reset_time=time.time() + (bucket.capacity - bucket.tokens) / bucket.refill_rate,
                throttle_level=ThrottleLevel.NONE
            )
        else:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=time.time() + 1 / bucket.refill_rate,
                throttle_level=ThrottleLevel.NONE,
                retry_after=1 / bucket.refill_rate
            )
    
    async def _check_leaky_bucket(self, client_id: str, limit: int) -> RateLimitResult:
        """Check rate limit using leaky bucket algorithm."""
        current_time = time.time()
        
        if client_id not in self.leaky_buckets:
            self.leaky_buckets[client_id] = {
                "volume": 0,
                "last_leak": current_time,
                "capacity": limit
            }
        
        bucket = self.leaky_buckets[client_id]
        
        # Calculate leak
        time_elapsed = current_time - bucket["last_leak"]
        leak_rate = limit / self.window_size  # leak per second
        leaked = time_elapsed * leak_rate
        
        bucket["volume"] = max(0, bucket["volume"] - leaked)
        bucket["last_leak"] = current_time
        
        # Check if we can add request
        if bucket["volume"] >= bucket["capacity"]:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=current_time + (bucket["volume"] - bucket["capacity"] + 1) / leak_rate,
                throttle_level=ThrottleLevel.NONE,
                retry_after=1 / leak_rate
            )
        
        # Add request
        bucket["volume"] += 1
        
        return RateLimitResult(
            allowed=True,
            remaining=int(bucket["capacity"] - bucket["volume"]),
            reset_time=current_time + bucket["volume"] / leak_rate,
            throttle_level=ThrottleLevel.NONE
        )
    
    async def _update_system_load(self) -> None:
        """Update system load for adaptive throttling."""
        # Simulate system load calculation
        # In production, this would monitor actual system metrics
        current_load = len(self.sliding_windows) / 1000  # Simple approximation
        
        self.system_load_history.append(current_load)
        if len(self.system_load_history) > 100:
            self.system_load_history.pop(0)
    
    async def _calculate_throttle_level(self, client_id: str) -> ThrottleLevel:
        """Calculate throttle level based on system load."""
        if not self.system_load_history:
            return ThrottleLevel.NONE
        
        avg_load = sum(self.system_load_history) / len(self.system_load_history)
        
        if avg_load >= self.adaptive_config["load_threshold_blocked"]:
            level = ThrottleLevel.BLOCKED
        elif avg_load >= self.adaptive_config["load_threshold_heavy"]:
            level = ThrottleLevel.HEAVY
        elif avg_load >= self.adaptive_config["load_threshold_moderate"]:
            level = ThrottleLevel.MODERATE
        elif avg_load >= self.adaptive_config["load_threshold_light"]:
            level = ThrottleLevel.LIGHT
        else:
            level = ThrottleLevel.NONE
        
        # Update throttle level if changed
        if self.throttle_levels.get(client_id) != level:
            self.throttle_levels[client_id] = level
            self.stats["throttle_events"] += 1
            self.stats["adaptive_adjustments"] += 1
        
        return level
    
    # Management methods
    
    def set_client_limit(self, client_id: str, limit: int, strategy: Optional[RateLimitStrategy] = None) -> None:
        """Set custom rate limit for a client."""
        self.client_limits[client_id] = limit
        if strategy:
            self.client_strategies[client_id] = strategy
        logger.info(f"Set rate limit for {client_id}: {limit} requests/{self.window_size}s")
    
    def add_bypass_client(self, client_id: str) -> None:
        """Add client to bypass list."""
        self.bypass_clients.add(client_id)
        logger.info(f"Added client {client_id} to rate limit bypass")
    
    def remove_bypass_client(self, client_id: str) -> None:
        """Remove client from bypass list."""
        self.bypass_clients.discard(client_id)
        logger.info(f"Removed client {client_id} from rate limit bypass")
    
    def reset_client_limits(self, client_id: str) -> None:
        """Reset rate limits for a client."""
        self.fixed_windows.pop(client_id, None)
        self.sliding_windows.pop(client_id, None)
        self.token_buckets.pop(client_id, None)
        self.leaky_buckets.pop(client_id, None)
        self.throttle_levels.pop(client_id, None)
        logger.info(f"Reset rate limits for client {client_id}")
    
    def get_client_status(self, client_id: str) -> Dict[str, Any]:
        """Get rate limit status for a client."""
        status = {
            "client_id": client_id,
            "limit": self.client_limits.get(client_id, self.default_limit),
            "strategy": self.client_strategies.get(client_id, self.strategy).value,
            "throttle_level": self.throttle_levels.get(client_id, ThrottleLevel.NONE).value,
            "bypassed": client_id in self.bypass_clients
        }
        
        # Add strategy-specific status
        if self.strategy == RateLimitStrategy.TOKEN_BUCKET and client_id in self.token_buckets:
            bucket = self.token_buckets[client_id]
            status["tokens_remaining"] = int(bucket.tokens)
            status["bucket_capacity"] = bucket.capacity
        
        return status
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global rate limiter statistics."""
        return {
            "strategy": self.strategy.value,
            "total_clients": len(set(
                list(self.fixed_windows.keys()) + 
                list(self.sliding_windows.keys()) + 
                list(self.token_buckets.keys()) + 
                list(self.leaky_buckets.keys())
            )),
            "bypass_clients": len(self.bypass_clients),
            "adaptive_enabled": self.enable_adaptive,
            "current_system_load": self.system_load_history[-1] if self.system_load_history else 0,
            "stats": self.stats.copy()
        }