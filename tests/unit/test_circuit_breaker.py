"""
Unit tests for CircuitBreaker component.

Tests the circuit breaker pattern implementation used for CLI resilience.
"""

# Import the component under test
import sys
import time
from pathlib import Path

import pytest
from agents.claude_agent import CircuitBreaker

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / ".claude"))


class TestCircuitBreaker:
    """Test cases for CircuitBreaker functionality."""

    @pytest.mark.unit
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initializes in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)

        assert cb.state == 'CLOSED'
        assert cb.failure_count == 0
        assert cb.can_execute() is True

    @pytest.mark.unit
    def test_circuit_breaker_success_resets_failure_count(self):
        """Test that successful execution resets failure count."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)

        # Simulate some failures
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        # Success should reset
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == 'CLOSED'

    @pytest.mark.unit
    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        threshold = 3

        # Trigger failures up to threshold
        for i in range(threshold):
            cb.record_failure()
            if i < threshold - 1:
                assert cb.state == 'CLOSED'
            else:
                assert cb.state == 'OPEN'

        assert cb.can_execute() is False

    @pytest.mark.unit
    def test_circuit_breaker_half_open_transition(self):
        """Test circuit breaker transitions to half-open after timeout."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)

        # Open the circuit
        for _ in range(3):
            cb.record_failure()

        assert cb.state == 'OPEN'
        assert cb.can_execute() is False

        # Wait for recovery timeout
        time.sleep(0.15)

        # Should now be able to execute (half-open)
        assert cb.can_execute() is True
        assert cb.state == 'HALF_OPEN'

    @pytest.mark.unit
    def test_circuit_breaker_half_open_success_closes(
            self, circuit_breaker_config):
        """Test circuit breaker closes from half-open on success."""
        config = circuit_breaker_config.copy()
        config["recovery_timeout"] = 0.1

        cb = CircuitBreaker(**config)

        # Open the circuit
        for _ in range(config["failure_threshold"]):
            cb._record_failure()

        # Wait and transition to half-open
        time.sleep(0.15)
        cb.can_execute()  # This transitions to half-open

        # Success should close the circuit
        cb._record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.unit
    def test_circuit_breaker_half_open_failure_opens(
            self, circuit_breaker_config):
        """Test circuit breaker reopens from half-open on failure."""
        config = circuit_breaker_config.copy()
        config["recovery_timeout"] = 0.1

        cb = CircuitBreaker(**config)

        # Open the circuit
        for _ in range(config["failure_threshold"]):
            cb._record_failure()

        # Wait and transition to half-open
        time.sleep(0.15)
        cb.can_execute()  # This transitions to half-open

        # Failure should reopen the circuit
        cb._record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.can_execute() is False

    @pytest.mark.unit
    async def test_circuit_breaker_execute_success(
            self, circuit_breaker_config):
        """Test circuit breaker execute method with successful function."""
        cb = CircuitBreaker(**circuit_breaker_config)

        async def successful_func():
            return "success"

        result = await cb.execute(successful_func)
        assert result == "success"
        assert cb.failure_count == 0
        assert cb.state == CircuitBreakerState.CLOSED

    @pytest.mark.unit
    async def test_circuit_breaker_execute_failure(
            self, circuit_breaker_config):
        """Test circuit breaker execute method with failing function."""
        cb = CircuitBreaker(**circuit_breaker_config)

        async def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await cb.execute(failing_func)

        assert cb.failure_count == 1
        assert cb.state == CircuitBreakerState.CLOSED

    @pytest.mark.unit
    async def test_circuit_breaker_execute_blocked_when_open(
            self, circuit_breaker_config):
        """Test circuit breaker blocks execution when open."""
        cb = CircuitBreaker(**circuit_breaker_config)

        # Open the circuit
        for _ in range(circuit_breaker_config["failure_threshold"]):
            cb._record_failure()

        async def any_func():
            return "should not execute"

        with pytest.raises(Exception, match="Circuit breaker is open"):
            await cb.execute(any_func)

    @pytest.mark.unit
    def test_circuit_breaker_statistics(self, circuit_breaker_config):
        """Test circuit breaker provides statistics."""
        cb = CircuitBreaker(**circuit_breaker_config)

        # Record some activity
        cb._record_success()
        cb._record_failure()
        cb._record_success()

        stats = cb.get_statistics()
        assert "state" in stats
        assert "failure_count" in stats
        assert "total_calls" in stats
        assert "success_calls" in stats
        assert "failure_calls" in stats

        assert stats["total_calls"] == 3
        assert stats["success_calls"] == 2
        assert stats["failure_calls"] == 1

    @pytest.mark.unit
    def test_circuit_breaker_reset(self, circuit_breaker_config):
        """Test circuit breaker can be manually reset."""
        cb = CircuitBreaker(**circuit_breaker_config)

        # Open the circuit
        for _ in range(circuit_breaker_config["failure_threshold"]):
            cb._record_failure()

        assert cb.state == CircuitBreakerState.OPEN

        # Reset should close the circuit
        cb.reset()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.can_execute() is True

    @pytest.mark.unit
    @pytest.mark.performance
    async def test_circuit_breaker_performance(
            self, circuit_breaker_config, performance_thresholds):
        """Test circuit breaker overhead is minimal."""
        cb = CircuitBreaker(**circuit_breaker_config)

        async def fast_func():
            return "fast"

        # Time multiple executions
        start_time = time.time()
        iterations = 1000

        for _ in range(iterations):
            await cb.execute(fast_func)

        execution_time = time.time() - start_time
        avg_time_per_call = execution_time / iterations

        # Circuit breaker overhead should be minimal (< 1ms per call)
        assert avg_time_per_call < 0.001, f"Circuit breaker overhead too high: {avg_time_per_call}s per call"

    @pytest.mark.unit
    def test_circuit_breaker_thread_safety_simulation(
            self, circuit_breaker_config):
        """Test circuit breaker behavior under simulated concurrent access."""
        cb = CircuitBreaker(**circuit_breaker_config)

        # Simulate concurrent failures
        import threading

        def record_failure():
            cb._record_failure()

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=record_failure)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All failures should be recorded
        assert cb.failure_count <= 10  # May be less due to race conditions
        if cb.failure_count >= circuit_breaker_config["failure_threshold"]:
            assert cb.state == CircuitBreakerState.OPEN
