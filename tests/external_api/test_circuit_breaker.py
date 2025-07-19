"""
Tests for Circuit Breaker component.
"""

import pytest
import asyncio
from datetime import datetime, timedelta

pytestmark = pytest.mark.asyncio

from external_api.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerConfig,
    CircuitBreakerManager,
    CircuitBreakerOpenError,
    with_circuit_breaker
)


class TestCircuitBreaker:
    """Test suite for CircuitBreaker class."""

    @pytest.fixture
    def circuit_breaker_config(self):
        """Create circuit breaker configuration."""
        return CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=5,
            success_threshold=2,
            request_timeout=1,
            sliding_window_size=10,
            minimum_requests=3,
            failure_rate_threshold=50.0
        )

    @pytest.fixture
    def circuit_breaker(self, circuit_breaker_config):
        """Create circuit breaker instance."""
        return CircuitBreaker("test-service", circuit_breaker_config)

    async def test_circuit_breaker_initialization(self, circuit_breaker):
        """Test circuit breaker initialization."""
        assert circuit_breaker.name == "test-service"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.metrics.total_requests == 0
        assert len(circuit_breaker.request_history) == 0

    async def test_successful_call(self, circuit_breaker):
        """Test successful function call through circuit breaker."""
        async def test_function():
            return "success"
        
        result = await circuit_breaker.call(test_function)
        assert result == "success"
        assert circuit_breaker.metrics.total_requests == 1
        assert circuit_breaker.metrics.successful_requests == 1
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    async def test_failed_call(self, circuit_breaker):
        """Test failed function call through circuit breaker."""
        async def test_function():
            raise Exception("Test error")
        
        with pytest.raises(Exception, match="Test error"):
            await circuit_breaker.call(test_function)
        
        assert circuit_breaker.metrics.total_requests == 1
        assert circuit_breaker.metrics.failed_requests == 1
        assert circuit_breaker.state == CircuitBreakerState.CLOSED  # Not enough failures yet

    async def test_circuit_opens_after_threshold(self, circuit_breaker):
        """Test circuit breaker opens after failure threshold."""
        async def failing_function():
            raise Exception("Service unavailable")
        
        # Fail enough times to open circuit
        for _ in range(circuit_breaker.config.failure_threshold):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_function)
        
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        assert circuit_breaker.metrics.current_consecutive_failures >= circuit_breaker.config.failure_threshold

    async def test_circuit_blocks_requests_when_open(self, circuit_breaker):
        """Test circuit breaker blocks requests when open."""
        # Force circuit to open
        await circuit_breaker.force_open("Test")
        
        async def test_function():
            return "should not execute"
        
        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.call(test_function)
        
        assert circuit_breaker.metrics.total_blocks == 1

    async def test_circuit_transitions_to_half_open(self, circuit_breaker):
        """Test circuit breaker transitions to half-open after timeout."""
        # Open the circuit
        await circuit_breaker.force_open("Test")
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Manually set failure time to past to trigger recovery
        circuit_breaker.last_failure_time = datetime.utcnow() - timedelta(
            seconds=circuit_breaker.config.recovery_timeout + 1
        )
        
        async def test_function():
            return "recovery test"
        
        # Next call should transition to half-open
        result = await circuit_breaker.call(test_function)
        assert result == "recovery test"
        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

    async def test_circuit_closes_from_half_open_on_success(self, circuit_breaker):
        """Test circuit breaker closes from half-open on sufficient successes."""
        # Set to half-open state
        circuit_breaker.state = CircuitBreakerState.HALF_OPEN
        circuit_breaker.state_changed_time = datetime.utcnow()
        
        async def successful_function():
            return "success"
        
        # Make enough successful calls to close circuit
        for _ in range(circuit_breaker.config.success_threshold):
            result = await circuit_breaker.call(successful_function)
            assert result == "success"
        
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    async def test_circuit_reopens_from_half_open_on_failure(self, circuit_breaker):
        """Test circuit breaker reopens from half-open on failure."""
        # Set to half-open state
        circuit_breaker.state = CircuitBreakerState.HALF_OPEN
        circuit_breaker.state_changed_time = datetime.utcnow()
        
        async def failing_function():
            raise Exception("Still failing")
        
        # Any failure in half-open should reopen circuit
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_function)
        
        assert circuit_breaker.state == CircuitBreakerState.OPEN

    async def test_request_timeout(self, circuit_breaker):
        """Test request timeout functionality."""
        async def slow_function():
            await asyncio.sleep(2)  # Longer than timeout
            return "slow result"
        
        with pytest.raises(asyncio.TimeoutError):
            await circuit_breaker.call(slow_function)
        
        assert circuit_breaker.metrics.failed_requests == 1

    async def test_failure_rate_threshold(self, circuit_breaker_config):
        """Test circuit opens based on failure rate threshold."""
        # Use larger window for this test
        circuit_breaker_config.sliding_window_size = 10
        circuit_breaker_config.failure_rate_threshold = 40.0  # 40% failure rate
        circuit_breaker_config.minimum_requests = 5
        
        cb = CircuitBreaker("rate-test", circuit_breaker_config)
        
        async def sometimes_failing_function():
            # Simulate 50% failure rate
            if cb.metrics.total_requests % 2 == 0:
                raise Exception("Intermittent failure")
            return "success"
        
        # Make enough requests to trigger rate-based opening
        for _ in range(6):  # 3 failures out of 6 = 50% > 40% threshold
            try:
                await cb.call(sometimes_failing_function)
            except Exception:
                pass
        
        assert cb.state == CircuitBreakerState.OPEN

    async def test_force_open_and_close(self, circuit_breaker):
        """Test manual circuit breaker control."""
        # Force open
        await circuit_breaker.force_open("Manual test")
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Force close
        await circuit_breaker.force_close("Manual recovery")
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.metrics.current_consecutive_failures == 0

    async def test_reset_circuit_breaker(self, circuit_breaker):
        """Test resetting circuit breaker to initial state."""
        # Make some requests to change state
        async def test_function():
            return "test"
        
        await circuit_breaker.call(test_function)
        assert circuit_breaker.metrics.total_requests > 0
        
        # Reset
        await circuit_breaker.reset()
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.metrics.total_requests == 0
        assert len(circuit_breaker.request_history) == 0

    async def test_get_status(self, circuit_breaker):
        """Test getting circuit breaker status."""
        async def test_function():
            return "test"
        
        # Make a successful call
        await circuit_breaker.call(test_function)
        
        status = await circuit_breaker.get_status()
        
        assert status["name"] == "test-service"
        assert status["state"] == CircuitBreakerState.CLOSED.value
        assert status["metrics"]["total_requests"] == 1
        assert status["metrics"]["successful_requests"] == 1
        assert status["metrics"]["failure_rate_percent"] == 0.0
        assert "configuration" in status
        assert "timestamps" in status

    async def test_test_service_method(self, circuit_breaker):
        """Test service testing method."""
        async def health_check():
            return True
        
        result = await circuit_breaker.test_service(health_check)
        assert result is True
        assert circuit_breaker.metrics.total_requests == 1
        assert circuit_breaker.metrics.successful_requests == 1

    async def test_test_service_failure(self, circuit_breaker):
        """Test service testing method with failure."""
        async def failing_health_check():
            return False
        
        result = await circuit_breaker.test_service(failing_health_check)
        assert result is False
        assert circuit_breaker.metrics.total_requests == 1
        assert circuit_breaker.metrics.failed_requests == 1

    async def test_concurrent_requests(self, circuit_breaker):
        """Test concurrent requests through circuit breaker."""
        async def test_function():
            await asyncio.sleep(0.01)  # Small delay
            return "success"
        
        # Execute multiple concurrent requests
        tasks = [circuit_breaker.call(test_function) for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        assert all(result == "success" for result in results)
        assert circuit_breaker.metrics.total_requests == 10
        assert circuit_breaker.metrics.successful_requests == 10

    async def test_metrics_calculation(self, circuit_breaker):
        """Test metrics calculation accuracy."""
        async def sometimes_failing():
            if circuit_breaker.metrics.total_requests % 3 == 0:
                raise Exception("Every third fails")
            return "success"
        
        # Make 9 requests (3 failures, 6 successes)
        for _ in range(9):
            try:
                await circuit_breaker.call(sometimes_failing)
            except Exception:
                pass
        
        assert circuit_breaker.metrics.total_requests == 9
        assert circuit_breaker.metrics.successful_requests == 6
        assert circuit_breaker.metrics.failed_requests == 3
        assert abs(circuit_breaker.metrics.failure_rate - 33.33) < 0.1
        assert abs(circuit_breaker.metrics.success_rate - 66.67) < 0.1


class TestCircuitBreakerManager:
    """Test suite for CircuitBreakerManager class."""

    @pytest.fixture
    def cb_manager(self):
        """Create circuit breaker manager."""
        return CircuitBreakerManager()

    async def test_manager_initialization(self, cb_manager):
        """Test manager initialization."""
        assert len(cb_manager.circuit_breakers) == 0
        assert cb_manager.default_config is not None

    async def test_get_or_create_circuit_breaker(self, cb_manager):
        """Test getting or creating circuit breaker."""
        # First call should create new circuit breaker
        cb1 = await cb_manager.get_or_create("service-1")
        assert cb1.name == "service-1"
        assert len(cb_manager.circuit_breakers) == 1
        
        # Second call should return existing circuit breaker
        cb2 = await cb_manager.get_or_create("service-1")
        assert cb1 is cb2
        assert len(cb_manager.circuit_breakers) == 1

    async def test_remove_circuit_breaker(self, cb_manager):
        """Test removing circuit breaker."""
        # Create circuit breaker
        await cb_manager.get_or_create("service-1")
        assert len(cb_manager.circuit_breakers) == 1
        
        # Remove it
        result = await cb_manager.remove("service-1")
        assert result is True
        assert len(cb_manager.circuit_breakers) == 0
        
        # Try to remove non-existent
        result = await cb_manager.remove("non-existent")
        assert result is False

    async def test_get_all_status(self, cb_manager):
        """Test getting status of all circuit breakers."""
        # Create multiple circuit breakers
        await cb_manager.get_or_create("service-1")
        await cb_manager.get_or_create("service-2")
        
        status = await cb_manager.get_all_status()
        assert len(status) == 2
        assert "service-1" in status
        assert "service-2" in status

    async def test_reset_all(self, cb_manager):
        """Test resetting all circuit breakers."""
        # Create and use circuit breakers
        cb1 = await cb_manager.get_or_create("service-1")
        cb2 = await cb_manager.get_or_create("service-2")
        
        # Make some requests
        async def test_func():
            return "test"
        
        await cb1.call(test_func)
        await cb2.call(test_func)
        
        assert cb1.metrics.total_requests > 0
        assert cb2.metrics.total_requests > 0
        
        # Reset all
        await cb_manager.reset_all()
        
        assert cb1.metrics.total_requests == 0
        assert cb2.metrics.total_requests == 0

    async def test_force_open_all(self, cb_manager):
        """Test forcing all circuit breakers open."""
        # Create circuit breakers
        cb1 = await cb_manager.get_or_create("service-1")
        cb2 = await cb_manager.get_or_create("service-2")
        
        assert cb1.state == CircuitBreakerState.CLOSED
        assert cb2.state == CircuitBreakerState.CLOSED
        
        # Force all open
        await cb_manager.force_open_all("Test scenario")
        
        assert cb1.state == CircuitBreakerState.OPEN
        assert cb2.state == CircuitBreakerState.OPEN

    async def test_get_summary_stats(self, cb_manager):
        """Test getting summary statistics."""
        # Create circuit breakers in different states
        cb1 = await cb_manager.get_or_create("service-1")
        cb2 = await cb_manager.get_or_create("service-2")
        cb3 = await cb_manager.get_or_create("service-3")
        
        # Set different states
        await cb2.force_open("Test")
        cb3.state = CircuitBreakerState.HALF_OPEN
        
        # Make some requests
        async def test_func():
            return "test"
        
        await cb1.call(test_func)
        
        stats = await cb_manager.get_summary_stats()
        
        assert stats["total_circuit_breakers"] == 3
        assert stats["states"]["closed"] == 1
        assert stats["states"]["open"] == 1
        assert stats["states"]["half_open"] == 1
        assert stats["total_requests"] == 1


class TestCircuitBreakerConvenience:
    """Test convenience functions."""

    async def test_with_circuit_breaker_function(self):
        """Test with_circuit_breaker convenience function."""
        async def test_function():
            return "success"
        
        result = await with_circuit_breaker("test-service", test_function)
        assert result == "success"

    async def test_with_circuit_breaker_failure(self):
        """Test with_circuit_breaker with failure."""
        async def failing_function():
            raise Exception("Test failure")
        
        with pytest.raises(Exception, match="Test failure"):
            await with_circuit_breaker("test-service", failing_function)

    async def test_with_circuit_breaker_custom_config(self):
        """Test with_circuit_breaker with custom configuration."""
        config = CircuitBreakerConfig(failure_threshold=1)
        
        async def failing_function():
            raise Exception("Immediate failure")
        
        # Should open after just one failure
        with pytest.raises(Exception):
            await with_circuit_breaker("test-service", failing_function, config=config)
        
        # Second call should be blocked
        with pytest.raises(CircuitBreakerOpenError):
            await with_circuit_breaker("test-service", failing_function, config=config)

    async def test_multiple_services_isolation(self):
        """Test that different services have isolated circuit breakers."""
        async def service1_func():
            raise Exception("Service 1 error")
        
        async def service2_func():
            return "Service 2 success"
        
        # Fail service 1 multiple times
        for _ in range(5):
            try:
                await with_circuit_breaker("service-1", service1_func)
            except:
                pass
        
        # Service 2 should still work (isolated circuit breaker)
        result = await with_circuit_breaker("service-2", service2_func)
        assert result == "Service 2 success"

    async def test_circuit_breaker_state_persistence(self):
        """Test that circuit breaker state persists across calls."""
        config = CircuitBreakerConfig(failure_threshold=2)
        
        async def failing_function():
            raise Exception("Persistent failure")
        
        # Fail twice to open circuit
        for _ in range(2):
            try:
                await with_circuit_breaker("persistent-service", failing_function, config=config)
            except Exception:
                pass
        
        # Third call should be blocked due to open circuit
        with pytest.raises(CircuitBreakerOpenError):
            await with_circuit_breaker("persistent-service", failing_function, config=config)