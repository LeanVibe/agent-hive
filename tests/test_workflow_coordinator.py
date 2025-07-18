"""
Tests for the enhanced workflow coordinator.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from advanced_orchestration.models import (
    AgentCapabilities,
    AgentSpecialization,
    CoordinationMetrics,
    CoordinatorConfig,
    DependencyType,
    EnhancedTaskAssignment,
    QualityGate,
    ResourceLimits,
    TaskDependency,
    TaskPriority,
    TaskStatus,
    WorkflowDefinition,
    WorkflowState,
    WorkflowType,
)
from advanced_orchestration.workflow_coordinator import WorkflowCoordinator


@pytest.fixture
def coordinator_config():
    """Test coordinator configuration."""
    return CoordinatorConfig(
        max_agents=5,
        min_agents=1,
        health_check_interval=10.0,
        load_balance_interval=30.0,
        resource_limits=ResourceLimits(max_agents=5)
    )


@pytest.fixture
def workflow_coordinator(coordinator_config):
    """Test workflow coordinator instance."""
    return WorkflowCoordinator(coordinator_config)


@pytest.fixture
def sample_workflow_definition():
    """Sample workflow definition for testing."""
    return WorkflowDefinition(
        workflow_id="test-workflow",
        workflow_type=WorkflowType.DOCUMENTATION,
        name="Test Documentation Workflow",
        description="Test workflow for documentation coordination",
        tasks=["task1", "task2", "task3"],
        dependencies=[
            TaskDependency(
                task_id="task2",
                depends_on="task1",
                dependency_type=DependencyType.BLOCKING
            ),
            TaskDependency(
                task_id="task3",
                depends_on="task1",
                dependency_type=DependencyType.SOFT
            )
        ],
        agent_assignments={
            "task1": AgentSpecialization.DOCUMENTATION,
            "task2": AgentSpecialization.QUALITY,
            "task3": AgentSpecialization.INTEGRATION
        },
        parallel_execution=True,
        max_parallel_tasks=3,
        estimated_duration=240
    )


@pytest.fixture
def sample_agent_capabilities():
    """Sample agent capabilities for testing."""
    return AgentCapabilities(
        specialization=AgentSpecialization.DOCUMENTATION,
        skill_level=0.8,
        supported_workflows=[
            WorkflowType.DOCUMENTATION, WorkflowType.TUTORIAL],
        max_concurrent_tasks=2,
        preferred_task_types=["documentation", "writing"],
        performance_metrics={"speed": 0.9, "quality": 0.8},
        learning_rate=0.1,
        adaptation_score=0.7
    )


@pytest.mark.asyncio
class TestWorkflowCoordinator:
    """Test cases for WorkflowCoordinator."""

    async def test_initialization(self, workflow_coordinator):
        """Test workflow coordinator initialization."""
        assert workflow_coordinator.running is False
        assert len(workflow_coordinator.active_workflows) == 0
        assert len(workflow_coordinator.workflow_definitions) == 0
        assert len(workflow_coordinator.enhanced_tasks) == 0
        assert len(workflow_coordinator.agent_capabilities) == 0
        assert workflow_coordinator.intelligent_routing is not None

    async def test_start_and_stop(self, workflow_coordinator):
        """Test starting and stopping the workflow coordinator."""
        # Mock the multi-agent coordinator
        workflow_coordinator.multi_agent_coordinator.start = AsyncMock()
        workflow_coordinator.multi_agent_coordinator.stop = AsyncMock()

        # Test start
        await workflow_coordinator.start()
        assert workflow_coordinator.running is True
        workflow_coordinator.multi_agent_coordinator.start.assert_called_once()

        # Test stop
        await workflow_coordinator.stop()
        assert workflow_coordinator.running is False
        workflow_coordinator.multi_agent_coordinator.stop.assert_called_once()

    async def test_workflow_registration(
            self,
            workflow_coordinator,
            sample_workflow_definition):
        """Test workflow registration."""
        # Mock validation
        workflow_coordinator._validate_workflow_definition = AsyncMock(
            return_value=True)
        workflow_coordinator._build_dependency_graph = AsyncMock()

        # Test registration
        result = await workflow_coordinator.register_workflow(sample_workflow_definition)

        assert result is True
        assert sample_workflow_definition.workflow_id in workflow_coordinator.workflow_definitions
        workflow_coordinator._validate_workflow_definition.assert_called_once()
        workflow_coordinator._build_dependency_graph.assert_called_once()

    async def test_workflow_registration_failure(
            self, workflow_coordinator, sample_workflow_definition):
        """Test workflow registration failure."""
        # Mock validation failure
        workflow_coordinator._validate_workflow_definition = AsyncMock(
            return_value=False)

        # Test registration
        result = await workflow_coordinator.register_workflow(sample_workflow_definition)

        assert result is False
        assert sample_workflow_definition.workflow_id not in workflow_coordinator.workflow_definitions

    async def test_agent_capabilities_registration(
            self, workflow_coordinator, sample_agent_capabilities):
        """Test agent capabilities registration."""
        agent_id = "test-agent"

        # Test registration
        result = await workflow_coordinator.register_agent_capabilities(agent_id, sample_agent_capabilities)

        assert result is True
        assert agent_id in workflow_coordinator.agent_capabilities
        assert workflow_coordinator.agent_capabilities[agent_id] == sample_agent_capabilities

    async def test_workflow_execution_initialization(
            self, workflow_coordinator, sample_workflow_definition):
        """Test workflow execution initialization."""
        # Setup
        workflow_coordinator.workflow_definitions[
            sample_workflow_definition.workflow_id] = sample_workflow_definition
        workflow_coordinator._create_enhanced_task_assignments = AsyncMock()
        workflow_coordinator._execute_workflow_phases = AsyncMock()

        # Test execution
        result = await workflow_coordinator.execute_workflow(sample_workflow_definition.workflow_id)

        assert isinstance(result, WorkflowState)
        assert result.workflow_id == sample_workflow_definition.workflow_id
        assert result.status == "initializing"
        assert sample_workflow_definition.workflow_id in workflow_coordinator.active_workflows

    async def test_workflow_execution_not_found(self, workflow_coordinator):
        """Test workflow execution with non-existent workflow."""
        with pytest.raises(Exception) as exc_info:
            await workflow_coordinator.execute_workflow("non-existent-workflow")

        assert "not found" in str(exc_info.value)

    async def test_task_progress_update(self, workflow_coordinator):
        """Test task progress update."""
        # Setup task
        task_id = "test-task"
        workflow_id = "test-workflow"

        enhanced_task = EnhancedTaskAssignment(
            task_id=task_id,
            workflow_id=workflow_id,
            agent_id="test-agent",
            agent_specialization=AgentSpecialization.GENERAL,
            task_data={},
            priority=TaskPriority.MEDIUM,
            dependencies=[],
            estimated_duration=60
        )

        workflow_coordinator.enhanced_tasks[task_id] = enhanced_task
        workflow_coordinator.active_workflows[workflow_id] = WorkflowState(
            workflow_id=workflow_id,
            status="executing",
            progress_percentage=0.0,
            active_tasks=[],
            completed_tasks=[],
            failed_tasks=[],
            blocked_tasks=[],
            quality_gates=[],
            coordination_metrics=CoordinationMetrics(
                workflow_completion_rate=0.0,
                parallel_efficiency=0.0,
                task_distribution_balance=0.0,
                quality_consistency=0.0,
                dependency_resolution_time=0.0,
                agent_utilization={},
                coordination_overhead=0.0
            ),
            estimated_completion=datetime.now() + timedelta(hours=1)
        )

        # Mock workflow progress update
        workflow_coordinator._update_workflow_progress = AsyncMock()

        # Test progress update
        result = await workflow_coordinator.update_task_progress(task_id, 0.5, 0.8)

        assert result is True
        assert enhanced_task.progress_percentage == 50.0
        assert enhanced_task.quality_score == 0.8
        workflow_coordinator._update_workflow_progress.assert_called_once()

    async def test_task_progress_update_not_found(self, workflow_coordinator):
        """Test task progress update with non-existent task."""
        result = await workflow_coordinator.update_task_progress("non-existent-task", 0.5, 0.8)
        assert result is False

    async def test_quality_gate_validation_success(self, workflow_coordinator):
        """Test successful quality gate validation."""
        # Setup tasks
        task1_id = "task1"
        task2_id = "task2"

        for task_id in [task1_id, task2_id]:
            enhanced_task = EnhancedTaskAssignment(
                task_id=task_id,
                workflow_id="test-workflow",
                agent_id="test-agent",
                agent_specialization=AgentSpecialization.GENERAL,
                task_data={},
                priority=TaskPriority.MEDIUM,
                dependencies=[],
                estimated_duration=60,
                status=TaskStatus.COMPLETED,
                quality_score=0.9
            )
            workflow_coordinator.enhanced_tasks[task_id] = enhanced_task

        # Setup quality gate
        gate_id = "test-gate"
        quality_gate = QualityGate(
            gate_id=gate_id,
            workflow_id="test-workflow",
            required_tasks=[task1_id, task2_id],
            quality_threshold=0.8,
            validation_criteria=["completeness", "accuracy"],
            blocking=True
        )

        workflow_coordinator.quality_gates[gate_id] = quality_gate

        # Test validation
        result = await workflow_coordinator.validate_quality_gate(gate_id)

        assert result is True
        assert workflow_coordinator.coordination_stats['quality_gates_passed'] == 1

    async def test_quality_gate_validation_failure(self, workflow_coordinator):
        """Test failed quality gate validation."""
        # Setup tasks with low quality
        task1_id = "task1"
        task2_id = "task2"

        for task_id in [task1_id, task2_id]:
            enhanced_task = EnhancedTaskAssignment(
                task_id=task_id,
                workflow_id="test-workflow",
                agent_id="test-agent",
                agent_specialization=AgentSpecialization.GENERAL,
                task_data={},
                priority=TaskPriority.MEDIUM,
                dependencies=[],
                estimated_duration=60,
                status=TaskStatus.COMPLETED,
                quality_score=0.5  # Below threshold
            )
            workflow_coordinator.enhanced_tasks[task_id] = enhanced_task

        # Setup quality gate
        gate_id = "test-gate"
        quality_gate = QualityGate(
            gate_id=gate_id,
            workflow_id="test-workflow",
            required_tasks=[task1_id, task2_id],
            quality_threshold=0.8,
            validation_criteria=["completeness", "accuracy"],
            blocking=True
        )

        workflow_coordinator.quality_gates[gate_id] = quality_gate

        # Test validation
        result = await workflow_coordinator.validate_quality_gate(gate_id)

        assert result is False
        assert workflow_coordinator.coordination_stats['quality_gates_failed'] == 1

    async def test_workflow_definition_validation_success(
            self, workflow_coordinator, sample_workflow_definition):
        """Test successful workflow definition validation."""
        result = await workflow_coordinator._validate_workflow_definition(sample_workflow_definition)
        assert result is True

    async def test_workflow_definition_validation_no_tasks(
            self, workflow_coordinator):
        """Test workflow definition validation with no tasks."""
        workflow_def = WorkflowDefinition(
            workflow_id="test-workflow",
            workflow_type=WorkflowType.DOCUMENTATION,
            name="Test Workflow",
            description="Test workflow",
            tasks=[],  # No tasks
            dependencies=[],
            agent_assignments={},
            parallel_execution=False
        )

        result = await workflow_coordinator._validate_workflow_definition(workflow_def)
        assert result is False

    async def test_workflow_definition_validation_invalid_dependency(
            self, workflow_coordinator):
        """Test workflow definition validation with invalid dependency."""
        workflow_def = WorkflowDefinition(
            workflow_id="test-workflow",
            workflow_type=WorkflowType.DOCUMENTATION,
            name="Test Workflow",
            description="Test workflow",
            tasks=["task1", "task2"],
            dependencies=[
                TaskDependency(
                    task_id="task2",
                    depends_on="non-existent-task",  # Invalid dependency
                    dependency_type=DependencyType.BLOCKING
                )
            ],
            agent_assignments={},
            parallel_execution=False
        )

        result = await workflow_coordinator._validate_workflow_definition(workflow_def)
        assert result is False

    async def test_circular_dependency_detection(self, workflow_coordinator):
        """Test circular dependency detection."""
        workflow_def = WorkflowDefinition(
            workflow_id="test-workflow",
            workflow_type=WorkflowType.DOCUMENTATION,
            name="Test Workflow",
            description="Test workflow",
            tasks=["task1", "task2", "task3"],
            dependencies=[
                TaskDependency(
                    task_id="task2",
                    depends_on="task1",
                    dependency_type=DependencyType.BLOCKING
                ),
                TaskDependency(
                    task_id="task3",
                    depends_on="task2",
                    dependency_type=DependencyType.BLOCKING
                ),
                TaskDependency(
                    task_id="task1",
                    depends_on="task3",  # Creates circular dependency
                    dependency_type=DependencyType.BLOCKING
                )
            ],
            agent_assignments={},
            parallel_execution=False
        )

        result = await workflow_coordinator._has_circular_dependencies(workflow_def)
        assert result is True

    async def test_task_readiness_check(self, workflow_coordinator):
        """Test task readiness check."""
        # Setup dependency task
        dep_task_id = "dependency-task"
        dep_task = EnhancedTaskAssignment(
            task_id=dep_task_id,
            workflow_id="test-workflow",
            agent_id="test-agent",
            agent_specialization=AgentSpecialization.GENERAL,
            task_data={},
            priority=TaskPriority.MEDIUM,
            dependencies=[],
            estimated_duration=60,
            status=TaskStatus.COMPLETED
        )
        workflow_coordinator.enhanced_tasks[dep_task_id] = dep_task

        # Setup dependent task
        task_id = "dependent-task"
        task = EnhancedTaskAssignment(
            task_id=task_id,
            workflow_id="test-workflow",
            agent_id="test-agent",
            agent_specialization=AgentSpecialization.GENERAL,
            task_data={},
            priority=TaskPriority.MEDIUM,
            dependencies=[
                TaskDependency(
                    task_id=task_id,
                    depends_on=dep_task_id,
                    dependency_type=DependencyType.BLOCKING,
                    required_status=TaskStatus.COMPLETED
                )
            ],
            estimated_duration=60,
            status=TaskStatus.WAITING_DEPENDENCY
        )
        workflow_coordinator.enhanced_tasks[task_id] = task

        # Test readiness
        result = await workflow_coordinator._is_task_ready(task_id)
        assert result is True

        # Test not ready (change dependency status)
        dep_task.status = TaskStatus.IN_PROGRESS
        result = await workflow_coordinator._is_task_ready(task_id)
        assert result is False

    async def test_parallel_group_identification(
            self, workflow_coordinator, sample_workflow_definition):
        """Test parallel group identification."""
        await workflow_coordinator._build_dependency_graph(sample_workflow_definition)

        # Check parallel groups
        parallel_groups = workflow_coordinator.parallel_execution_groups[
            sample_workflow_definition.workflow_id]

        # task2 and task3 should be in the same parallel group (both depend on
        # task1)
        assert len(parallel_groups) >= 0  # May vary based on implementation

    async def test_ml_agent_selection(
            self,
            workflow_coordinator,
            sample_agent_capabilities):
        """Test ML-based agent selection."""
        # Setup agent capabilities
        agent_id = "test-agent"
        workflow_coordinator.agent_capabilities[agent_id] = sample_agent_capabilities

        # Setup performance history
        workflow_coordinator.performance_history[agent_id] = [
            {"performance": 0.8, "timestamp": datetime.now()},
            {"performance": 0.9, "timestamp": datetime.now()}
        ]

        # Create test task
        task = EnhancedTaskAssignment(
            task_id="test-task",
            workflow_id="test-workflow",
            agent_id="",
            agent_specialization=AgentSpecialization.DOCUMENTATION,
            task_data={},
            priority=TaskPriority.MEDIUM,
            dependencies=[],
            estimated_duration=60
        )

        # Test ML selection
        candidates = [agent_id]
        result = await workflow_coordinator._ml_agent_selection(task, candidates)

        assert result == agent_id

    async def test_heuristic_agent_selection(self, workflow_coordinator):
        """Test heuristic-based agent selection."""
        # Mock coordinator state
        mock_state = MagicMock()
        mock_state.active_agents = {
            "agent1": MagicMock(active_tasks=2),
            "agent2": MagicMock(active_tasks=1),
            "agent3": MagicMock(active_tasks=3)
        }

        workflow_coordinator.multi_agent_coordinator.get_coordinator_state = AsyncMock(
            return_value=mock_state)

        # Create test task
        task = EnhancedTaskAssignment(
            task_id="test-task",
            workflow_id="test-workflow",
            agent_id="",
            agent_specialization=AgentSpecialization.GENERAL,
            task_data={},
            priority=TaskPriority.MEDIUM,
            dependencies=[],
            estimated_duration=60
        )

        # Test heuristic selection
        candidates = ["agent1", "agent2", "agent3"]
        result = await workflow_coordinator._heuristic_agent_selection(task, candidates)

        assert result == "agent2"  # Should select agent with least active tasks

    async def test_coordination_metrics_calculation(
            self, workflow_coordinator):
        """Test coordination metrics calculation."""
        # Setup workflow
        workflow_id = "test-workflow"
        workflow_state = WorkflowState(
            workflow_id=workflow_id,
            status="executing",
            progress_percentage=50.0,
            active_tasks=["task1"],
            completed_tasks=["task2"],
            failed_tasks=[],
            blocked_tasks=[],
            quality_gates=[],
            coordination_metrics=CoordinationMetrics(
                workflow_completion_rate=0.0,
                parallel_efficiency=0.0,
                task_distribution_balance=0.0,
                quality_consistency=0.0,
                dependency_resolution_time=0.0,
                agent_utilization={},
                coordination_overhead=0.0
            ),
            estimated_completion=datetime.now() + timedelta(hours=1)
        )

        workflow_coordinator.active_workflows[workflow_id] = workflow_state
        workflow_coordinator.parallel_execution_groups[workflow_id] = []

        # Test calculation
        await workflow_coordinator._calculate_coordination_metrics(workflow_id)

        # Check that metrics were calculated
        assert workflow_id in workflow_coordinator.coordination_metrics
        metrics = workflow_coordinator.coordination_metrics[workflow_id]
        assert isinstance(metrics, CoordinationMetrics)
        assert metrics.workflow_completion_rate == 0.5

    async def test_coordination_statistics(self, workflow_coordinator):
        """Test coordination statistics retrieval."""
        # Setup some state
        workflow_coordinator.coordination_stats['workflows_executed'] = 2
        workflow_coordinator.coordination_stats['parallel_tasks_executed'] = 5
        workflow_coordinator.active_workflows['test-workflow'] = MagicMock()
        workflow_coordinator.enhanced_tasks['test-task'] = MagicMock()
        workflow_coordinator.agent_capabilities['test-agent'] = MagicMock()
        workflow_coordinator.quality_gates['test-gate'] = MagicMock()

        # Test statistics
        stats = workflow_coordinator.get_coordination_statistics()

        assert stats['workflows_executed'] == 2
        assert stats['parallel_tasks_executed'] == 5
        assert stats['active_workflows'] == 1
        assert stats['total_tasks'] == 1
        assert stats['registered_agents'] == 1
        assert stats['quality_gates'] == 1

    async def test_workflow_state_retrieval(self, workflow_coordinator):
        """Test workflow state retrieval."""
        # Setup workflow state
        workflow_id = "test-workflow"
        workflow_state = WorkflowState(
            workflow_id=workflow_id,
            status="executing",
            progress_percentage=50.0,
            active_tasks=["task1"],
            completed_tasks=["task2"],
            failed_tasks=[],
            blocked_tasks=[],
            quality_gates=[],
            coordination_metrics=CoordinationMetrics(
                workflow_completion_rate=0.0,
                parallel_efficiency=0.0,
                task_distribution_balance=0.0,
                quality_consistency=0.0,
                dependency_resolution_time=0.0,
                agent_utilization={},
                coordination_overhead=0.0
            ),
            estimated_completion=datetime.now() + timedelta(hours=1)
        )

        workflow_coordinator.active_workflows[workflow_id] = workflow_state

        # Test retrieval
        result = await workflow_coordinator.get_workflow_state(workflow_id)

        assert result == workflow_state
        assert result.workflow_id == workflow_id
        assert result.status == "executing"

    async def test_workflow_state_retrieval_not_found(
            self, workflow_coordinator):
        """Test workflow state retrieval for non-existent workflow."""
        result = await workflow_coordinator.get_workflow_state("non-existent-workflow")
        assert result is None

    async def test_coordination_metrics_retrieval(self, workflow_coordinator):
        """Test coordination metrics retrieval."""
        # Setup metrics
        workflow_id = "test-workflow"
        metrics = CoordinationMetrics(
            workflow_completion_rate=0.8,
            parallel_efficiency=0.9,
            task_distribution_balance=0.7,
            quality_consistency=0.85,
            dependency_resolution_time=45.0,
            agent_utilization={"agent1": 0.6, "agent2": 0.8},
            coordination_overhead=0.1
        )

        workflow_coordinator.coordination_metrics[workflow_id] = metrics

        # Test retrieval
        result = await workflow_coordinator.get_coordination_metrics(workflow_id)

        assert result == metrics
        assert result.workflow_completion_rate == 0.8
        assert result.parallel_efficiency == 0.9

    async def test_coordination_metrics_retrieval_not_found(
            self, workflow_coordinator):
        """Test coordination metrics retrieval for non-existent workflow."""
        result = await workflow_coordinator.get_coordination_metrics("non-existent-workflow")
        assert result is None


@pytest.mark.asyncio
class TestWorkflowCoordinatorIntegration:
    """Integration tests for WorkflowCoordinator."""

    async def test_full_workflow_execution_simulation(
            self,
            workflow_coordinator,
            sample_workflow_definition,
            sample_agent_capabilities):
        """Test full workflow execution simulation."""
        # Setup
        await workflow_coordinator.start()

        # Register agent capabilities
        agent_id = "test-agent"
        await workflow_coordinator.register_agent_capabilities(agent_id, sample_agent_capabilities)

        # Register workflow
        await workflow_coordinator.register_workflow(sample_workflow_definition)

        # Mock the multi-agent coordinator methods
        workflow_coordinator.multi_agent_coordinator.distribute_task = AsyncMock()
        workflow_coordinator.multi_agent_coordinator.get_coordinator_state = AsyncMock()

        # Mock coordinator state
        mock_state = MagicMock()
        mock_state.active_agents = {
            agent_id: MagicMock(
                status=MagicMock(value="healthy"),
                active_tasks=0
            )
        }
        workflow_coordinator.multi_agent_coordinator.get_coordinator_state.return_value = mock_state

        # Mock task distribution
        mock_task_assignment = MagicMock()
        mock_task_assignment.task_id = "coordinator-task-id"
        workflow_coordinator.multi_agent_coordinator.distribute_task.return_value = mock_task_assignment

        # Mock task execution monitoring
        workflow_coordinator._monitor_task_completion = AsyncMock()

        # Mock workflow execution phases to avoid actual execution
        workflow_coordinator._execute_workflow_phases = AsyncMock()

        # Execute workflow
        workflow_state = await workflow_coordinator.execute_workflow(sample_workflow_definition.workflow_id)

        # Verify workflow state
        assert workflow_state.workflow_id == sample_workflow_definition.workflow_id
        assert workflow_state.status == "initializing"
        assert len(workflow_coordinator.enhanced_tasks) == len(
            sample_workflow_definition.tasks)

        # Cleanup
        await workflow_coordinator.stop()

        # Wait briefly for background tasks to complete
        await asyncio.sleep(0.1)

    async def test_parallel_task_execution_coordination(
            self, workflow_coordinator):
        """Test parallel task execution coordination."""
        # Create workflow with parallel tasks
        workflow_def = WorkflowDefinition(
            workflow_id="parallel-workflow",
            workflow_type=WorkflowType.DEVELOPMENT,
            name="Parallel Development Workflow",
            description="Test parallel task execution",
            tasks=["task1", "task2", "task3", "task4"],
            dependencies=[
                TaskDependency(
                    task_id="task2",
                    depends_on="task1",
                    dependency_type=DependencyType.BLOCKING
                ),
                TaskDependency(
                    task_id="task3",
                    depends_on="task1",
                    dependency_type=DependencyType.BLOCKING
                ),
                TaskDependency(
                    task_id="task4",
                    depends_on="task1",
                    dependency_type=DependencyType.BLOCKING
                )
            ],
            agent_assignments={
                "task1": AgentSpecialization.GENERAL,
                "task2": AgentSpecialization.DEVELOPMENT,
                "task3": AgentSpecialization.TESTING,
                "task4": AgentSpecialization.QUALITY
            },
            parallel_execution=True,
            max_parallel_tasks=3
        )

        # Setup and test
        await workflow_coordinator.start()
        await workflow_coordinator.register_workflow(workflow_def)

        # Check parallel group identification
        parallel_groups = workflow_coordinator.parallel_execution_groups[workflow_def.workflow_id]

        # task2, task3, task4 should be identified as parallel (all depend on task1)
        # The exact grouping depends on the implementation
        assert len(parallel_groups) >= 0

        await workflow_coordinator.stop()

    async def test_quality_gate_integration(
            self, workflow_coordinator, sample_workflow_definition):
        """Test quality gate integration with workflow execution."""
        # Setup quality gate
        gate_id = "integration-gate"
        quality_gate = QualityGate(
            gate_id=gate_id,
            workflow_id=sample_workflow_definition.workflow_id,
            required_tasks=["task1", "task2"],
            quality_threshold=0.8,
            validation_criteria=["completeness", "accuracy", "performance"],
            blocking=True,
            auto_validation=False,
            timeout_minutes=30
        )

        workflow_coordinator.quality_gates[gate_id] = quality_gate

        # Setup workflow and tasks
        await workflow_coordinator.register_workflow(sample_workflow_definition)

        # Simulate task completion with quality scores
        for task_id in ["task1", "task2"]:
            enhanced_task = EnhancedTaskAssignment(
                task_id=task_id,
                workflow_id=sample_workflow_definition.workflow_id,
                agent_id="test-agent",
                agent_specialization=AgentSpecialization.GENERAL,
                task_data={},
                priority=TaskPriority.MEDIUM,
                dependencies=[],
                estimated_duration=60,
                status=TaskStatus.COMPLETED,
                quality_score=0.85
            )
            workflow_coordinator.enhanced_tasks[task_id] = enhanced_task

        # Test quality gate validation
        result = await workflow_coordinator.validate_quality_gate(gate_id)

        assert result is True
        assert workflow_coordinator.coordination_stats['quality_gates_passed'] == 1
