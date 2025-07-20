"""
Circuit Breaker Pattern Implementation for Service Discovery

Provides fault tolerance and resilience for service calls with automatic
failure detection, state management, and recovery mechanisms.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, TypeVar, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import uuid

from .service_discovery import ServiceInstance


logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5           # Failures before opening
    recovery_timeout: int = 60           # Seconds before trying half-open
    success_threshold: int = 3           # Successes to close from half-open
    request_timeout: int = 30            # Individual request timeout
    sliding_window_size: int = 20        # Window for failure calculation
    minimum_requests: int = 10           # Minimum requests before evaluation
    failure_rate_threshold: float = 50.0 # Failure rate % to open circuit


@dataclass
class RequestResult:
    """Result of a request through circuit breaker."""
    success: bool
    response_time_ms: float
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CircuitBreakerMetrics:
    """Circuit breaker metrics and statistics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_blocks: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    current_consecutive_failures: int = 0
    current_consecutive_successes: int = 0
    state_changes: int = 0
    avg_response_time_ms: float = 0.0
    
    @property
    def failure_rate(self) -> float:
        """Calculate current failure rate."""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100
    
    @property
    def success_rate(self) -> float:
        """Calculate current success rate."""
        return 100.0 - self.failure_rate


class CircuitBreaker:
    """
    Circuit Breaker implementation for service resilience.
    
    Provides automatic failure detection and recovery with configurable
    thresholds and timeouts. Prevents cascading failures in distributed systems.
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """Initialize circuit breaker."""
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # State management
        self.state = CircuitBreakerState.CLOSED
        self.last_failure_time: Optional[datetime] = None
        self.state_changed_time = datetime.utcnow()
        
        # Metrics and history
        self.metrics = CircuitBreakerMetrics()
        self.request_history: List[RequestResult] = []
        
        # Async locks for thread safety
        self._state_lock = asyncio.Lock()
        
        logger.info(f"Circuit breaker '{name}' initialized in {self.state.value} state")
    
    async def call(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: When circuit is open
            asyncio.TimeoutError: When request times out
        """
        async with self._state_lock:
            # Check if we should allow the request
            if not await self._should_allow_request():
                self.metrics.total_blocks += 1
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is {self.state.value}, request blocked"
                )
        
        # Execute request with timeout
        start_time = time.time()
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.request_timeout
            )
            
            # Record success
            response_time = (time.time() - start_time) * 1000
            await self._record_success(response_time)
            
            return result
            
        except Exception as e:
            # Record failure
            response_time = (time.time() - start_time) * 1000
            await self._record_failure(response_time, str(e))
            raise
    
    async def test_service(self, test_func: Callable[..., Awaitable[bool]], *args, **kwargs) -> bool:
        """
        Test service availability (used in half-open state).
        
        Args:
            test_func: Async function that returns bool for service health
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            True if service is healthy
        """
        try:
            start_time = time.time()
            result = await asyncio.wait_for(
                test_func(*args, **kwargs),
                timeout=self.config.request_timeout
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if result:
                await self._record_success(response_time)
            else:
                await self._record_failure(response_time, "Health check failed")
            
            return result
            
        except Exception as e:
            response_time = (time.time() - time.time()) * 1000
            await self._record_failure(response_time, str(e))
            return False
    
    async def force_open(self, reason: str = "Manual override") -> None:
        """Force circuit breaker to open state."""
        async with self._state_lock:
            await self._change_state(CircuitBreakerState.OPEN)
            logger.warning(f"Circuit breaker '{self.name}' forced open: {reason}")
    
    async def force_close(self, reason: str = "Manual override") -> None:
        """Force circuit breaker to closed state."""
        async with self._state_lock:
            await self._change_state(CircuitBreakerState.CLOSED)
            self.metrics.current_consecutive_failures = 0
            logger.info(f"Circuit breaker '{self.name}' forced closed: {reason}")
    
    async def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        async with self._state_lock:
            self.state = CircuitBreakerState.CLOSED
            self.metrics = CircuitBreakerMetrics()
            self.request_history.clear()
            self.last_failure_time = None
            self.state_changed_time = datetime.utcnow()
            
            logger.info(f"Circuit breaker '{self.name}' reset to initial state")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        time_since_state_change = (
            datetime.utcnow() - self.state_changed_time
        ).total_seconds()
        
        recent_requests = self.request_history[-self.config.sliding_window_size:]
        recent_failures = [r for r in recent_requests if not r.success]
        
        return {
            "name": self.name,
            "state": self.state.value,
            "time_in_current_state_seconds": time_since_state_change,
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "total_blocks": self.metrics.total_blocks,
                "failure_rate_percent": round(self.metrics.failure_rate, 2),
                "success_rate_percent": round(self.metrics.success_rate, 2),
                "avg_response_time_ms": round(self.metrics.avg_response_time_ms, 2),
                "consecutive_failures": self.metrics.current_consecutive_failures,
                "consecutive_successes": self.metrics.current_consecutive_successes,
                "state_changes": self.metrics.state_changes
            },
            "recent_window": {
                "size": len(recent_requests),
                "failures": len(recent_failures),
                "failure_rate_percent": (len(recent_failures) / max(1, len(recent_requests))) * 100
            },
            "configuration": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "request_timeout": self.config.request_timeout,
                "sliding_window_size": self.config.sliding_window_size,
                "minimum_requests": self.config.minimum_requests,
                "failure_rate_threshold": self.config.failure_rate_threshold
            },
            "timestamps": {
                "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
                "last_success": self.metrics.last_success_time.isoformat() if self.metrics.last_success_time else None,
                "state_changed": self.state_changed_time.isoformat()
            }
        }
    
    # Private methods
    
    async def _should_allow_request(self) -> bool:
        """Check if request should be allowed based on current state."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        if self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time:
                time_since_failure = datetime.utcnow() - self.last_failure_time
                if time_since_failure.total_seconds() >= self.config.recovery_timeout:
                    await self._change_state(CircuitBreakerState.HALF_OPEN)
                    return True
            return False
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            # Allow limited requests to test recovery
            return True
        
        return False
    
    async def _record_success(self, response_time_ms: float) -> None:
        """Record successful request."""
        self.metrics.total_requests += 1
        self.metrics.successful_requests += 1
        self.metrics.current_consecutive_successes += 1
        self.metrics.current_consecutive_failures = 0
        self.metrics.last_success_time = datetime.utcnow()
        
        # Update average response time
        if self.metrics.avg_response_time_ms == 0:
            self.metrics.avg_response_time_ms = response_time_ms
        else:
            # Exponential moving average
            self.metrics.avg_response_time_ms = (
                0.9 * self.metrics.avg_response_time_ms + 0.1 * response_time_ms
            )
        
        # Add to history
        self.request_history.append(RequestResult(
            success=True,
            response_time_ms=response_time_ms
        ))
        
        # Trim history
        if len(self.request_history) > self.config.sliding_window_size * 2:
            self.request_history = self.request_history[-self.config.sliding_window_size:]
        
        # State transition logic
        if self.state == CircuitBreakerState.HALF_OPEN:
            if self.metrics.current_consecutive_successes >= self.config.success_threshold:
                await self._change_state(CircuitBreakerState.CLOSED)
        
        logger.debug(f"Circuit breaker '{self.name}' recorded success: {response_time_ms:.2f}ms")
    
    async def _record_failure(self, response_time_ms: float, error: str) -> None:
        """Record failed request."""
        self.metrics.total_requests += 1
        self.metrics.failed_requests += 1
        self.metrics.current_consecutive_failures += 1
        self.metrics.current_consecutive_successes = 0
        self.last_failure_time = datetime.utcnow()
        
        # Add to history
        self.request_history.append(RequestResult(
            success=False,
            response_time_ms=response_time_ms,
            error=error
        ))
        
        # Trim history
        if len(self.request_history) > self.config.sliding_window_size * 2:
            self.request_history = self.request_history[-self.config.sliding_window_size:]
        
        # State transition logic
        await self._evaluate_state_transition()
        
        logger.debug(f"Circuit breaker '{self.name}' recorded failure: {error}")
    
    async def _evaluate_state_transition(self) -> None:
        """Evaluate if state should change based on current metrics."""
        if self.state == CircuitBreakerState.CLOSED:
            # Check if we should open
            should_open = False
            
            # Check consecutive failures
            if self.metrics.current_consecutive_failures >= self.config.failure_threshold:
                should_open = True
            
            # Check failure rate in sliding window
            recent_requests = self.request_history[-self.config.sliding_window_size:]
            if len(recent_requests) >= self.config.minimum_requests:
                recent_failures = [r for r in recent_requests if not r.success]
                failure_rate = (len(recent_failures) / len(recent_requests)) * 100
                
                if failure_rate >= self.config.failure_rate_threshold:
                    should_open = True
            
            if should_open:
                await self._change_state(CircuitBreakerState.OPEN)
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Any failure in half-open state should reopen circuit
            await self._change_state(CircuitBreakerState.OPEN)
    
    async def _change_state(self, new_state: CircuitBreakerState) -> None:
        """Change circuit breaker state."""
        if new_state != self.state:
            old_state = self.state
            self.state = new_state
            self.state_changed_time = datetime.utcnow()
            self.metrics.state_changes += 1
            
            logger.info(f"Circuit breaker '{self.name}' state changed: "
                       f"{old_state.value} -> {new_state.value}")


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreakerManager:
    """
    Manager for multiple circuit breakers.
    
    Provides centralized management of circuit breakers for different services
    and endpoints with shared configuration and monitoring.
    """
    
    def __init__(self, default_config: Optional[CircuitBreakerConfig] = None):
        """Initialize circuit breaker manager."""
        self.default_config = default_config or CircuitBreakerConfig()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
        
        logger.info("Circuit breaker manager initialized")
    
    async def get_or_create(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get existing circuit breaker or create new one."""
        async with self._lock:
            if name not in self.circuit_breakers:
                cb_config = config or self.default_config
                self.circuit_breakers[name] = CircuitBreaker(name, cb_config)
                logger.info(f"Created new circuit breaker: {name}")
            
            return self.circuit_breakers[name]
    
    async def remove(self, name: str) -> bool:
        """Remove circuit breaker."""
        async with self._lock:
            if name in self.circuit_breakers:
                del self.circuit_breakers[name]
                logger.info(f"Removed circuit breaker: {name}")
                return True
            return False
    
    async def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        status = {}
        for name, cb in self.circuit_breakers.items():
            status[name] = await cb.get_status()
        return status
    
    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for cb in self.circuit_breakers.values():
            await cb.reset()
        logger.info("Reset all circuit breakers")
    
    async def force_open_all(self, reason: str = "Manager override") -> None:
        """Force all circuit breakers to open state."""
        for cb in self.circuit_breakers.values():
            await cb.force_open(reason)
        logger.warning(f"Forced all circuit breakers open: {reason}")
    
    async def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for all circuit breakers."""
        if not self.circuit_breakers:
            return {
                "total_circuit_breakers": 0,
                "states": {"closed": 0, "open": 0, "half_open": 0},
                "total_requests": 0,
                "total_failures": 0,
                "total_blocks": 0
            }
        
        states = {"closed": 0, "open": 0, "half_open": 0}
        total_requests = 0
        total_failures = 0
        total_blocks = 0
        
        for cb in self.circuit_breakers.values():
            states[cb.state.value] += 1
            total_requests += cb.metrics.total_requests
            total_failures += cb.metrics.failed_requests
            total_blocks += cb.metrics.total_blocks
        
        return {
            "total_circuit_breakers": len(self.circuit_breakers),
            "states": states,
            "total_requests": total_requests,
            "total_failures": total_failures,
            "total_blocks": total_blocks,
            "overall_failure_rate": (total_failures / max(1, total_requests)) * 100
        }


# Convenience functions for common patterns

async def with_circuit_breaker(name: str, func: Callable[..., Awaitable[T]], 
                             *args, config: Optional[CircuitBreakerConfig] = None, **kwargs) -> T:
    """Execute function with circuit breaker protection."""
    # Use global manager instance
    if not hasattr(with_circuit_breaker, "_manager"):
        with_circuit_breaker._manager = CircuitBreakerManager()
    
    cb = await with_circuit_breaker._manager.get_or_create(name, config)
    return await cb.call(func, *args, **kwargs)


async def service_circuit_breaker(service_instance: ServiceInstance, 
                                func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
    """Execute function with service-specific circuit breaker."""
    cb_name = f"service_{service_instance.service_name}_{service_instance.host}_{service_instance.port}"
    return await with_circuit_breaker(cb_name, func, *args, **kwargs)