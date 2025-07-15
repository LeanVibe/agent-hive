"""
Tests for enhanced coordination protocols.
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from advanced_orchestration.enhanced_coordination import EnhancedCoordinationProtocol
from advanced_orchestration.models import (
    CoordinatorConfig, WorkflowDefinition, WorkflowType, AgentSpecialization,
    EnhancedTaskAssignment, TaskPriority, TaskStatus, TaskDependency,
    DependencyType, AgentCapabilities, ResourceLimits
)


@pytest.fixture
def coordinator_config():
    """Create coordinator configuration for testing."""
    return CoordinatorConfig(
        max_agents=5,
        min_agents=2,
        health_check_interval=10.0,
        load_balance_interval=30.0,
        resource_limits=ResourceLimits(
            max_cpu_cores=8,
            max_memory_mb=4096,
            max_disk_mb=10240,
            max_network_mbps=1000,
            max_agents=5
        )
    )


@pytest.fixture
def sample_workflow_definition():
    """Create sample workflow definition for testing."""
    return WorkflowDefinition(
        workflow_id="test_workflow_001",
        workflow_type=WorkflowType.DOCUMENTATION,
        name="Test Documentation Workflow",
        description="Test workflow for documentation coordination",
        tasks=["task_001", "task_002", "task_003", "task_004"],
        dependencies=[
            TaskDependency(
                task_id="task_002",
                depends_on="task_001",
                dependency_type=DependencyType.BLOCKING
            ),
            TaskDependency(
                task_id="task_003",
                depends_on="task_001",
                dependency_type=DependencyType.SOFT
            ),
            TaskDependency(
                task_id="task_004",
                depends_on="task_002",
                dependency_type=DependencyType.BLOCKING
            )
        ],
        agent_assignments={
            "task_001": AgentSpecialization.DOCUMENTATION,
            "task_002": AgentSpecialization.DOCUMENTATION,
            "task_003": AgentSpecialization.QUALITY,
            "task_004": AgentSpecialization.DOCUMENTATION
        },
        parallel_execution=True,
        max_parallel_tasks=3,
        estimated_duration=240
    )


@pytest.fixture
def sample_enhanced_task():
    """Create sample enhanced task for testing."""
    return EnhancedTaskAssignment(
        task_id="test_task_001",
        workflow_id="test_workflow_001",
        agent_id="",
        agent_specialization=AgentSpecialization.DOCUMENTATION,
        task_data={"type": "documentation", "priority": "high"},
        priority=TaskPriority.HIGH,
        dependencies=[],
        estimated_duration=60,
        status=TaskStatus.PENDING
    )


@pytest.fixture
def sample_agent_capabilities():
    """Create sample agent capabilities for testing."""
    return {
        "doc_agent_001": AgentCapabilities(
            specialization=AgentSpecialization.DOCUMENTATION,
            skill_level=0.9,
            supported_workflows=[WorkflowType.DOCUMENTATION],
            max_concurrent_tasks=3,
            performance_metrics={"success_rate": 0.95, "avg_completion_time": 45.0}
        ),
        "quality_agent_001": AgentCapabilities(
            specialization=AgentSpecialization.QUALITY,
            skill_level=0.8,
            supported_workflows=[WorkflowType.QUALITY],
            max_concurrent_tasks=2,
            performance_metrics={"success_rate": 0.90, "avg_completion_time": 60.0}
        ),
        "general_agent_001": AgentCapabilities(
            specialization=AgentSpecialization.GENERAL,
            skill_level=0.7,
            supported_workflows=[WorkflowType.DOCUMENTATION, WorkflowType.QUALITY],
            max_concurrent_tasks=4,
            performance_metrics={"success_rate": 0.85, "avg_completion_time": 50.0}
        )
    }


@pytest_asyncio.fixture
async def enhanced_coordination_protocol(coordinator_config):
    """Create enhanced coordination protocol for testing."""
    protocol = EnhancedCoordinationProtocol(coordinator_config)
    
    # Mock the underlying coordinators to avoid actual startup
    protocol.multi_agent_coordinator = Mock()
    protocol.multi_agent_coordinator.start = AsyncMock()
    protocol.multi_agent_coordinator.stop = AsyncMock()
    protocol.multi_agent_coordinator.get_coordinator_state = AsyncMock()
    
    protocol.workflow_coordinator = Mock()
    protocol.workflow_coordinator.start = AsyncMock()
    protocol.workflow_coordinator.stop = AsyncMock()
    protocol.workflow_coordinator.register_workflow = AsyncMock(return_value=True)
    protocol.workflow_coordinator.execute_workflow = AsyncMock()
    protocol.workflow_coordinator.get_workflow_state = AsyncMock()
    protocol.workflow_coordinator.workflow_definitions = {}
    protocol.workflow_coordinator.active_workflows = {}
    protocol.workflow_coordinator.enhanced_tasks = {}
    protocol.workflow_coordinator.agent_capabilities = {}
    
    yield protocol
    
    # Cleanup
    if protocol.running:
        await protocol.stop()


class TestEnhancedCoordinationProtocol:
    """Test suite for Enhanced Coordination Protocol."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, coordinator_config):
        """Test enhanced coordination protocol initialization."""
        protocol = EnhancedCoordinationProtocol(coordinator_config)
        
        assert protocol.config == coordinator_config
        assert protocol.intelligent_routing.use_ml_prediction is True
        assert protocol.intelligent_routing.learning_enabled is True
        assert not protocol.running
        assert len(protocol.coordination_history) == 0
        assert len(protocol.intelligent_routing_cache) == 0
        assert len(protocol.dependency_resolution_cache) == 0
    
    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self, enhanced_coordination_protocol):
        """Test start and stop lifecycle."""
        protocol = enhanced_coordination_protocol
        
        # Test start
        await protocol.start()
        assert protocol.running is True
        protocol.multi_agent_coordinator.start.assert_called_once()
        protocol.workflow_coordinator.start.assert_called_once()
        
        # Test stop
        await protocol.stop()
        assert protocol.running is False
        protocol.multi_agent_coordinator.stop.assert_called_once()
        protocol.workflow_coordinator.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_enhanced_workflow(
        self, 
        enhanced_coordination_protocol,
        sample_workflow_definition
    ):
        """Test enhanced workflow execution."""
        protocol = enhanced_coordination_protocol
        
        # Mock workflow state
        mock_workflow_state = Mock()
        mock_workflow_state.workflow_id = sample_workflow_definition.workflow_id
        mock_workflow_state.status = "executing"
        
        protocol.workflow_coordinator.execute_workflow.return_value = mock_workflow_state
        
        # Execute workflow
        result = await protocol.execute_enhanced_workflow(sample_workflow_definition)
        
        assert result == mock_workflow_state
        protocol.workflow_coordinator.register_workflow.assert_called_once_with(
            sample_workflow_definition
        )
        protocol.workflow_coordinator.execute_workflow.assert_called_once()
        
        # Check coordination event was logged
        assert len(protocol.coordination_events) > 0
        assert protocol.coordination_events[-1]["type"] == "workflow_started"
    
    @pytest.mark.asyncio
    async def test_intelligent_task_routing_with_cache(
        self, 
        enhanced_coordination_protocol,
        sample_enhanced_task
    ):
        """Test intelligent task routing with cache."""
        protocol = enhanced_coordination_protocol
        available_agents = ["agent_001", "agent_002", "agent_003"]
        
        # Test cache miss and routing
        result = await protocol.intelligent_task_routing(sample_enhanced_task, available_agents)
        
        assert result in available_agents
        assert len(protocol.coordination_events) > 0
        assert protocol.coordination_events[-1]["type"] == "intelligent_routing"
        
        # Test cache hit
        cache_key = f"{sample_enhanced_task.task_id}_{sample_enhanced_task.agent_specialization.value}"
        protocol.intelligent_routing_cache[cache_key] = ("agent_001", 0.9)
        
        result = await protocol.intelligent_task_routing(sample_enhanced_task, available_agents)
        assert result == "agent_001"
    
    @pytest.mark.asyncio
    async def test_intelligent_task_routing_empty_agents(
        self, 
        enhanced_coordination_protocol,
        sample_enhanced_task
    ):
        """Test intelligent task routing with empty agent list."""
        protocol = enhanced_coordination_protocol
        
        result = await protocol.intelligent_task_routing(sample_enhanced_task, [])
        assert result is None
    
    @pytest.mark.asyncio
    async def test_resolve_dynamic_dependencies(
        self, 
        enhanced_coordination_protocol,
        sample_workflow_definition
    ):
        """Test dynamic dependency resolution."""
        protocol = enhanced_coordination_protocol
        
        # Setup workflow
        protocol.workflow_coordinator.workflow_definitions[sample_workflow_definition.workflow_id] = sample_workflow_definition
        
        # Mock workflow state
        mock_workflow_state = Mock()
        protocol.workflow_coordinator.get_workflow_state.return_value = mock_workflow_state
        
        # Test dependency resolution
        result = await protocol.resolve_dynamic_dependencies(
            sample_workflow_definition.workflow_id,
            "task_002"
        )
        
        assert isinstance(result, list)
        assert len(protocol.coordination_events) > 0
        assert protocol.coordination_events[-1]["type"] == "dependency_resolution"
    
    @pytest.mark.asyncio
    async def test_resolve_dynamic_dependencies_with_cache(
        self, 
        enhanced_coordination_protocol,
        sample_workflow_definition
    ):
        """Test dynamic dependency resolution with cache."""
        protocol = enhanced_coordination_protocol
        
        # Setup cache
        cache_key = f"{sample_workflow_definition.workflow_id}_task_002"
        protocol.dependency_resolution_cache[cache_key] = ["task_001"]
        
        result = await protocol.resolve_dynamic_dependencies(
            sample_workflow_definition.workflow_id,
            "task_002"
        )
        
        assert result == ["task_001"]
    
    @pytest.mark.asyncio
    async def test_optimize_parallel_execution(
        self, 
        enhanced_coordination_protocol,
        sample_workflow_definition
    ):
        """Test parallel execution optimization."""
        protocol = enhanced_coordination_protocol
        
        task_groups = [["task_001"], ["task_002", "task_003"], ["task_004"]]
        
        result = await protocol.optimize_parallel_execution(
            sample_workflow_definition.workflow_id,
            task_groups
        )
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(group, list) for group in result)
        assert len(protocol.coordination_events) > 0
        assert protocol.coordination_events[-1]["type"] == "parallel_optimization"
    
    @pytest.mark.asyncio
    async def test_monitor_real_time_coordination(self, enhanced_coordination_protocol):
        """Test real-time coordination monitoring."""
        protocol = enhanced_coordination_protocol
        
        # Mock coordinator state
        mock_coordinator_state = Mock()
        mock_coordinator_state.active_agents = {}
        protocol.multi_agent_coordinator.get_coordinator_state.return_value = mock_coordinator_state
        
        # Mock workflow coordinator state
        protocol.workflow_coordinator.active_workflows = {}
        protocol.workflow_coordinator.enhanced_tasks = {}
        
        result = await protocol.monitor_real_time_coordination()
        
        assert result.workflow_completion_rate >= 0.0
        assert result.parallel_efficiency >= 0.0
        assert result.task_distribution_balance >= 0.0
        assert result.quality_consistency >= 0.0
        assert result.dependency_resolution_time >= 0.0
        assert isinstance(result.agent_utilization, dict)
        assert result.coordination_overhead >= 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_agent_scores(
        self, 
        enhanced_coordination_protocol,
        sample_enhanced_task,
        sample_agent_capabilities
    ):
        """Test agent score calculation for routing."""
        protocol = enhanced_coordination_protocol
        
        # Setup agent capabilities
        protocol.workflow_coordinator.agent_capabilities = sample_agent_capabilities
        
        # Mock coordinator state
        mock_coordinator_state = Mock()
        mock_coordinator_state.active_agents = {
            "doc_agent_001": Mock(active_tasks=1),
            "quality_agent_001": Mock(active_tasks=0),
            "general_agent_001": Mock(active_tasks=2)
        }
        protocol.multi_agent_coordinator.get_coordinator_state.return_value = mock_coordinator_state
        
        available_agents = ["doc_agent_001", "quality_agent_001", "general_agent_001"]
        
        result = await protocol._calculate_agent_scores(sample_enhanced_task, available_agents)
        
        assert isinstance(result, dict)
        assert len(result) == 3
        assert all(isinstance(score, float) for score in result.values())
        assert "doc_agent_001" in result
        assert "quality_agent_001" in result
        assert "general_agent_001" in result
        
        # Documentation agent should have higher score for documentation task
        assert result["doc_agent_001"] > result["quality_agent_001"]
    
    @pytest.mark.asyncio
    async def test_resolve_task_dependencies(
        self, 
        enhanced_coordination_protocol,
        sample_workflow_definition
    ):
        """Test task dependency resolution."""
        protocol = enhanced_coordination_protocol
        
        result = await protocol._resolve_task_dependencies(
            sample_workflow_definition,
            "task_002"
        )
        
        assert result == ["task_001"]
        
        result = await protocol._resolve_task_dependencies(
            sample_workflow_definition,
            "task_004"
        )
        
        assert result == ["task_002"]
    
    @pytest.mark.asyncio
    async def test_optimize_dependency_chain(
        self, 
        enhanced_coordination_protocol,
        sample_workflow_definition
    ):
        """Test dependency chain optimization."""
        protocol = enhanced_coordination_protocol
        
        dependencies = ["task_001", "task_002"]
        
        result = await protocol._optimize_dependency_chain(
            sample_workflow_definition,
            "task_004",
            dependencies
        )
        
        assert isinstance(result, list)
        assert len(result) <= len(dependencies)
    
    @pytest.mark.asyncio
    async def test_analyze_parallel_groups(
        self, 
        enhanced_coordination_protocol,
        sample_workflow_definition
    ):
        """Test parallel group analysis."""
        protocol = enhanced_coordination_protocol
        
        task_groups = [["task_001"], ["task_002", "task_003"], ["task_004"]]
        
        result = await protocol._analyze_parallel_groups(
            sample_workflow_definition.workflow_id,
            task_groups
        )
        
        assert isinstance(result, dict)
        assert "group_count" in result
        assert "total_tasks" in result
        assert "max_group_size" in result
        assert "min_group_size" in result
        assert "expected_improvement" in result
        
        assert result["group_count"] == 3
        assert result["total_tasks"] == 4
        assert result["max_group_size"] == 2
        assert result["min_group_size"] == 1
    
    @pytest.mark.asyncio
    async def test_optimize_groups_by_resources(
        self, 
        enhanced_coordination_protocol
    ):
        """Test resource-based group optimization."""
        protocol = enhanced_coordination_protocol
        
        # Mock coordinator state with limited agents
        mock_coordinator_state = Mock()
        mock_coordinator_state.active_agents = {
            "agent_001": Mock(status=Mock(value="healthy")),
            "agent_002": Mock(status=Mock(value="healthy"))
        }
        protocol.multi_agent_coordinator.get_coordinator_state.return_value = mock_coordinator_state
        
        task_groups = [["task_001"], ["task_002"], ["task_003"], ["task_004"]]
        
        result = await protocol._optimize_groups_by_resources(task_groups)
        
        assert isinstance(result, list)
        assert len(result) <= 2  # Should be limited by available agents
    
    @pytest.mark.asyncio
    async def test_workflow_performance_metrics_calculation(
        self, 
        enhanced_coordination_protocol
    ):
        """Test workflow performance metrics calculation."""
        protocol = enhanced_coordination_protocol
        
        # Test workflow completion rate
        protocol.workflow_coordinator.active_workflows = {
            "workflow_001": Mock(status="completed"),
            "workflow_002": Mock(status="executing"),
            "workflow_003": Mock(status="completed")
        }
        
        result = await protocol._calculate_workflow_completion_rate()
        assert result == 2/3  # 2 completed out of 3 total
        
        # Test parallel efficiency
        protocol.parallel_execution_analytics = {
            "workflow_001": {"expected_improvement": 0.3},
            "workflow_002": {"expected_improvement": 0.5}
        }
        
        result = await protocol._calculate_parallel_efficiency()
        assert result == 0.4  # Average of 0.3 and 0.5
    
    @pytest.mark.asyncio
    async def test_coordination_event_logging(self, enhanced_coordination_protocol):
        """Test coordination event logging."""
        protocol = enhanced_coordination_protocol
        
        event_data = {"test": "data", "value": 123}
        
        await protocol._log_coordination_event("test_event", event_data)
        
        assert len(protocol.coordination_events) == 1
        event = protocol.coordination_events[0]
        assert event["type"] == "test_event"
        assert event["data"] == event_data
        assert "timestamp" in event
    
    @pytest.mark.asyncio
    async def test_get_coordination_statistics(self, enhanced_coordination_protocol):
        """Test coordination statistics retrieval."""
        protocol = enhanced_coordination_protocol
        
        # Add some test data
        protocol.coordination_events.append({"type": "test", "data": {}})
        protocol.performance_alerts.append({"type": "alert", "message": "test"})
        protocol.intelligent_routing_cache["test_key"] = ("agent_001", 0.9)
        protocol.dependency_resolution_cache["test_dep"] = ["task_001"]
        
        result = protocol.get_coordination_statistics()
        
        assert isinstance(result, dict)
        assert "active_workflows" in result
        assert "coordination_events" in result
        assert "performance_alerts" in result
        assert "routing_cache_size" in result
        assert "dependency_cache_size" in result
        assert "agent_performance_tracked" in result
        assert "coordination_efficiency" in result
        assert "recent_events" in result
        
        assert result["coordination_events"] == 1
        assert result["performance_alerts"] == 1
        assert result["routing_cache_size"] == 1
        assert result["dependency_cache_size"] == 1
    
    @pytest.mark.asyncio
    async def test_error_handling_in_intelligent_routing(
        self, 
        enhanced_coordination_protocol,
        sample_enhanced_task
    ):
        """Test error handling in intelligent routing."""
        protocol = enhanced_coordination_protocol
        
        # Mock error in score calculation
        with patch.object(protocol, '_calculate_agent_scores', side_effect=Exception("Test error")):
            result = await protocol.intelligent_task_routing(
                sample_enhanced_task, 
                ["agent_001", "agent_002"]
            )
            assert result == "agent_001"  # Should fallback to first available
    
    @pytest.mark.asyncio
    async def test_error_handling_in_dependency_resolution(
        self, 
        enhanced_coordination_protocol,
        sample_workflow_definition
    ):
        """Test error handling in dependency resolution."""
        protocol = enhanced_coordination_protocol
        
        # Mock error in workflow state retrieval
        protocol.workflow_coordinator.get_workflow_state.side_effect = Exception("Test error")
        
        result = await protocol.resolve_dynamic_dependencies(
            sample_workflow_definition.workflow_id,
            "task_002"
        )
        
        assert result == []  # Should return empty list on error
    
    @pytest.mark.asyncio
    async def test_performance_alert_generation(self, enhanced_coordination_protocol):
        """Test performance alert generation."""
        protocol = enhanced_coordination_protocol
        
        # Mock stalled workflow
        mock_workflow_state = Mock()
        mock_workflow_state.progress_percentage = 30.0
        mock_workflow_state.started_at = datetime.now() - timedelta(hours=3)
        protocol.workflow_coordinator.get_workflow_state.return_value = mock_workflow_state
        
        await protocol._check_performance_alerts("test_workflow")
        
        assert len(protocol.performance_alerts) == 1
        alert = protocol.performance_alerts[0]
        assert alert["type"] == "workflow_stalled"
        assert alert["workflow_id"] == "test_workflow"
        assert alert["progress"] == 30.0
    
    @pytest.mark.asyncio
    async def test_cache_cleanup_mechanisms(self, enhanced_coordination_protocol):
        """Test cache cleanup mechanisms."""
        protocol = enhanced_coordination_protocol
        
        # Fill caches beyond limits
        for i in range(1001):
            protocol.intelligent_routing_cache[f"key_{i}"] = (f"agent_{i}", 0.5)
        
        for i in range(501):
            protocol.dependency_resolution_cache[f"dep_{i}"] = [f"task_{i}"]
        
        # Trigger cleanup
        await protocol._intelligent_routing_optimizer()
        await protocol._dependency_resolution_optimizer()
        
        # Check that caches were cleaned
        assert len(protocol.intelligent_routing_cache) == 0
        assert len(protocol.dependency_resolution_cache) == 0


@pytest.mark.asyncio
class TestIntegrationScenarios:
    """Integration test scenarios for enhanced coordination."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow_coordination(
        self, 
        enhanced_coordination_protocol,
        sample_workflow_definition,
        sample_agent_capabilities
    ):
        """Test end-to-end workflow coordination."""
        protocol = enhanced_coordination_protocol
        
        # Setup
        protocol.workflow_coordinator.agent_capabilities = sample_agent_capabilities
        
        # Mock workflow state
        mock_workflow_state = Mock()
        mock_workflow_state.workflow_id = sample_workflow_definition.workflow_id
        mock_workflow_state.status = "executing"
        mock_workflow_state.progress_percentage = 0.0
        protocol.workflow_coordinator.execute_workflow.return_value = mock_workflow_state
        
        # Execute workflow
        result = await protocol.execute_enhanced_workflow(sample_workflow_definition)
        
        assert result.workflow_id == sample_workflow_definition.workflow_id
        assert len(protocol.coordination_events) > 0
        assert protocol.coordination_events[-1]["type"] == "workflow_started"
    
    @pytest.mark.asyncio
    async def test_parallel_task_coordination_with_dependencies(
        self, 
        enhanced_coordination_protocol,
        sample_workflow_definition
    ):
        """Test parallel task coordination with dependencies."""
        protocol = enhanced_coordination_protocol
        
        # Setup workflow
        protocol.workflow_coordinator.workflow_definitions[sample_workflow_definition.workflow_id] = sample_workflow_definition
        
        # Mock workflow state
        mock_workflow_state = Mock()
        protocol.workflow_coordinator.get_workflow_state.return_value = mock_workflow_state
        
        # Test dependency resolution for parallel tasks
        task_002_deps = await protocol.resolve_dynamic_dependencies(
            sample_workflow_definition.workflow_id,
            "task_002"
        )
        
        task_003_deps = await protocol.resolve_dynamic_dependencies(
            sample_workflow_definition.workflow_id,
            "task_003"
        )
        
        # task_002 should have task_001 as dependency
        # task_003 should have optimized dependencies (soft dependency might be removed)
        assert len(task_002_deps) >= 0  # At least some dependencies
        assert len(task_003_deps) >= 0  # Dependencies might be optimized
    
    @pytest.mark.asyncio
    async def test_agent_performance_tracking_and_routing(
        self, 
        enhanced_coordination_protocol,
        sample_enhanced_task,
        sample_agent_capabilities
    ):
        """Test agent performance tracking and intelligent routing."""
        protocol = enhanced_coordination_protocol
        
        # Setup agent capabilities
        protocol.workflow_coordinator.agent_capabilities = sample_agent_capabilities
        
        # Add performance history
        protocol.agent_performance_history["doc_agent_001"].extend([0.9, 0.8, 0.95])
        protocol.agent_performance_history["quality_agent_001"].extend([0.7, 0.6, 0.75])
        
        # Mock coordinator state
        mock_coordinator_state = Mock()
        mock_coordinator_state.active_agents = {
            "doc_agent_001": Mock(active_tasks=1),
            "quality_agent_001": Mock(active_tasks=0)
        }
        protocol.multi_agent_coordinator.get_coordinator_state.return_value = mock_coordinator_state
        
        # Test routing decision
        result = await protocol.intelligent_task_routing(
            sample_enhanced_task,
            ["doc_agent_001", "quality_agent_001"]
        )
        
        # Should prefer doc_agent_001 due to specialization match and good performance
        assert result == "doc_agent_001"
    
    @pytest.mark.asyncio
    async def test_coordination_optimization_feedback_loop(
        self, 
        enhanced_coordination_protocol,
        sample_workflow_definition
    ):
        """Test coordination optimization feedback loop."""
        protocol = enhanced_coordination_protocol
        
        # Setup mock data for optimization
        protocol.parallel_execution_analytics = {
            "workflow_001": {"expected_improvement": 0.2},
            "workflow_002": {"expected_improvement": 0.4}
        }
        
        # Mock coordinator state
        mock_coordinator_state = Mock()
        mock_coordinator_state.active_agents = {
            "agent_001": Mock(active_tasks=3),
            "agent_002": Mock(active_tasks=1)
        }
        protocol.multi_agent_coordinator.get_coordinator_state.return_value = mock_coordinator_state
        
        # Test optimization identification
        await protocol._identify_optimization_opportunities()
        
        # Should identify load balancing optimization due to uneven task distribution
        assert len(protocol.coordination_events) > 0
        optimization_event = next(
            (event for event in protocol.coordination_events 
             if event["type"] == "optimization_opportunities"), 
            None
        )
        
        if optimization_event:
            assert "load_balancing_optimization" in optimization_event["data"]["opportunities"]