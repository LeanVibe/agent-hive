#!/usr/bin/env python3
"""
Advanced Rate Limiting System for LeanVibe Agent Hive

Provides comprehensive rate limiting with multiple strategies and algorithms
to protect against DoS, DDoS, and abuse while maintaining optimal performance.
"""

import asyncio
import logging
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field
import json
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor

from config.auth_models import Permission


logger = logging.getLogger(__name__)


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    TOKEN_BUCKET = "token_bucket"
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    SLIDING_WINDOW_LOG = "sliding_window_log"
    DISTRIBUTED = "distributed"


class RateLimitScope(Enum):
    """Rate limit scope definitions."""
    GLOBAL = "global"
    PER_USER = "per_user"
    PER_ENDPOINT = "per_endpoint"
    PER_IP = "per_ip"
    PER_ROLE = "per_role"
    CUSTOM = "custom"


class RateLimitResult(Enum):
    """Rate limit check results."""
    ALLOWED = "allowed"
    REJECTED = "rejected"
    WARNING = "warning"


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit rule."""
    name: str
    scope: RateLimitScope
    strategy: RateLimitStrategy
    requests_per_window: int
    window_seconds: int
    burst_capacity: Optional[int] = None
    refill_rate: Optional[float] = None
    enabled: bool = True
    priority: int = 100
    target_pattern: Optional[str] = None
    custom_key_func: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RateLimitViolation:
    """Rate limit violation record."""
    violation_id: str
    key: str
    rule_name: str
    violated_at: datetime
    requests_count: int
    window_limit: int
    severity: str
    client_info: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RateLimitStatus:
    """Current rate limit status."""
    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None
    violation: Optional[RateLimitViolation] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TokenBucket:
    """Thread-safe token bucket implementation."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """Initialize token bucket."""
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens from bucket."""
        with self._lock:
            now = time.time()
            
            # Add tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            # Check if enough tokens available
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bucket status."""
        with self._lock:
            return {
                "capacity": self.capacity,
                "current_tokens": self.tokens,
                "refill_rate": self.refill_rate,
                "last_refill": self.last_refill
            }


class SlidingWindowCounter:
    """Sliding window counter for rate limiting."""
    
    def __init__(self, window_seconds: int, max_requests: int):
        """Initialize sliding window counter."""
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.requests = deque()
        self._lock = threading.Lock()
    
    def add_request(self, timestamp: Optional[float] = None) -> bool:
        """Add request and check if within limit."""
        if timestamp is None:
            timestamp = time.time()
        
        with self._lock:
            # Remove old requests outside window
            cutoff = timestamp - self.window_seconds
            while self.requests and self.requests[0] <= cutoff:
                self.requests.popleft()
            
            # Check if we can add this request
            if len(self.requests) < self.max_requests:
                self.requests.append(timestamp)
                return True
            
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current window status."""
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            # Clean old requests
            while self.requests and self.requests[0] <= cutoff:
                self.requests.popleft()
            
            return {
                "window_seconds": self.window_seconds,
                "max_requests": self.max_requests,
                "current_requests": len(self.requests),
                "remaining": max(0, self.max_requests - len(self.requests)),
                "oldest_request": self.requests[0] if self.requests else None,
                "reset_time": cutoff + self.window_seconds if self.requests else now
            }


class FixedWindowCounter:
    """Fixed window counter for rate limiting."""
    
    def __init__(self, window_seconds: int, max_requests: int):
        """Initialize fixed window counter."""
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.current_window_start = self._get_window_start(time.time())
        self.current_count = 0
        self._lock = threading.Lock()
    
    def _get_window_start(self, timestamp: float) -> float:
        """Get start of current window."""
        return timestamp - (timestamp % self.window_seconds)
    
    def add_request(self, timestamp: Optional[float] = None) -> bool:
        """Add request and check if within limit."""
        if timestamp is None:
            timestamp = time.time()
        
        with self._lock:
            window_start = self._get_window_start(timestamp)
            
            # Reset counter if new window
            if window_start != self.current_window_start:
                self.current_window_start = window_start
                self.current_count = 0
            
            # Check if we can add this request
            if self.current_count < self.max_requests:
                self.current_count += 1
                return True
            
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current window status."""
        with self._lock:
            now = time.time()
            window_start = self._get_window_start(now)
            
            # Reset if new window
            if window_start != self.current_window_start:
                self.current_window_start = window_start
                self.current_count = 0
            
            return {
                "window_seconds": self.window_seconds,
                "max_requests": self.max_requests,
                "current_requests": self.current_count,
                "remaining": max(0, self.max_requests - self.current_count),
                "window_start": self.current_window_start,
                "reset_time": self.current_window_start + self.window_seconds
            }


class RateLimiter:
    """
    Advanced rate limiting system with multiple strategies and algorithms.
    
    Features:
    - Multiple rate limiting algorithms (token bucket, sliding window, fixed window)
    - Configurable scopes (global, per-user, per-endpoint, per-IP, per-role)
    - Priority-based rule processing
    - Real-time monitoring and alerting
    - Integration with authentication and RBAC systems
    - Performance optimized with minimal overhead
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize rate limiter."""
        self.config = config or self._get_default_config()
        
        # Rate limit rules and state
        self.rules: Dict[str, RateLimitConfig] = {}
        self.limiters: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.violations: List[RateLimitViolation] = []
        
        # Performance tracking
        self.check_count = 0
        self.violation_count = 0
        self.check_times = deque(maxlen=1000)
        
        # Monitoring and alerting
        self.alert_callbacks: List[callable] = []
        self.metrics: Dict[str, Any] = defaultdict(int)
        
        # Thread safety
        self._lock = threading.RLock()
        self._cleanup_task = None
        
        # Load default rules
        self._load_default_rules()
        
        # Start background cleanup
        self._start_cleanup_task()
        
        logger.info("Advanced Rate Limiter initialized with multiple strategies")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default rate limiter configuration."""
        return {
            "global_rate_limit": {
                "requests_per_second": 1000,
                "burst_capacity": 1500
            },
            "per_user_rate_limit": {
                "requests_per_minute": 100,
                "burst_capacity": 150
            },
            "per_endpoint_rate_limit": {
                "requests_per_minute": 200,
                "burst_capacity": 300
            },
            "violation_threshold": 5,
            "cleanup_interval_seconds": 300,
            "max_violations_stored": 10000,
            "performance_target_ms": 5.0,
            "enable_monitoring": True,
            "enable_alerting": True
        }
    
    def _load_default_rules(self) -> None:
        """Load default rate limiting rules."""
        default_rules = [
            # Global system protection
            RateLimitConfig(
                name="global_protection",
                scope=RateLimitScope.GLOBAL,
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                requests_per_window=1000,
                window_seconds=1,
                burst_capacity=1500,
                refill_rate=1000.0,
                priority=10
            ),
            
            # Per-user limits
            RateLimitConfig(
                name="per_user_standard",
                scope=RateLimitScope.PER_USER,
                strategy=RateLimitStrategy.SLIDING_WINDOW,
                requests_per_window=100,
                window_seconds=60,
                priority=20
            ),
            
            # Per-endpoint limits
            RateLimitConfig(
                name="per_endpoint_standard",
                scope=RateLimitScope.PER_ENDPOINT,
                strategy=RateLimitStrategy.FIXED_WINDOW,
                requests_per_window=200,
                window_seconds=60,
                priority=30
            ),
            
            # Per-IP limits for DoS protection
            RateLimitConfig(
                name="per_ip_protection",
                scope=RateLimitScope.PER_IP,
                strategy=RateLimitStrategy.SLIDING_WINDOW,
                requests_per_window=300,
                window_seconds=60,
                priority=40
            ),
            
            # Admin endpoints strict limits
            RateLimitConfig(
                name="admin_endpoint_protection",
                scope=RateLimitScope.PER_ENDPOINT,
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                requests_per_window=10,
                window_seconds=60,
                burst_capacity=15,
                refill_rate=0.17,  # 10 requests per minute
                target_pattern="/api/v1/admin/*",
                priority=5
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: RateLimitConfig) -> bool:
        """Add a rate limiting rule."""
        try:
            with self._lock:
                self.rules[rule.name] = rule
                logger.info(f"Added rate limit rule: {rule.name}")
                return True
        except Exception as e:
            logger.error(f"Failed to add rate limit rule {rule.name}: {e}")
            return False
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a rate limiting rule."""
        try:
            with self._lock:
                if rule_name in self.rules:
                    del self.rules[rule_name]
                    # Clean up associated limiters
                    if rule_name in self.limiters:
                        del self.limiters[rule_name]
                    logger.info(f"Removed rate limit rule: {rule_name}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to remove rate limit rule {rule_name}: {e}")
            return False
    
    async def check_rate_limit(self, request_context: Dict[str, Any]) -> RateLimitStatus:
        """
        Check if request is within rate limits.
        
        Args:
            request_context: Request context including user_id, endpoint, ip, etc.
            
        Returns:
            RateLimitStatus with decision and metadata
        """
        start_time = time.time()
        
        try:
            with self._lock:
                self.check_count += 1
                
                # Extract context information
                user_id = request_context.get("user_id")
                endpoint = request_context.get("endpoint", "/")
                client_ip = request_context.get("client_ip", "unknown")
                user_roles = request_context.get("user_roles", [])
                
                # Get applicable rules sorted by priority
                applicable_rules = self._get_applicable_rules(request_context)
                
                # Check each rule
                for rule in applicable_rules:
                    if not rule.enabled:
                        continue
                    
                    # Generate limiter key
                    limiter_key = self._generate_limiter_key(rule, request_context)
                    
                    # Get or create limiter
                    limiter = self._get_or_create_limiter(rule, limiter_key)
                    
                    # Check rate limit
                    allowed = self._check_limiter(limiter, rule)
                    
                    if not allowed:
                        # Rate limit exceeded
                        violation = self._record_violation(rule, limiter_key, request_context)
                        
                        # Calculate retry after
                        retry_after = self._calculate_retry_after(limiter, rule)
                        
                        return RateLimitStatus(
                            allowed=False,
                            remaining=0,
                            reset_time=datetime.utcnow() + timedelta(seconds=retry_after),
                            retry_after=retry_after,
                            violation=violation,
                            metadata={
                                "rule_name": rule.name,
                                "rule_scope": rule.scope.value,
                                "limiter_key": limiter_key
                            }
                        )
                
                # All rules passed - calculate remaining and reset time
                remaining, reset_time = self._calculate_remaining_and_reset(applicable_rules, request_context)
                
                return RateLimitStatus(
                    allowed=True,
                    remaining=remaining,
                    reset_time=reset_time,
                    metadata={
                        "rules_checked": len(applicable_rules),
                        "check_time_ms": (time.time() - start_time) * 1000
                    }
                )
                
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Fail open for system stability
            return RateLimitStatus(
                allowed=True,
                remaining=999,
                reset_time=datetime.utcnow() + timedelta(minutes=1),
                metadata={"error": str(e)}
            )
        
        finally:
            # Track performance
            check_time = (time.time() - start_time) * 1000
            self.check_times.append(check_time)
            self.metrics["total_checks"] += 1
            self.metrics["total_check_time_ms"] += check_time
    
    def _get_applicable_rules(self, request_context: Dict[str, Any]) -> List[RateLimitConfig]:
        """Get applicable rules for request context, sorted by priority."""
        applicable = []
        
        endpoint = request_context.get("endpoint", "/")
        
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            # Check if rule applies to this request
            if rule.target_pattern:
                import fnmatch
                if not fnmatch.fnmatch(endpoint, rule.target_pattern):
                    continue
            
            applicable.append(rule)
        
        # Sort by priority (lower number = higher priority)
        return sorted(applicable, key=lambda r: r.priority)
    
    def _generate_limiter_key(self, rule: RateLimitConfig, context: Dict[str, Any]) -> str:
        """Generate unique key for rate limiter."""
        if rule.scope == RateLimitScope.GLOBAL:
            return f"{rule.name}:global"
        elif rule.scope == RateLimitScope.PER_USER:
            user_id = context.get("user_id", "anonymous")
            return f"{rule.name}:user:{user_id}"
        elif rule.scope == RateLimitScope.PER_ENDPOINT:
            endpoint = context.get("endpoint", "/")
            return f"{rule.name}:endpoint:{endpoint}"
        elif rule.scope == RateLimitScope.PER_IP:
            client_ip = context.get("client_ip", "unknown")
            return f"{rule.name}:ip:{client_ip}"
        elif rule.scope == RateLimitScope.PER_ROLE:
            roles = context.get("user_roles", [])
            role_key = ":".join(sorted(roles)) if roles else "no_role"
            return f"{rule.name}:role:{role_key}"
        else:
            # Custom key function
            if rule.custom_key_func:
                # In production, this would use a secure eval or predefined functions
                return f"{rule.name}:custom:{rule.custom_key_func}"
            return f"{rule.name}:unknown"
    
    def _get_or_create_limiter(self, rule: RateLimitConfig, key: str) -> Any:
        """Get existing limiter or create new one."""
        if key not in self.limiters[rule.name]:
            if rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
                capacity = rule.burst_capacity or rule.requests_per_window
                refill_rate = rule.refill_rate or (rule.requests_per_window / rule.window_seconds)
                self.limiters[rule.name][key] = TokenBucket(capacity, refill_rate)
            
            elif rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
                self.limiters[rule.name][key] = SlidingWindowCounter(
                    rule.window_seconds, rule.requests_per_window
                )
            
            elif rule.strategy == RateLimitStrategy.FIXED_WINDOW:
                self.limiters[rule.name][key] = FixedWindowCounter(
                    rule.window_seconds, rule.requests_per_window
                )
            
            else:
                # Default to sliding window
                self.limiters[rule.name][key] = SlidingWindowCounter(
                    rule.window_seconds, rule.requests_per_window
                )
        
        return self.limiters[rule.name][key]
    
    def _check_limiter(self, limiter: Any, rule: RateLimitConfig) -> bool:
        """Check if request is allowed by limiter."""
        if isinstance(limiter, TokenBucket):
            return limiter.consume(1)
        elif isinstance(limiter, (SlidingWindowCounter, FixedWindowCounter)):
            return limiter.add_request()
        else:
            # Unknown limiter type
            return True
    
    def _record_violation(self, rule: RateLimitConfig, key: str, context: Dict[str, Any]) -> RateLimitViolation:
        """Record rate limit violation."""
        violation = RateLimitViolation(
            violation_id=str(uuid.uuid4()),
            key=key,
            rule_name=rule.name,
            violated_at=datetime.utcnow(),
            requests_count=rule.requests_per_window + 1,  # Exceeded by 1
            window_limit=rule.requests_per_window,
            severity="high" if rule.priority < 20 else "medium",
            client_info={
                "user_id": context.get("user_id"),
                "client_ip": context.get("client_ip"),
                "endpoint": context.get("endpoint"),
                "user_agent": context.get("user_agent")
            },
            metadata=context.copy()
        )
        
        self.violations.append(violation)
        self.violation_count += 1
        
        # Keep only recent violations
        if len(self.violations) > self.config.get("max_violations_stored", 10000):
            self.violations = self.violations[-5000:]
        
        # Trigger alerts
        self._trigger_violation_alert(violation)
        
        logger.warning(f"Rate limit violation: {rule.name} for key {key}")
        return violation
    
    def _calculate_retry_after(self, limiter: Any, rule: RateLimitConfig) -> int:
        """Calculate retry after seconds."""
        if isinstance(limiter, TokenBucket):
            # Time needed to refill one token
            return max(1, int(1.0 / limiter.refill_rate))
        elif isinstance(limiter, (SlidingWindowCounter, FixedWindowCounter)):
            status = limiter.get_status()
            reset_time = status.get("reset_time", time.time() + rule.window_seconds)
            return max(1, int(reset_time - time.time()))
        else:
            return rule.window_seconds
    
    def _calculate_remaining_and_reset(self, rules: List[RateLimitConfig], 
                                     context: Dict[str, Any]) -> Tuple[int, datetime]:
        """Calculate remaining requests and reset time."""
        min_remaining = float('inf')
        earliest_reset = datetime.utcnow() + timedelta(hours=1)
        
        for rule in rules:
            key = self._generate_limiter_key(rule, context)
            if key in self.limiters.get(rule.name, {}):
                limiter = self.limiters[rule.name][key]
                status = limiter.get_status()
                
                remaining = status.get("remaining", rule.requests_per_window)
                reset_time_ts = status.get("reset_time", time.time() + rule.window_seconds)
                reset_time = datetime.fromtimestamp(reset_time_ts)
                
                min_remaining = min(min_remaining, remaining)
                earliest_reset = min(earliest_reset, reset_time)
        
        return (
            int(min_remaining) if min_remaining != float('inf') else 999,
            earliest_reset
        )
    
    def _trigger_violation_alert(self, violation: RateLimitViolation) -> None:
        """Trigger violation alert to registered callbacks."""
        for callback in self.alert_callbacks:
            try:
                callback(violation)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def add_alert_callback(self, callback: callable) -> None:
        """Add violation alert callback."""
        self.alert_callbacks.append(callback)
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get comprehensive rate limiting statistics."""
        avg_check_time = sum(self.check_times) / len(self.check_times) if self.check_times else 0
        
        return {
            "performance": {
                "total_checks": self.check_count,
                "total_violations": self.violation_count,
                "violation_rate_percent": (self.violation_count / max(1, self.check_count)) * 100,
                "avg_check_time_ms": avg_check_time,
                "max_check_time_ms": max(self.check_times) if self.check_times else 0,
                "performance_target_ms": self.config.get("performance_target_ms", 5.0),
                "performance_target_met": avg_check_time <= self.config.get("performance_target_ms", 5.0)
            },
            "rules": {
                "total_rules": len(self.rules),
                "enabled_rules": sum(1 for r in self.rules.values() if r.enabled),
                "rules_by_scope": {
                    scope.value: sum(1 for r in self.rules.values() if r.scope == scope)
                    for scope in RateLimitScope
                },
                "rules_by_strategy": {
                    strategy.value: sum(1 for r in self.rules.values() if r.strategy == strategy)
                    for strategy in RateLimitStrategy
                }
            },
            "violations": {
                "total_violations": len(self.violations),
                "recent_violations": len([v for v in self.violations 
                                        if v.violated_at > datetime.utcnow() - timedelta(hours=1)]),
                "violations_by_rule": {
                    rule_name: sum(1 for v in self.violations if v.rule_name == rule_name)
                    for rule_name in set(v.rule_name for v in self.violations)
                },
                "violations_by_severity": {
                    severity: sum(1 for v in self.violations if v.severity == severity)
                    for severity in set(v.severity for v in self.violations)
                }
            },
            "limiters": {
                "total_limiters": sum(len(limiters) for limiters in self.limiters.values()),
                "limiters_by_rule": {
                    rule_name: len(limiters) for rule_name, limiters in self.limiters.items()
                }
            },
            "configuration": {
                "cleanup_interval": self.config.get("cleanup_interval_seconds", 300),
                "max_violations_stored": self.config.get("max_violations_stored", 10000),
                "monitoring_enabled": self.config.get("enable_monitoring", True),
                "alerting_enabled": self.config.get("enable_alerting", True)
            }
        }
    
    def get_rate_limit_headers(self, status: RateLimitStatus) -> Dict[str, str]:
        """Generate rate limit headers for HTTP responses."""
        headers = {
            "X-RateLimit-Limit": str(status.remaining + (0 if status.allowed else 1)),
            "X-RateLimit-Remaining": str(status.remaining),
            "X-RateLimit-Reset": str(int(status.reset_time.timestamp()))
        }
        
        if status.retry_after:
            headers["Retry-After"] = str(status.retry_after)
        
        return headers
    
    def _start_cleanup_task(self) -> None:
        """Start background cleanup task."""
        async def cleanup_task():
            while True:
                try:
                    await asyncio.sleep(self.config.get("cleanup_interval_seconds", 300))
                    self._cleanup_expired_limiters()
                except Exception as e:
                    logger.error(f"Cleanup task error: {e}")
                    await asyncio.sleep(60)  # Wait before retrying
        
        try:
            loop = asyncio.get_running_loop()
            self._cleanup_task = loop.create_task(cleanup_task())
            logger.info("Rate limiter cleanup task started")
        except RuntimeError:
            logger.info("No event loop running, cleanup will be handled manually")
    
    def _cleanup_expired_limiters(self) -> None:
        """Clean up expired limiters to free memory."""
        with self._lock:
            cleaned_count = 0
            current_time = time.time()
            
            for rule_name, limiters in list(self.limiters.items()):
                rule = self.rules.get(rule_name)
                if not rule:
                    # Rule no longer exists, remove all its limiters
                    del self.limiters[rule_name]
                    cleaned_count += len(limiters)
                    continue
                
                # Clean expired limiters based on last activity
                expired_keys = []
                for key, limiter in limiters.items():
                    if hasattr(limiter, 'last_refill'):
                        # Token bucket - check last refill time
                        if current_time - limiter.last_refill > rule.window_seconds * 2:
                            expired_keys.append(key)
                    elif hasattr(limiter, 'requests'):
                        # Sliding window - check if no recent requests
                        if not limiter.requests or current_time - limiter.requests[-1] > rule.window_seconds * 2:
                            expired_keys.append(key)
                    elif hasattr(limiter, 'current_window_start'):
                        # Fixed window - check window age
                        if current_time - limiter.current_window_start > rule.window_seconds * 2:
                            expired_keys.append(key)
                
                for key in expired_keys:
                    del limiters[key]
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired rate limiters")
    
    def reset_user_limits(self, user_id: str) -> int:
        """Reset all rate limits for a specific user."""
        reset_count = 0
        
        with self._lock:
            for rule_name, limiters in self.limiters.items():
                keys_to_remove = [key for key in limiters.keys() if f":user:{user_id}" in key]
                for key in keys_to_remove:
                    del limiters[key]
                    reset_count += 1
        
        logger.info(f"Reset {reset_count} rate limiters for user {user_id}")
        return reset_count
    
    def reset_ip_limits(self, client_ip: str) -> int:
        """Reset all rate limits for a specific IP address."""
        reset_count = 0
        
        with self._lock:
            for rule_name, limiters in self.limiters.items():
                keys_to_remove = [key for key in limiters.keys() if f":ip:{client_ip}" in key]
                for key in keys_to_remove:
                    del limiters[key]
                    reset_count += 1
        
        logger.info(f"Reset {reset_count} rate limiters for IP {client_ip}")
        return reset_count
    
    def get_recent_violations(self, hours: int = 1) -> List[RateLimitViolation]:
        """Get recent violations within specified hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [v for v in self.violations if v.violated_at > cutoff]
    
    def export_config(self) -> Dict[str, Any]:
        """Export current rate limiter configuration."""
        return {
            "rules": {
                name: {
                    "name": rule.name,
                    "scope": rule.scope.value,
                    "strategy": rule.strategy.value,
                    "requests_per_window": rule.requests_per_window,
                    "window_seconds": rule.window_seconds,
                    "burst_capacity": rule.burst_capacity,
                    "refill_rate": rule.refill_rate,
                    "enabled": rule.enabled,
                    "priority": rule.priority,
                    "target_pattern": rule.target_pattern,
                    "metadata": rule.metadata
                }
                for name, rule in self.rules.items()
            },
            "configuration": self.config
        }
    
    def import_config(self, config_data: Dict[str, Any]) -> bool:
        """Import rate limiter configuration."""
        try:
            with self._lock:
                # Clear existing rules
                self.rules.clear()
                self.limiters.clear()
                
                # Import rules
                for rule_data in config_data.get("rules", {}).values():
                    rule = RateLimitConfig(
                        name=rule_data["name"],
                        scope=RateLimitScope(rule_data["scope"]),
                        strategy=RateLimitStrategy(rule_data["strategy"]),
                        requests_per_window=rule_data["requests_per_window"],
                        window_seconds=rule_data["window_seconds"],
                        burst_capacity=rule_data.get("burst_capacity"),
                        refill_rate=rule_data.get("refill_rate"),
                        enabled=rule_data.get("enabled", True),
                        priority=rule_data.get("priority", 100),
                        target_pattern=rule_data.get("target_pattern"),
                        metadata=rule_data.get("metadata", {})
                    )
                    self.rules[rule.name] = rule
                
                # Update configuration
                self.config.update(config_data.get("configuration", {}))
                
                logger.info(f"Imported {len(self.rules)} rate limit rules")
                return True
                
        except Exception as e:
            logger.error(f"Failed to import rate limiter config: {e}")
            return False