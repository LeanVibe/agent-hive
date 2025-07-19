"""
Tests for Load Balancer component.
"""

import pytest
import asyncio
from datetime import datetime, timedelta

pytestmark = pytest.mark.asyncio

from external_api.service_discovery import ServiceDiscovery, ServiceInstance, ServiceStatus
from external_api.load_balancer import (
    ServiceLoadBalancer,
    LoadBalancingAlgorithm,
    LoadBalancerInstance,
    HealthStatus
)


class TestServiceLoadBalancer:
    """Test suite for ServiceLoadBalancer class."""

    @pytest.fixture
    def service_discovery(self):
        """Create ServiceDiscovery instance."""
        return ServiceDiscovery({"health_check_interval": 1})

    @pytest.fixture
    def load_balancer(self, service_discovery):
        """Create ServiceLoadBalancer instance."""
        config = {
            "algorithm": LoadBalancingAlgorithm.HEALTH_WEIGHTED.value,
            "health_check_interval": 1,
            "circuit_breaker_threshold": 3,
            "circuit_breaker_timeout": 5,
            "sticky_sessions": True
        }
        return ServiceLoadBalancer(service_discovery, config)

    @pytest.fixture
    def sample_service_instance_1(self):
        """Create first sample service instance."""
        return ServiceInstance(
            service_id="service-001",
            service_name="test-service",
            host="localhost",
            port=8080,
            metadata={"version": "1.0.0"},
            health_check_url="http://localhost:8080/health",
            tags=["web", "api"]
        )

    @pytest.fixture
    def sample_service_instance_2(self):
        """Create second sample service instance."""
        return ServiceInstance(
            service_id="service-002",
            service_name="test-service",
            host="localhost",
            port=8081,
            metadata={"version": "1.0.1"},
            health_check_url="http://localhost:8081/health",
            tags=["web", "api"]
        )

    @pytest.fixture
    def sample_service_instance_different(self):
        """Create service instance for different service."""
        return ServiceInstance(
            service_id="other-service-001",
            service_name="other-service",
            host="localhost",
            port=9080,
            metadata={"version": "2.0.0"},
            tags=["worker"]
        )

    async def test_load_balancer_initialization(self, load_balancer):
        """Test load balancer initialization."""
        assert load_balancer.algorithm == LoadBalancingAlgorithm.HEALTH_WEIGHTED
        assert load_balancer.circuit_breaker_threshold == 3
        assert load_balancer.sticky_sessions_enabled is True
        assert len(load_balancer.instances) == 0
        assert not load_balancer._running

    async def test_start_stop_load_balancer(self, load_balancer):
        """Test starting and stopping load balancer."""
        # Test start
        await load_balancer.start()
        assert load_balancer._running is True

        # Test stop
        await load_balancer.stop()
        assert load_balancer._running is False

    async def test_add_instance_success(self, load_balancer, sample_service_instance_1):
        """Test successful instance addition."""
        result = await load_balancer.add_instance(sample_service_instance_1)
        
        assert result is True
        assert sample_service_instance_1.service_id in load_balancer.instances
        
        lb_instance = load_balancer.instances[sample_service_instance_1.service_id]
        assert lb_instance.service_instance == sample_service_instance_1
        assert lb_instance.health_status == HealthStatus.UNKNOWN

    async def test_remove_instance_success(self, load_balancer, sample_service_instance_1):
        """Test successful instance removal."""
        # Add instance first
        await load_balancer.add_instance(sample_service_instance_1)
        assert sample_service_instance_1.service_id in load_balancer.instances

        # Remove instance
        result = await load_balancer.remove_instance(sample_service_instance_1.service_id)
        
        assert result is True
        assert sample_service_instance_1.service_id not in load_balancer.instances

    async def test_remove_nonexistent_instance(self, load_balancer):
        """Test removing non-existent instance."""
        result = await load_balancer.remove_instance("nonexistent-id")
        assert result is False

    async def test_select_instance_no_instances(self, load_balancer):
        """Test selecting instance when none available."""
        instance = await load_balancer.select_instance("test-service")
        assert instance is None

    async def test_select_instance_single_healthy(self, load_balancer, sample_service_instance_1):
        """Test selecting single healthy instance."""
        # Add instance and mark as healthy
        await load_balancer.add_instance(sample_service_instance_1)
        lb_instance = load_balancer.instances[sample_service_instance_1.service_id]
        lb_instance.health_status = HealthStatus.HEALTHY

        # Select instance
        selected = await load_balancer.select_instance("test-service")
        assert selected == sample_service_instance_1

    async def test_select_instance_multiple_instances(self, load_balancer, 
                                                     sample_service_instance_1, 
                                                     sample_service_instance_2):
        """Test selecting from multiple instances."""
        # Add instances and mark as healthy
        await load_balancer.add_instance(sample_service_instance_1)
        await load_balancer.add_instance(sample_service_instance_2)
        
        for instance_id in [sample_service_instance_1.service_id, sample_service_instance_2.service_id]:
            load_balancer.instances[instance_id].health_status = HealthStatus.HEALTHY

        # Select instance multiple times (should distribute)
        selections = []
        for _ in range(10):
            selected = await load_balancer.select_instance("test-service")
            selections.append(selected.service_id)
        
        # Should have selections from both instances
        assert sample_service_instance_1.service_id in selections
        assert sample_service_instance_2.service_id in selections

    async def test_select_instance_different_algorithms(self, service_discovery, 
                                                       sample_service_instance_1, 
                                                       sample_service_instance_2):
        """Test different load balancing algorithms."""
        algorithms = [
            LoadBalancingAlgorithm.ROUND_ROBIN,
            LoadBalancingAlgorithm.RANDOM,
            LoadBalancingAlgorithm.LEAST_CONNECTIONS,
            LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN
        ]
        
        for algorithm in algorithms:
            config = {"algorithm": algorithm.value}
            lb = ServiceLoadBalancer(service_discovery, config)
            
            # Add instances
            await lb.add_instance(sample_service_instance_1)
            await lb.add_instance(sample_service_instance_2)
            
            # Mark as healthy
            for instance_id in [sample_service_instance_1.service_id, sample_service_instance_2.service_id]:
                lb.instances[instance_id].health_status = HealthStatus.HEALTHY
            
            # Test selection
            selected = await lb.select_instance("test-service")
            assert selected is not None
            assert selected.service_name == "test-service"

    async def test_sticky_sessions(self, load_balancer, sample_service_instance_1, sample_service_instance_2):
        """Test sticky session functionality."""
        # Add instances and mark as healthy
        await load_balancer.add_instance(sample_service_instance_1)
        await load_balancer.add_instance(sample_service_instance_2)
        
        for instance_id in [sample_service_instance_1.service_id, sample_service_instance_2.service_id]:
            load_balancer.instances[instance_id].health_status = HealthStatus.HEALTHY

        session_id = "test-session-123"
        
        # First selection should create sticky session
        first_selection = await load_balancer.select_instance("test-service", session_id=session_id)
        assert first_selection is not None
        
        # Subsequent selections should return same instance
        for _ in range(5):
            subsequent_selection = await load_balancer.select_instance("test-service", session_id=session_id)
            assert subsequent_selection.service_id == first_selection.service_id

    async def test_record_request_result_success(self, load_balancer, sample_service_instance_1):
        """Test recording successful request result."""
        await load_balancer.add_instance(sample_service_instance_1)
        
        # Record successful request
        await load_balancer.record_request_result(
            sample_service_instance_1.service_id, 
            success=True, 
            response_time_ms=150.0
        )
        
        lb_instance = load_balancer.instances[sample_service_instance_1.service_id]
        assert lb_instance.metrics.total_requests == 1
        assert lb_instance.metrics.successful_requests == 1
        assert lb_instance.metrics.avg_response_time_ms == 150.0
        assert lb_instance.metrics.success_rate == 100.0

    async def test_record_request_result_failure(self, load_balancer, sample_service_instance_1):
        """Test recording failed request result."""
        await load_balancer.add_instance(sample_service_instance_1)
        
        # Record failed request
        await load_balancer.record_request_result(
            sample_service_instance_1.service_id, 
            success=False, 
            response_time_ms=5000.0,
            error="Connection timeout"
        )
        
        lb_instance = load_balancer.instances[sample_service_instance_1.service_id]
        assert lb_instance.metrics.total_requests == 1
        assert lb_instance.metrics.failed_requests == 1
        assert lb_instance.metrics.success_rate == 0.0

    async def test_circuit_breaker_logic(self, load_balancer, sample_service_instance_1):
        """Test circuit breaker activation."""
        await load_balancer.add_instance(sample_service_instance_1)
        lb_instance = load_balancer.instances[sample_service_instance_1.service_id]
        lb_instance.health_status = HealthStatus.HEALTHY
        
        # Record multiple failures to trigger circuit breaker
        for _ in range(load_balancer.circuit_breaker_threshold + 1):
            await load_balancer.record_request_result(
                sample_service_instance_1.service_id, 
                success=False, 
                response_time_ms=1000.0,
                error="Service error"
            )
        
        # Circuit breaker should be open
        assert lb_instance.circuit_breaker_open is True
        assert lb_instance.is_available is False

    async def test_load_balancer_stats(self, load_balancer, sample_service_instance_1, sample_service_instance_2):
        """Test getting load balancer statistics."""
        # Add instances
        await load_balancer.add_instance(sample_service_instance_1)
        await load_balancer.add_instance(sample_service_instance_2)
        
        # Mark instances as healthy
        for instance_id in [sample_service_instance_1.service_id, sample_service_instance_2.service_id]:
            load_balancer.instances[instance_id].health_status = HealthStatus.HEALTHY
        
        # Record some requests
        await load_balancer.record_request_result(sample_service_instance_1.service_id, True, 100.0)
        await load_balancer.record_request_result(sample_service_instance_2.service_id, True, 200.0)
        
        # Get stats
        stats = await load_balancer.get_load_balancing_stats()
        
        assert stats["total_instances"] == 2
        assert stats["healthy_instances"] == 2
        assert stats["total_requests"] == 2
        assert stats["algorithm"] == LoadBalancingAlgorithm.HEALTH_WEIGHTED.value
        assert "instance_details" in stats
        assert len(stats["instance_details"]) == 2

    async def test_health_weighted_selection(self, load_balancer, sample_service_instance_1, sample_service_instance_2):
        """Test health-weighted selection algorithm."""
        # Add instances
        await load_balancer.add_instance(sample_service_instance_1)
        await load_balancer.add_instance(sample_service_instance_2)
        
        # Set different health scores
        lb_instance_1 = load_balancer.instances[sample_service_instance_1.service_id]
        lb_instance_2 = load_balancer.instances[sample_service_instance_2.service_id]
        
        lb_instance_1.health_status = HealthStatus.HEALTHY
        lb_instance_1.metrics.health_score = 90.0
        
        lb_instance_2.health_status = HealthStatus.DEGRADED
        lb_instance_2.metrics.health_score = 30.0
        
        # Test selection bias towards healthier instance
        selections = []
        for _ in range(20):
            selected = await load_balancer.select_instance("test-service")
            selections.append(selected.service_id)
        
        # Should favor the healthier instance
        instance_1_count = selections.count(sample_service_instance_1.service_id)
        instance_2_count = selections.count(sample_service_instance_2.service_id)
        
        # Instance 1 should be selected more often due to better health
        assert instance_1_count > instance_2_count

    async def test_concurrent_operations(self, load_balancer):
        """Test concurrent load balancer operations."""
        # Create multiple instances
        instances = []
        for i in range(5):
            instance = ServiceInstance(
                service_id=f"service-{i:03d}",
                service_name="test-service",
                host="localhost",
                port=8080 + i,
                metadata={"instance": i}
            )
            instances.append(instance)
        
        # Add all instances concurrently
        add_tasks = [load_balancer.add_instance(instance) for instance in instances]
        results = await asyncio.gather(*add_tasks)
        
        # All should succeed
        assert all(results)
        assert len(load_balancer.instances) == 5
        
        # Mark all as healthy
        for instance in instances:
            load_balancer.instances[instance.service_id].health_status = HealthStatus.HEALTHY
        
        # Concurrent selections
        selection_tasks = [load_balancer.select_instance("test-service") for _ in range(20)]
        selections = await asyncio.gather(*selection_tasks)
        
        # All selections should succeed
        assert all(selection is not None for selection in selections)
        assert all(selection.service_name == "test-service" for selection in selections)

    async def test_effective_weight_calculation(self, load_balancer, sample_service_instance_1):
        """Test effective weight calculation based on health."""
        await load_balancer.add_instance(sample_service_instance_1)
        lb_instance = load_balancer.instances[sample_service_instance_1.service_id]
        
        # Test healthy instance
        lb_instance.health_status = HealthStatus.HEALTHY
        lb_instance.metrics.health_score = 90.0
        lb_instance.metrics.weight = 1.0
        
        effective_weight = lb_instance.effective_weight
        assert effective_weight == 0.9  # 1.0 * (90/100)
        
        # Test degraded instance
        lb_instance.health_status = HealthStatus.DEGRADED
        lb_instance.metrics.health_score = 80.0
        
        effective_weight = lb_instance.effective_weight
        assert effective_weight == 0.4  # 1.0 * (80/100) * 0.5 (degraded factor)

    async def test_request_metadata_routing(self, load_balancer, sample_service_instance_1, sample_service_instance_2):
        """Test routing with request metadata."""
        # Add instances
        await load_balancer.add_instance(sample_service_instance_1)
        await load_balancer.add_instance(sample_service_instance_2)
        
        # Mark as healthy
        for instance_id in [sample_service_instance_1.service_id, sample_service_instance_2.service_id]:
            load_balancer.instances[instance_id].health_status = HealthStatus.HEALTHY
        
        # Test with consistent hash algorithm
        load_balancer.algorithm = LoadBalancingAlgorithm.CONSISTENT_HASH
        
        # Same client IP should get same instance
        client_ip = "192.168.1.100"
        request_metadata = {"client_ip": client_ip}
        
        first_selection = await load_balancer.select_instance(
            "test-service", request_metadata=request_metadata
        )
        
        # Multiple requests from same IP should go to same instance
        for _ in range(5):
            subsequent_selection = await load_balancer.select_instance(
                "test-service", request_metadata=request_metadata
            )
            assert subsequent_selection.service_id == first_selection.service_id

    async def test_health_monitoring_with_start_stop(self, load_balancer, sample_service_instance_1):
        """Test health monitoring when starting/stopping load balancer."""
        # Add instance
        await load_balancer.add_instance(sample_service_instance_1)
        
        # Start load balancer (should start health monitoring)
        await load_balancer.start()
        assert load_balancer._running is True
        
        # Verify health check task was created
        assert sample_service_instance_1.service_id in load_balancer._health_check_tasks
        
        # Stop load balancer
        await load_balancer.stop()
        assert load_balancer._running is False
        assert len(load_balancer._health_check_tasks) == 0

    async def test_circuit_breaker_recovery(self, load_balancer, sample_service_instance_1):
        """Test circuit breaker recovery after timeout."""
        await load_balancer.add_instance(sample_service_instance_1)
        lb_instance = load_balancer.instances[sample_service_instance_1.service_id]
        
        # Trigger circuit breaker
        for _ in range(load_balancer.circuit_breaker_threshold):
            await load_balancer.record_request_result(
                sample_service_instance_1.service_id, False, 1000.0
            )
        
        assert lb_instance.circuit_breaker_open is True
        
        # Manually set recovery time in past
        from datetime import datetime, timedelta
        lb_instance.circuit_breaker_open_until = datetime.utcnow() - timedelta(seconds=1)
        
        # Instance should be available again
        assert lb_instance.is_available is True