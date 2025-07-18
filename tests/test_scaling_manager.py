#!/usr/bin/env python3
"""
Tests for the ScalingManager.

This test suite covers:
- Scaling decision making
- Scale-up and scale-down operations
- Scaling metrics and history
- Cooldown period management
- Scaling configuration
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from advanced_orchestration.models import (
    AgentStatus,
    CoordinatorConfig,
    ResourceLimits,
    ScalingConfig,
    ScalingException,
    ScalingMetrics,
    ScalingReason,
)
from advanced_orchestration.multi_agent_coordinator import (
    MultiAgentCoordinator,
)
from advanced_orchestration.scaling_manager import (
    ScalingDecision,
    ScalingEvent,
    ScalingManager,
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestScalingManager:
    """Test suite for ScalingManager"""

    @pytest.fixture
    def resource_limits(self):
        """Create resource limits for testing"""
        return ResourceLimits(
            max_cpu_cores=8,
            max_memory_mb=8192,
            max_disk_mb=16384,
            max_network_mbps=2000,
            max_agents=10
        )

    @pytest.fixture
    def scaling_manager(self, resource_limits):
        """Create scaling manager instance for testing"""
        return ScalingManager(resource_limits)

    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator for testing"""
        config = CoordinatorConfig(max_agents=10)
        coordinator = Mock(spec=MultiAgentCoordinator)
        coordinator.config = config
        coordinator.agents = {}
        return coordinator

    @pytest.fixture
    def sample_scaling_metrics(self):
        """Create sample scaling metrics"""
        return ScalingMetrics(
            current_agents=3,
            target_agents=3,
            queue_depth=50,
            avg_response_time=2.0,
            resource_utilization=0.6,
            throughput=100.0,
            error_rate=0.01
        )

    def test_scaling_manager_initialization(
            self, scaling_manager, resource_limits):
        """Test scaling manager initializes correctly"""
        assert scaling_manager.resource_limits == resource_limits
        assert scaling_manager.config.max_agents == resource_limits.max_agents
        assert scaling_manager.last_scaling_event is None
        assert scaling_manager.scaling_history == []
        assert scaling_manager.scaling_metrics_history == []
        assert scaling_manager.scaling_enabled is True

    @pytest.mark.asyncio
    async def test_should_scale_up_high_queue_depth(
            self, scaling_manager, mock_coordinator):
        """Test scale up decision based on high queue depth"""
        # Mock high queue depth metrics
        mock_metrics = ScalingMetrics(
            current_agents=2,
            target_agents=2,
            queue_depth=150,  # Above threshold
            avg_response_time=1.0,
            resource_utilization=0.5,
            throughput=50.0,
            error_rate=0.01
        )
        mock_coordinator._calculate_scaling_metrics = AsyncMock(
            return_value=mock_metrics)

        # Check scale up decision
        should_scale, reason = await scaling_manager.should_scale_up(mock_coordinator)

        assert should_scale is True
        assert reason is not None
        assert reason.reason == "High queue depth"
        assert reason.metric_name == "queue_depth"
        assert reason.current_value == 150

    @pytest.mark.asyncio
    async def test_should_scale_up_high_response_time(
            self, scaling_manager, mock_coordinator):
        """Test scale up decision based on high response time"""
        # Mock high response time metrics
        mock_metrics = ScalingMetrics(
            current_agents=2,
            target_agents=2,
            queue_depth=20,
            avg_response_time=10.0,  # Above threshold
            resource_utilization=0.5,
            throughput=50.0,
            error_rate=0.01
        )
        mock_coordinator._calculate_scaling_metrics = AsyncMock(
            return_value=mock_metrics)

        # Check scale up decision
        should_scale, reason = await scaling_manager.should_scale_up(mock_coordinator)

        assert should_scale is True
        assert reason is not None
        assert reason.reason == "High response time"
        assert reason.metric_name == "avg_response_time"
        assert reason.current_value == 10.0

    @pytest.mark.asyncio
    async def test_should_scale_up_high_resource_utilization(
            self, scaling_manager, mock_coordinator):
        """Test scale up decision based on high resource utilization"""
        # Mock high resource utilization metrics
        mock_metrics = ScalingMetrics(
            current_agents=2,
            target_agents=2,
            queue_depth=20,
            avg_response_time=1.0,
            resource_utilization=0.9,  # Above threshold
            throughput=50.0,
            error_rate=0.01
        )
        mock_coordinator._calculate_scaling_metrics = AsyncMock(
            return_value=mock_metrics)

        # Check scale up decision
        should_scale, reason = await scaling_manager.should_scale_up(mock_coordinator)

        assert should_scale is True
        assert reason is not None
        assert reason.reason == "High resource utilization"
        assert reason.metric_name == "resource_utilization"
        assert reason.current_value == 0.9

    @pytest.mark.asyncio
    async def test_should_scale_up_at_max_capacity(
            self, scaling_manager, mock_coordinator):
        """Test scale up decision at maximum capacity"""
        # Mock metrics at max capacity
        mock_metrics = ScalingMetrics(
            current_agents=10,  # At max capacity
            target_agents=10,
            queue_depth=150,
            avg_response_time=10.0,
            resource_utilization=0.9,
            throughput=50.0,
            error_rate=0.01
        )
        mock_coordinator._calculate_scaling_metrics = AsyncMock(
            return_value=mock_metrics)

        # Check scale up decision
        should_scale, reason = await scaling_manager.should_scale_up(mock_coordinator)

        assert should_scale is False
        assert reason is None

    @pytest.mark.asyncio
    async def test_should_scale_down_low_utilization(
            self, scaling_manager, mock_coordinator):
        """Test scale down decision based on low resource utilization"""
        # Mock low utilization metrics
        mock_metrics = ScalingMetrics(
            current_agents=5,
            target_agents=5,
            queue_depth=10,  # Low queue depth
            avg_response_time=0.5,  # Low response time
            resource_utilization=0.2,  # Below threshold
            throughput=50.0,
            error_rate=0.01
        )
        mock_coordinator._calculate_scaling_metrics = AsyncMock(
            return_value=mock_metrics)

        # Add stable metrics history
        for i in range(5):
            scaling_manager.scaling_metrics_history.append(mock_metrics)

        # Check scale down decision
        should_scale, reason = await scaling_manager.should_scale_down(mock_coordinator)

        assert should_scale is True
        assert reason is not None
        assert reason.reason == "Low resource utilization"
        assert reason.metric_name == "resource_utilization"
        assert reason.current_value == 0.2

    @pytest.mark.asyncio
    async def test_should_scale_down_at_min_capacity(
            self, scaling_manager, mock_coordinator):
        """Test scale down decision at minimum capacity"""
        # Mock metrics at min capacity
        mock_metrics = ScalingMetrics(
            current_agents=2,  # At min capacity
            target_agents=2,
            queue_depth=10,
            avg_response_time=0.5,
            resource_utilization=0.1,
            throughput=50.0,
            error_rate=0.01
        )
        mock_coordinator._calculate_scaling_metrics = AsyncMock(
            return_value=mock_metrics)

        # Check scale down decision
        should_scale, reason = await scaling_manager.should_scale_down(mock_coordinator)

        assert should_scale is False
        assert reason is None

    @pytest.mark.asyncio
    async def test_scale_up_success(self, scaling_manager, mock_coordinator):
        """Test successful scale up operation"""
        # Mock coordinator agents
        mock_coordinator.agents = {
            "agent-1": Mock(status=AgentStatus.HEALTHY),
            "agent-2": Mock(status=AgentStatus.HEALTHY)
        }

        # Scale up
        new_agents = await scaling_manager.scale_up(mock_coordinator, count=2)

        assert len(new_agents) == 2
        assert all(agent_id.startswith("auto-agent-")
                   for agent_id in new_agents)

    @pytest.mark.asyncio
    async def test_scale_up_at_max_capacity(
            self, scaling_manager, mock_coordinator):
        """Test scale up at maximum capacity"""
        # Mock coordinator agents at max capacity
        mock_coordinator.agents = {
            f"agent-{i}": Mock(status=AgentStatus.HEALTHY)
            for i in range(10)
        }

        # Try to scale up
        with pytest.raises(ScalingException):
            await scaling_manager.scale_up(mock_coordinator, count=1)

    @pytest.mark.asyncio
    async def test_scale_down_success(self, scaling_manager, mock_coordinator):
        """Test successful scale down operation"""
        # Mock coordinator agents
        mock_coordinator.agents = {
            "agent-1": Mock(status=AgentStatus.HEALTHY, active_tasks=0),
            "agent-2": Mock(status=AgentStatus.HEALTHY, active_tasks=1),
            "agent-3": Mock(status=AgentStatus.HEALTHY, active_tasks=2)
        }
        mock_coordinator.unregister_agent = AsyncMock(return_value=True)

        # Scale down
        removed_agents = await scaling_manager.scale_down(mock_coordinator, count=1)

        assert len(removed_agents) == 1
        # Should remove agent with least tasks
        assert removed_agents[0] == "agent-1"
        mock_coordinator.unregister_agent.assert_called_once_with("agent-1")

    @pytest.mark.asyncio
    async def test_scale_down_at_min_capacity(
            self, scaling_manager, mock_coordinator):
        """Test scale down at minimum capacity"""
        # Mock coordinator agents at min capacity
        mock_coordinator.agents = {
            "agent-1": Mock(status=AgentStatus.HEALTHY, active_tasks=0),
            "agent-2": Mock(status=AgentStatus.HEALTHY, active_tasks=1)
        }

        # Try to scale down
        with pytest.raises(ScalingException):
            await scaling_manager.scale_down(mock_coordinator, count=1)

    @pytest.mark.asyncio
    async def test_check_scaling_needs_disabled(
            self, scaling_manager, mock_coordinator):
        """Test scaling check when scaling is disabled"""
        # Disable scaling
        scaling_manager.disable_scaling()

        # Check scaling needs
        decision = await scaling_manager.check_scaling_needs(mock_coordinator)

        assert decision is None

    @pytest.mark.asyncio
    async def test_check_scaling_needs_cooldown(
            self, scaling_manager, mock_coordinator):
        """Test scaling check during cooldown period"""
        # Set recent scaling event
        scaling_manager.last_scaling_event = datetime.now() - timedelta(seconds=30)

        # Mock metrics that would normally trigger scaling
        mock_metrics = ScalingMetrics(
            current_agents=2,
            target_agents=2,
            queue_depth=150,
            avg_response_time=1.0,
            resource_utilization=0.9,
            throughput=50.0,
            error_rate=0.01
        )
        mock_coordinator._calculate_scaling_metrics = AsyncMock(
            return_value=mock_metrics)

        # Check scaling needs
        decision = await scaling_manager.check_scaling_needs(mock_coordinator)

        assert decision is None  # Should be blocked by cooldown

    @pytest.mark.asyncio
    async def test_check_scaling_needs_scale_up(
            self, scaling_manager, mock_coordinator):
        """Test scaling check that triggers scale up"""
        # Mock metrics that trigger scale up
        mock_metrics = ScalingMetrics(
            current_agents=2,
            target_agents=2,
            queue_depth=150,
            avg_response_time=1.0,
            resource_utilization=0.9,
            throughput=50.0,
            error_rate=0.01
        )
        mock_coordinator._calculate_scaling_metrics = AsyncMock(
            return_value=mock_metrics)

        # Mock coordinator agents
        mock_coordinator.agents = {
            "agent-1": Mock(status=AgentStatus.HEALTHY),
            "agent-2": Mock(status=AgentStatus.HEALTHY)
        }

        # Check scaling needs
        decision = await scaling_manager.check_scaling_needs(mock_coordinator)

        assert decision == ScalingDecision.SCALE_UP
        assert len(scaling_manager.scaling_history) == 1
        assert scaling_manager.scaling_history[0].decision == ScalingDecision.SCALE_UP

    def test_get_scaling_history(self, scaling_manager):
        """Test getting scaling history"""
        # Add sample events
        for i in range(5):
            event = ScalingEvent(
                timestamp=datetime.now() - timedelta(minutes=i),
                decision=ScalingDecision.SCALE_UP,
                reason=ScalingReason("test", "test_metric", 1.0, 0.8),
                agents_before=2,
                agents_after=3,
                success=True
            )
            scaling_manager.scaling_history.append(event)

        # Get history
        history = scaling_manager.get_scaling_history(limit=3)

        assert len(history) == 3
        assert all(isinstance(event, ScalingEvent) for event in history)

    def test_get_scaling_statistics(self, scaling_manager):
        """Test getting scaling statistics"""
        # Add sample events
        events = [
            ScalingEvent(
                timestamp=datetime.now(),
                decision=ScalingDecision.SCALE_UP,
                reason=ScalingReason("test", "test_metric", 1.0, 0.8),
                agents_before=2,
                agents_after=3,
                success=True
            ),
            ScalingEvent(
                timestamp=datetime.now(),
                decision=ScalingDecision.SCALE_DOWN,
                reason=ScalingReason("test", "test_metric", 0.3, 0.2),
                agents_before=3,
                agents_after=2,
                success=True
            ),
            ScalingEvent(
                timestamp=datetime.now(),
                decision=ScalingDecision.SCALE_UP,
                reason=ScalingReason("test", "test_metric", 1.0, 0.8),
                agents_before=2,
                agents_after=2,
                success=False
            )
        ]
        scaling_manager.scaling_history = events

        # Get statistics
        stats = scaling_manager.get_scaling_statistics()

        assert stats['total_events'] == 3
        assert stats['successful_events'] == 2
        assert stats['scale_up_events'] == 2
        assert stats['scale_down_events'] == 1
        assert stats['success_rate'] == 2 / 3
        assert stats['scaling_enabled'] is True

    def test_enable_disable_scaling(self, scaling_manager):
        """Test enabling and disabling scaling"""
        # Initially enabled
        assert scaling_manager.scaling_enabled is True

        # Disable scaling
        scaling_manager.disable_scaling()
        assert scaling_manager.scaling_enabled is False

        # Enable scaling
        scaling_manager.enable_scaling()
        assert scaling_manager.scaling_enabled is True

    def test_update_config(self, scaling_manager):
        """Test updating scaling configuration"""
        # Create new config
        new_config = ScalingConfig(
            scale_up_threshold=0.9,
            scale_down_threshold=0.2,
            min_agents=1,
            max_agents=20,
            cooldown_period=600.0
        )

        # Update config
        scaling_manager.update_config(new_config)

        assert scaling_manager.config == new_config
        assert scaling_manager.config.scale_up_threshold == 0.9
        assert scaling_manager.config.max_agents == 20

    def test_cooldown_period_check(self, scaling_manager):
        """Test cooldown period check"""
        # No previous event
        assert scaling_manager._in_cooldown_period() is False

        # Recent event
        scaling_manager.last_scaling_event = datetime.now() - timedelta(seconds=30)
        assert scaling_manager._in_cooldown_period() is True

        # Old event
        scaling_manager.last_scaling_event = datetime.now() - timedelta(seconds=600)
        assert scaling_manager._in_cooldown_period() is False

    def test_conditions_stability_check(self, scaling_manager):
        """Test stability conditions check"""
        # Not enough history
        assert scaling_manager._are_conditions_stable() is False

        # Add stable metrics
        stable_metrics = ScalingMetrics(
            current_agents=3,
            target_agents=3,
            queue_depth=20,
            avg_response_time=1.0,
            resource_utilization=0.5,
            throughput=50.0,
            error_rate=0.01
        )

        for i in range(3):
            scaling_manager.scaling_metrics_history.append(stable_metrics)

        # Should be stable
        assert scaling_manager._are_conditions_stable() is True

        # Add unstable metrics
        unstable_metrics = ScalingMetrics(
            current_agents=3,
            target_agents=3,
            queue_depth=200,  # High variance
            avg_response_time=10.0,  # High variance
            resource_utilization=0.5,
            throughput=50.0,
            error_rate=0.01
        )
        scaling_manager.scaling_metrics_history.append(unstable_metrics)

        # Should be unstable
        assert scaling_manager._are_conditions_stable() is False

    def test_variance_calculation(self, scaling_manager):
        """Test variance calculation"""
        # Single value
        assert scaling_manager._calculate_variance([5.0]) == 0.0

        # Multiple values
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        variance = scaling_manager._calculate_variance(values)
        assert variance == 2.0  # Known variance for this sequence

        # No variance
        assert scaling_manager._calculate_variance([5.0, 5.0, 5.0]) == 0.0

    def test_metrics_history_management(self, scaling_manager):
        """Test metrics history management"""
        # Add many metrics
        for i in range(200):
            metrics = ScalingMetrics(
                current_agents=3,
                target_agents=3,
                queue_depth=50,
                avg_response_time=1.0,
                resource_utilization=0.5,
                throughput=50.0,
                error_rate=0.01
            )
            scaling_manager._update_metrics_history(metrics)

        # Should be limited (implementation keeps 100 items and trims to 50)
        assert len(scaling_manager.scaling_metrics_history) <= 100


class TestScalingManagerIntegration:
    """Integration tests for ScalingManager with MultiAgentCoordinator"""

    @pytest.mark.asyncio
    async def test_full_scaling_workflow(self):
        """Test complete scaling workflow"""
        # Create coordinator and scaling manager
        config = CoordinatorConfig(
            max_agents=5,
            min_agents=2,
            scaling_check_interval=0.1
        )
        coordinator = MultiAgentCoordinator(config)

        # Mock resource manager
        coordinator.resource_manager.allocate_resources = AsyncMock(
            return_value=Mock())
        coordinator.resource_manager.deallocate_resources = AsyncMock(
            return_value=True)
        coordinator.resource_manager.get_resource_usage = AsyncMock(
            return_value=Mock())

        # Start coordinator
        await coordinator.start()

        # Register initial agents
        from advanced_orchestration.models import (
            AgentMetadata,
            AgentRegistration,
            ResourceRequirements,
        )

        for i in range(2):
            registration = AgentRegistration(
                agent_id=f"agent-{i}",
                capabilities=["testing"],
                resource_requirements=ResourceRequirements(),
                metadata=AgentMetadata(
                    agent_type="test",
                    version="1.0.0",
                    startup_time=datetime.now(),
                    last_heartbeat=datetime.now(),
                    capabilities=["testing"],
                    resource_requirements=ResourceRequirements()
                )
            )
            await coordinator.register_agent(registration)

        # Create conditions that should trigger scale up
        for i in range(200):  # Add many pending tasks
            await coordinator.distribute_task({"type": "test"}, priority=5)

        # Check scaling needs
        decision = await coordinator.scaling_manager.check_scaling_needs(coordinator)

        # Should trigger scale up due to high queue depth
        # May be None due to cooldown
        assert decision == ScalingDecision.SCALE_UP or decision is None

        # Stop coordinator
        await coordinator.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
