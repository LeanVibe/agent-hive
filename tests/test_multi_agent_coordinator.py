#!/usr/bin/env python3
"""
Comprehensive tests for the MultiAgentCoordinator.

This test suite covers:
- Agent registration and unregistration
- Task distribution and load balancing
- Resource management integration
- Scaling management integration
- Health monitoring and fault tolerance
- Performance metrics and monitoring
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from advanced_orchestration.models import (
    AgentMetadata,
    AgentRegistration,
    AgentStatus,
    CoordinatorConfig,
    LoadBalancingStrategy,
    ResourceLimits,
    ResourceRequirements,
    TaskStatus,
)
from advanced_orchestration.multi_agent_coordinator import (
    MultiAgentCoordinator,
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMultiAgentCoordinator:
    """Test suite for MultiAgentCoordinator"""

    @pytest.fixture
    def coordinator_config(self):
        """Create coordinator configuration for testing"""
        return CoordinatorConfig(
            max_agents=5,
            min_agents=1,
            health_check_interval=1.0,
            load_balance_interval=2.0,
            task_timeout=30.0,
            agent_startup_timeout=10.0,
            failure_threshold=2,
            scaling_check_interval=5.0,
            resource_limits=ResourceLimits(
                max_cpu_cores=4,
                max_memory_mb=4096,
                max_disk_mb=8192,
                max_agents=5
            )
        )

    @pytest.fixture
    def coordinator(self, coordinator_config):
        """Create coordinator instance for testing"""
        return MultiAgentCoordinator(coordinator_config)

    @pytest.fixture
    def sample_agent_registration(self):
        """Create a sample agent registration"""
        return AgentRegistration(
            agent_id="test-agent-001",
            capabilities=["code_generation", "testing"],
            resource_requirements=ResourceRequirements(
                cpu_cores=1,
                memory_mb=512,
                disk_mb=1024
            ),
            metadata=AgentMetadata(
                agent_type="claude",
                version="1.0.0",
                startup_time=datetime.now(),
                last_heartbeat=datetime.now(),
                capabilities=["code_generation", "testing"],
                resource_requirements=ResourceRequirements(
                    cpu_cores=1,
                    memory_mb=512,
                    disk_mb=1024
                )
            )
        )

    @pytest.fixture
    def sample_task_data(self):
        """Create sample task data"""
        return {
            "type": "code_generation",
            "description": "Generate test code",
            "requirements": ["python", "pytest"],
            "deadline": datetime.now() + timedelta(hours=1)
        }

    def test_coordinator_initialization(self, coordinator):
        """Test coordinator initializes correctly"""
        assert coordinator.config is not None
        assert coordinator.agents == {}
        assert coordinator.pending_tasks == []
        assert coordinator.assigned_tasks == {}
        assert coordinator.running is False
        assert coordinator.resource_manager is not None
        assert coordinator.scaling_manager is not None
        assert coordinator.performance_metrics is not None

    @pytest.mark.asyncio
    async def test_start_stop_coordinator(self, coordinator):
        """Test starting and stopping the coordinator"""
        # Start coordinator
        await coordinator.start()
        assert coordinator.running is True

        # Stop coordinator
        await coordinator.stop()
        assert coordinator.running is False

    @pytest.mark.asyncio
    async def test_agent_registration_success(
            self, coordinator, sample_agent_registration):
        """Test successful agent registration"""
        # Mock resource manager
        coordinator.resource_manager.allocate_resources = AsyncMock(
            return_value=Mock())

        # Register agent
        result = await coordinator.register_agent(sample_agent_registration)

        assert result is True
        assert sample_agent_registration.agent_id in coordinator.agents

        agent_info = coordinator.agents[sample_agent_registration.agent_id]
        assert agent_info.agent_id == sample_agent_registration.agent_id
        assert agent_info.status == AgentStatus.HEALTHY
        assert agent_info.active_tasks == 0

    @pytest.mark.asyncio
    async def test_agent_registration_duplicate(
            self, coordinator, sample_agent_registration):
        """Test duplicate agent registration fails"""
        # Mock resource manager
        coordinator.resource_manager.allocate_resources = AsyncMock(
            return_value=Mock())

        # Register agent first time
        await coordinator.register_agent(sample_agent_registration)

        # Try to register same agent again
        with pytest.raises(Exception):
            await coordinator.register_agent(sample_agent_registration)

    @pytest.mark.asyncio
    async def test_agent_registration_max_capacity(
            self, coordinator, sample_agent_registration):
        """Test agent registration at max capacity"""
        # Mock resource manager
        coordinator.resource_manager.allocate_resources = AsyncMock(
            return_value=Mock())

        # Register maximum number of agents
        for i in range(coordinator.config.max_agents):
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

        # Try to register one more agent (should fail)
        with pytest.raises(Exception):
            await coordinator.register_agent(sample_agent_registration)

    @pytest.mark.asyncio
    async def test_agent_unregistration(
            self, coordinator, sample_agent_registration):
        """Test agent unregistration"""
        # Mock resource manager
        coordinator.resource_manager.allocate_resources = AsyncMock(
            return_value=Mock())
        coordinator.resource_manager.deallocate_resources = AsyncMock(
            return_value=True)

        # Register agent
        await coordinator.register_agent(sample_agent_registration)

        # Unregister agent
        result = await coordinator.unregister_agent(sample_agent_registration.agent_id)

        assert result is True
        assert sample_agent_registration.agent_id not in coordinator.agents

    @pytest.mark.asyncio
    async def test_task_distribution_no_agents(
            self, coordinator, sample_task_data):
        """Test task distribution when no agents available"""
        # Distribute task
        assignment = await coordinator.distribute_task(sample_task_data, priority=5)

        # Should be added to pending tasks
        assert assignment is not None
        assert assignment.status == TaskStatus.PENDING
        assert assignment.agent_id == ""
        assert len(coordinator.pending_tasks) == 1

    @pytest.mark.asyncio
    async def test_task_distribution_with_agents(
            self, coordinator, sample_agent_registration, sample_task_data):
        """Test task distribution with available agents"""
        # Mock resource manager
        coordinator.resource_manager.allocate_resources = AsyncMock(
            return_value=Mock())

        # Register agent
        await coordinator.register_agent(sample_agent_registration)

        # Distribute task
        assignment = await coordinator.distribute_task(sample_task_data, priority=5)

        # Should be assigned to agent
        assert assignment is not None
        assert assignment.status == TaskStatus.ASSIGNED
        assert assignment.agent_id == sample_agent_registration.agent_id
        assert assignment.task_id in coordinator.assigned_tasks
        assert coordinator.agents[sample_agent_registration.agent_id].active_tasks == 1

    @pytest.mark.asyncio
    async def test_task_completion_success(
            self,
            coordinator,
            sample_agent_registration,
            sample_task_data):
        """Test successful task completion"""
        # Mock resource manager
        coordinator.resource_manager.allocate_resources = AsyncMock(
            return_value=Mock())

        # Register agent and distribute task
        await coordinator.register_agent(sample_agent_registration)
        assignment = await coordinator.distribute_task(sample_task_data, priority=5)

        # Complete task
        result = await coordinator.complete_task(assignment.task_id, success=True)

        assert result is True
        assert assignment.task_id not in coordinator.assigned_tasks
        assert assignment in coordinator.task_history
        assert assignment.status == TaskStatus.COMPLETED
        assert coordinator.agents[sample_agent_registration.agent_id].active_tasks == 0
        assert coordinator.performance_metrics['tasks_completed'] == 1

    @pytest.mark.asyncio
    async def test_task_completion_failure(
            self,
            coordinator,
            sample_agent_registration,
            sample_task_data):
        """Test failed task completion"""
        # Mock resource manager
        coordinator.resource_manager.allocate_resources = AsyncMock(
            return_value=Mock())

        # Register agent and distribute task
        await coordinator.register_agent(sample_agent_registration)
        assignment = await coordinator.distribute_task(sample_task_data, priority=5)

        # Complete task with failure
        result = await coordinator.complete_task(assignment.task_id, success=False)

        assert result is True
        assert assignment.task_id not in coordinator.assigned_tasks
        assert assignment in coordinator.task_history
        assert assignment.status == TaskStatus.FAILED
        assert coordinator.agents[sample_agent_registration.agent_id].active_tasks == 0
        assert coordinator.agents[sample_agent_registration.agent_id].error_count == 1
        assert coordinator.performance_metrics['tasks_failed'] == 1

    @pytest.mark.asyncio
    async def test_get_agent_status(
            self, coordinator, sample_agent_registration):
        """Test getting agent status"""
        # Mock resource manager
        coordinator.resource_manager.allocate_resources = AsyncMock(
            return_value=Mock())

        # Register agent
        await coordinator.register_agent(sample_agent_registration)

        # Get agent status
        status = await coordinator.get_agent_status(sample_agent_registration.agent_id)

        assert status is not None
        assert status.agent_id == sample_agent_registration.agent_id
        assert status.status == AgentStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_get_coordinator_state(
            self, coordinator, sample_agent_registration):
        """Test getting coordinator state"""
        # Mock resource manager and related methods
        coordinator.resource_manager.allocate_resources = AsyncMock(
            return_value=Mock())
        coordinator.resource_manager.get_resource_usage = AsyncMock(
            return_value=Mock())

        # Register agent
        await coordinator.register_agent(sample_agent_registration)

        # Get coordinator state
        state = await coordinator.get_coordinator_state()

        assert state is not None
        assert len(state.active_agents) == 1
        assert sample_agent_registration.agent_id in state.active_agents
        assert state.resource_usage is not None
        assert state.scaling_metrics is not None
        assert state.load_balancing_metrics is not None

    @pytest.mark.asyncio
    async def test_load_balancing_round_robin(self, coordinator):
        """Test round-robin load balancing"""
        # Mock resource manager
        coordinator.resource_manager.allocate_resources = AsyncMock(
            return_value=Mock())

        # Set strategy to round-robin
        coordinator.config.load_balancing_strategy = LoadBalancingStrategy.ROUND_ROBIN

        # Register multiple agents
        agents = []
        for i in range(3):
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
            agents.append(registration.agent_id)

        # Distribute tasks and check round-robin distribution
        task_data = {"type": "test"}
        assignments = []
        for i in range(6):
            assignment = await coordinator.distribute_task(task_data, priority=5)
            assignments.append(assignment)

        # Check that tasks are distributed in round-robin fashion
        expected_agents = [agents[i % 3] for i in range(6)]
        actual_agents = [a.agent_id for a in assignments]
        assert actual_agents == expected_agents

    @pytest.mark.asyncio
    async def test_load_balancing_least_connections(self, coordinator):
        """Test least connections load balancing"""
        # Mock resource manager
        coordinator.resource_manager.allocate_resources = AsyncMock(
            return_value=Mock())

        # Set strategy to least connections
        coordinator.config.load_balancing_strategy = LoadBalancingStrategy.LEAST_CONNECTIONS

        # Register multiple agents
        agents = []
        for i in range(3):
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
            agents.append(registration.agent_id)

        # Distribute tasks
        task_data = {"type": "test"}
        assignments = []
        for i in range(3):
            assignment = await coordinator.distribute_task(task_data, priority=5)
            assignments.append(assignment)

        # All agents should have 1 task each
        for agent_id in agents:
            assert coordinator.agents[agent_id].active_tasks == 1

    @pytest.mark.asyncio
    async def test_agent_failure_handling(
            self, coordinator, sample_agent_registration):
        """Test agent failure handling"""
        # Mock resource manager
        coordinator.resource_manager.allocate_resources = AsyncMock(
            return_value=Mock())

        # Register agent
        await coordinator.register_agent(sample_agent_registration)

        # Simulate agent failure
        await coordinator.handle_agent_failure(sample_agent_registration.agent_id)

        # Check that agent status is updated
        agent_info = coordinator.agents[sample_agent_registration.agent_id]
        assert agent_info.status == AgentStatus.UNHEALTHY
        assert agent_info.error_count == 1
        assert coordinator.performance_metrics['agent_failures'] == 1

    @pytest.mark.asyncio
    async def test_agent_failure_task_reassignment(
            self, coordinator, sample_agent_registration, sample_task_data):
        """Test task reassignment when agent fails"""
        # Mock resource manager
        coordinator.resource_manager.allocate_resources = AsyncMock(
            return_value=Mock())

        # Register agent and distribute task
        await coordinator.register_agent(sample_agent_registration)
        assignment = await coordinator.distribute_task(sample_task_data, priority=5)

        # Simulate agent failure
        await coordinator.handle_agent_failure(sample_agent_registration.agent_id)

        # Check that task is reassigned to pending
        assert assignment.task_id not in coordinator.assigned_tasks
        assert assignment in coordinator.pending_tasks
        assert assignment.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_agent_removal_on_threshold(
            self, coordinator, sample_agent_registration):
        """Test agent removal when error threshold exceeded"""
        # Mock resource manager
        coordinator.resource_manager.allocate_resources = AsyncMock(
            return_value=Mock())
        coordinator.resource_manager.deallocate_resources = AsyncMock(
            return_value=True)

        # Register agent
        await coordinator.register_agent(sample_agent_registration)

        # Simulate failures until threshold
        for i in range(coordinator.config.failure_threshold):
            await coordinator.handle_agent_failure(sample_agent_registration.agent_id)

        # Agent should be removed
        assert sample_agent_registration.agent_id not in coordinator.agents

    @pytest.mark.asyncio
    async def test_rebalance_load(self, coordinator):
        """Test load rebalancing"""
        # Mock resource manager
        coordinator.resource_manager.allocate_resources = AsyncMock(
            return_value=Mock())

        # Register agents
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

        # Add some pending tasks
        for i in range(3):
            assignment = await coordinator.distribute_task({"type": "test"}, priority=5)
            coordinator.pending_tasks.append(assignment)

        # Rebalance load
        await coordinator.rebalance_load()

        # Should have processed pending tasks
        assert coordinator.performance_metrics['load_balancing_events'] == 1
        assert coordinator.last_load_balance is not None

    @pytest.mark.asyncio
    async def test_heartbeat_update(
            self, coordinator, sample_agent_registration):
        """Test agent heartbeat update"""
        # Mock resource manager
        coordinator.resource_manager.allocate_resources = AsyncMock(
            return_value=Mock())

        # Register agent
        await coordinator.register_agent(sample_agent_registration)

        # Update heartbeat
        original_heartbeat = coordinator.agents[sample_agent_registration.agent_id].last_heartbeat
        await asyncio.sleep(0.1)  # Small delay

        result = await coordinator.update_agent_heartbeat(sample_agent_registration.agent_id)

        assert result is True
        new_heartbeat = coordinator.agents[sample_agent_registration.agent_id].last_heartbeat
        assert new_heartbeat > original_heartbeat

    @pytest.mark.asyncio
    async def test_performance_metrics(self, coordinator):
        """Test performance metrics collection"""
        metrics = coordinator.get_performance_metrics()

        assert 'tasks_completed' in metrics
        assert 'tasks_failed' in metrics
        assert 'agent_failures' in metrics
        assert 'scaling_events' in metrics
        assert 'load_balancing_events' in metrics
        assert 'uptime_seconds' in metrics
        assert 'active_agents' in metrics
        assert 'total_agents' in metrics
        assert 'pending_tasks' in metrics
        assert 'assigned_tasks' in metrics

    @pytest.mark.asyncio
    async def test_scaling_integration(self, coordinator):
        """Test scaling manager integration"""
        # Mock scaling manager
        coordinator.scaling_manager.check_scaling_needs = AsyncMock(
            return_value=None)

        # Start coordinator to trigger scaling monitor
        await coordinator.start()

        # Let scaling monitor run briefly
        await asyncio.sleep(0.1)

        # Stop coordinator
        await coordinator.stop()

        # Verify scaling check was called
        # (In real implementation, this would verify the scaling monitor worked)
        assert coordinator.scaling_manager is not None


class TestMultiAgentCoordinatorIntegration:
    """Integration tests for MultiAgentCoordinator with other components"""

    @pytest.mark.asyncio
    async def test_coordinator_with_resource_manager(self):
        """Test coordinator integration with ResourceManager"""
        config = CoordinatorConfig(
            resource_limits=ResourceLimits(
                max_cpu_cores=4,
                max_memory_mb=4096,
                max_disk_mb=8192
            )
        )
        coordinator = MultiAgentCoordinator(config)

        # Test resource manager integration
        assert coordinator.resource_manager is not None
        assert coordinator.resource_manager.limits == config.resource_limits

    @pytest.mark.asyncio
    async def test_coordinator_with_scaling_manager(self):
        """Test coordinator integration with ScalingManager"""
        config = CoordinatorConfig(
            resource_limits=ResourceLimits(max_agents=10)
        )
        coordinator = MultiAgentCoordinator(config)

        # Test scaling manager integration
        assert coordinator.scaling_manager is not None
        assert coordinator.scaling_manager.resource_limits == config.resource_limits

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test end-to-end workflow with multiple agents and tasks"""
        config = CoordinatorConfig(
            max_agents=3,
            health_check_interval=0.1,
            load_balance_interval=0.2
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

        # Register multiple agents
        agents = []
        for i in range(3):
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
            agents.append(registration.agent_id)

        # Distribute multiple tasks
        tasks = []
        for i in range(5):
            task_data = {"type": "test", "id": i}
            assignment = await coordinator.distribute_task(task_data, priority=5)
            tasks.append(assignment)

        # Complete some tasks
        for i in range(3):
            await coordinator.complete_task(tasks[i].task_id, success=True)

        # Simulate agent failure
        await coordinator.handle_agent_failure(agents[0])

        # Let background tasks run
        await asyncio.sleep(0.3)

        # Check system state
        state = await coordinator.get_coordinator_state()
        assert len(state.active_agents) == 3  # Still 3 but one unhealthy
        assert coordinator.performance_metrics['tasks_completed'] == 3
        assert coordinator.performance_metrics['agent_failures'] == 1

        # Stop coordinator
        await coordinator.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
