"""
Comprehensive tests for the Intelligence Framework

This module contains unit tests and integration tests for all components
of the intelligence framework system.
"""

import pytest
import asyncio
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import json

# Import the modules to test
from intelligence_framework import (
    IntelligenceFramework, IntelligenceConfig, IntelligenceDecision,
    AgentIntelligence, IntelligenceLevel, DecisionType
)
from agent_coordination_protocols import (
    AgentCoordinationProtocols, AgentMessage, MessageType, Priority,
    CoordinationSession, CoordinationStrategy, AgentCapability
)
from intelligent_task_allocation import (
    IntelligentTaskAllocator, IntelligentTask, TaskPriority, TaskComplexity,
    AllocationStrategy, AgentPerformanceProfile
)
from performance_monitoring_optimization import (
    PerformanceMonitoringOptimization, PerformanceMetric, PerformanceMetricType,
    PerformanceThreshold, AlertLevel, OptimizationAction
)
from advanced_orchestration.models import (
    ResourceRequirements, AgentInfo, AgentStatus, AgentRegistration,
    AgentMetadata, CoordinatorConfig
)
from ml_enhancements.models import MLConfig


class TestIntelligenceFramework:
    """Test suite for the Intelligence Framework."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)
        yield db_path
        os.unlink(db_path)

    @pytest.fixture
    def intelligence_config(self, temp_db):
        """Create test configuration."""
        return IntelligenceConfig(
            intelligence_level=IntelligenceLevel.ADVANCED,
            decision_confidence_threshold=0.8,
            db_path=temp_db
        )

    @pytest.fixture
    def intelligence_framework(self, intelligence_config):
        """Create intelligence framework instance."""
        return IntelligenceFramework(intelligence_config)

    @pytest.mark.asyncio
    async def test_framework_initialization(self, intelligence_framework):
        """Test framework initialization."""
        assert intelligence_framework.config.intelligence_level == IntelligenceLevel.ADVANCED
        assert intelligence_framework.config.decision_confidence_threshold == 0.8
        assert intelligence_framework.adaptive_learning is not None
        assert intelligence_framework.predictive_analytics is not None
        assert intelligence_framework.pattern_optimizer is not None
        assert intelligence_framework.coordinator is not None

    @pytest.mark.asyncio
    async def test_start_stop_framework(self, intelligence_framework):
        """Test starting and stopping the framework."""
        # Start framework
        await intelligence_framework.start()
        assert intelligence_framework.running is True
        assert len(intelligence_framework.background_tasks) > 0

        # Stop framework
        await intelligence_framework.stop()
        assert intelligence_framework.running is False
        assert len(intelligence_framework.background_tasks) == 0

    @pytest.mark.asyncio
    async def test_make_decision(self, intelligence_framework):
        """Test decision making functionality."""
        context = {
            'agent_count': 5,
            'task_complexity': 0.7,
            'resource_usage': 0.6,
            'queue_size': 3
        }

        decision = await intelligence_framework.make_decision(
            DecisionType.TASK_ALLOCATION,
            context
        )

        assert isinstance(decision, IntelligenceDecision)
        assert decision.decision_type == DecisionType.TASK_ALLOCATION
        assert 0.0 <= decision.confidence <= 1.0
        assert decision.recommendation is not None
        assert decision.reasoning is not None

    @pytest.mark.asyncio
    async def test_assess_agent_intelligence(self, intelligence_framework):
        """Test agent intelligence assessment."""
        # Mock agent info
        agent_info = Mock()
        agent_info.agent_id = "test_agent_1"
        agent_info.active_tasks = 2
        agent_info.error_count = 0
        agent_info.registration = Mock()
        agent_info.registration.capabilities = ["processing", "analysis"]

        # Mock coordinator
        intelligence_framework.coordinator.get_agent_status = AsyncMock(return_value=agent_info)

        intelligence = await intelligence_framework.assess_agent_intelligence("test_agent_1")

        assert isinstance(intelligence, AgentIntelligence)
        assert intelligence.agent_id == "test_agent_1"
        assert intelligence.intelligence_level in IntelligenceLevel
        assert 0.0 <= intelligence.performance_score <= 1.0
        assert 0.0 <= intelligence.learning_progress <= 1.0
        assert 0.0 <= intelligence.decision_accuracy <= 1.0

    @pytest.mark.asyncio
    async def test_optimize_system_performance(self, intelligence_framework):
        """Test system performance optimization."""
        # Mock coordinator state
        mock_state = Mock()
        mock_state.active_agents = {"agent1": Mock(), "agent2": Mock()}
        mock_state.pending_tasks = []
        mock_state.assigned_tasks = {}
        mock_state.load_balancing_metrics = Mock()
        mock_state.load_balancing_metrics.distribution_variance = 0.2

        intelligence_framework.coordinator.get_coordinator_state = AsyncMock(return_value=mock_state)

        # Mock predictive analytics
        mock_prediction = Mock()
        mock_prediction.predicted_value = 0.85
        mock_prediction.accuracy_score = 0.9
        intelligence_framework.predictive_analytics.predict_performance = AsyncMock(return_value=mock_prediction)

        # Mock pattern optimizer
        intelligence_framework.pattern_optimizer.analyze_patterns = AsyncMock(return_value=[])

        optimization_results = await intelligence_framework.optimize_system_performance()

        assert 'timestamp' in optimization_results
        assert 'current_performance' in optimization_results
        assert 'recommendations' in optimization_results
        assert 'system_health' in optimization_results
        assert isinstance(optimization_results['recommendations'], list)

    @pytest.mark.asyncio
    async def test_database_operations(self, intelligence_framework):
        """Test database operations."""
        # Create a test decision
        decision = IntelligenceDecision(
            decision_id="test_decision_1",
            decision_type=DecisionType.TASK_ALLOCATION,
            confidence=0.85,
            recommendation={"action": "allocate", "agent_id": "test_agent"},
            reasoning="Test reasoning"
        )

        # Store decision
        await intelligence_framework._store_decision(decision)

        # Verify storage
        with sqlite3.connect(intelligence_framework.config.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM intelligence_decisions WHERE decision_id = ?",
                (decision.decision_id,)
            )
            result = cursor.fetchone()
            assert result is not None
            assert result[1] == decision.decision_type.value
            assert result[2] == decision.confidence


class TestAgentCoordinationProtocols:
    """Test suite for Agent Coordination Protocols."""

    @pytest.fixture
    def coordination_protocols(self):
        """Create coordination protocols instance."""
        return AgentCoordinationProtocols("test_agent_1")

    @pytest.mark.asyncio
    async def test_send_message(self, coordination_protocols):
        """Test message sending functionality."""
        content = {"task_id": "test_task_1", "priority": "high"}

        # Mock message delivery
        coordination_protocols._deliver_message = AsyncMock()

        message = await coordination_protocols.send_message(
            recipient_id="test_agent_2",
            message_type=MessageType.TASK_REQUEST,
            content=content,
            priority=Priority.HIGH
        )

        # Verify message was delivered
        coordination_protocols._deliver_message.assert_called_once()

        # Check metrics
        assert coordination_protocols.coordination_metrics['messages_sent'] == 1

    @pytest.mark.asyncio
    async def test_broadcast_message(self, coordination_protocols):
        """Test message broadcasting."""
        # Add known agents
        coordination_protocols.known_agents = {
            "agent_2": {"status": "active"},
            "agent_3": {"status": "active"}
        }

        # Mock message delivery
        coordination_protocols._deliver_message = AsyncMock()

        await coordination_protocols.broadcast_message(
            MessageType.STATUS_UPDATE,
            {"status": "healthy"},
            Priority.MEDIUM
        )

        # Should send to all known agents except self
        assert coordination_protocols._deliver_message.call_count == 2

    @pytest.mark.asyncio
    async def test_capability_registration(self, coordination_protocols):
        """Test capability registration."""
        capability = await coordination_protocols.register_capability(
            name="data_processing",
            description="Process large datasets",
            performance_score=0.9,
            resource_requirements={"cpu": 4, "memory": 8192},
            availability=0.8,
            specializations=["machine_learning", "analytics"]
        )

        assert isinstance(capability, AgentCapability)
        assert capability.name == "data_processing"
        assert capability.performance_score == 0.9
        assert capability.availability == 0.8
        assert "machine_learning" in capability.specializations

        # Verify capability is stored
        assert capability.capability_id in coordination_protocols.capabilities

    @pytest.mark.asyncio
    async def test_find_agents_with_capability(self, coordination_protocols):
        """Test finding agents with specific capabilities."""
        # Add mock agent capabilities
        coordination_protocols.agent_capabilities = {
            "agent_2": {
                "cap_1": AgentCapability(
                    capability_id="cap_1",
                    name="data_processing",
                    description="Process data",
                    performance_score=0.9,
                    resource_requirements={},
                    availability=0.8,
                    specializations=[]
                )
            },
            "agent_3": {
                "cap_2": AgentCapability(
                    capability_id="cap_2",
                    name="data_processing",
                    description="Process data",
                    performance_score=0.7,
                    resource_requirements={},
                    availability=0.6,
                    specializations=[]
                )
            }
        }

        # Find agents with data_processing capability
        matching_agents = await coordination_protocols.find_agents_with_capability(
            "data_processing",
            min_performance=0.8,
            min_availability=0.7
        )

        assert len(matching_agents) == 1
        assert matching_agents[0][0] == "agent_2"
        assert matching_agents[0][1].performance_score == 0.9

    @pytest.mark.asyncio
    async def test_coordination_session(self, coordination_protocols):
        """Test coordination session management."""
        participants = {"agent_2", "agent_3"}
        objective = "Complete data processing task"

        # Mock message sending
        coordination_protocols.send_message = AsyncMock()

        session = await coordination_protocols.initiate_coordination_session(
            participants,
            objective,
            CoordinationStrategy.PEER_TO_PEER
        )

        assert isinstance(session, CoordinationSession)
        assert session.participants == participants | {"test_agent_1"}
        assert session.coordinator_id == "test_agent_1"
        assert session.objective == objective
        assert session.strategy == CoordinationStrategy.PEER_TO_PEER

        # Verify session is stored
        assert session.session_id in coordination_protocols.active_sessions

        # Verify coordination requests were sent
        assert coordination_protocols.send_message.call_count == len(participants)


class TestIntelligentTaskAllocator:
    """Test suite for Intelligent Task Allocator."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)
        yield db_path
        os.unlink(db_path)

    @pytest.fixture
    def task_allocator(self, temp_db):
        """Create task allocator instance."""
        config = {"db_path": temp_db}
        return IntelligentTaskAllocator(config)

    @pytest.mark.asyncio
    async def test_submit_task(self, task_allocator):
        """Test task submission."""
        requirements = ResourceRequirements(
            cpu_cores=2,
            memory_mb=4096,
            disk_mb=1024,
            network_mbps=10
        )

        task = await task_allocator.submit_task(
            task_type="data_processing",
            priority=TaskPriority.HIGH,
            complexity=TaskComplexity.MODERATE,
            requirements=requirements,
            dependencies=["task_1"],
            deadline=datetime.now() + timedelta(hours=2)
        )

        assert isinstance(task, IntelligentTask)
        assert task.task_type == "data_processing"
        assert task.priority == TaskPriority.HIGH
        assert task.complexity == TaskComplexity.MODERATE
        assert task.requirements == requirements
        assert len(task.dependencies) == 1
        assert task.dependencies[0] == "task_1"

        # Verify task is in queue
        assert len(task_allocator.task_queue) == 1
        assert task_allocator.task_queue[0].task_id == task.task_id

    @pytest.mark.asyncio
    async def test_allocate_task(self, task_allocator):
        """Test task allocation."""
        # Create a test task
        requirements = ResourceRequirements(cpu_cores=1, memory_mb=512)
        task = IntelligentTask(
            task_id="test_task_1",
            task_type="simple_task",
            priority=TaskPriority.MEDIUM,
            complexity=TaskComplexity.SIMPLE,
            requirements=requirements
        )

        # Create mock agents
        agent1 = Mock()
        agent1.agent_id = "agent_1"
        agent1.active_tasks = 1
        agent1.error_count = 0
        agent1.registration = Mock()
        agent1.registration.capabilities = ["simple_task"]
        agent1.resource_allocation = Mock()
        agent1.resource_allocation.allocated_cpu = 4
        agent1.resource_allocation.allocated_memory = 8192
        agent1.resource_allocation.allocated_disk = 10240
        agent1.resource_allocation.allocated_network = 100

        agent2 = Mock()
        agent2.agent_id = "agent_2"
        agent2.active_tasks = 3
        agent2.error_count = 1
        agent2.registration = Mock()
        agent2.registration.capabilities = ["simple_task"]
        agent2.resource_allocation = Mock()
        agent2.resource_allocation.allocated_cpu = 2
        agent2.resource_allocation.allocated_memory = 4096
        agent2.resource_allocation.allocated_disk = 5120
        agent2.resource_allocation.allocated_network = 50

        available_agents = [agent1, agent2]

        # Mock dependency check
        task_allocator._check_dependencies = AsyncMock(return_value=True)

        # Mock allocation performance with side effects
        async def mock_perform_allocation(task, agent):
            # Simulate the actual allocation behavior
            task_allocator.active_tasks[task.task_id] = task
            task_allocator.agent_workloads[agent.agent_id] = task_allocator.agent_workloads.get(agent.agent_id, 0) + 1
            task.allocation_attempts += 1
            return True

        task_allocator._perform_allocation = AsyncMock(side_effect=mock_perform_allocation)

        # Allocate task
        selected_agent_id = await task_allocator.allocate_task(
            task,
            available_agents,
            AllocationStrategy.LOAD_BALANCED
        )

        # Should select agent1 (lower workload)
        assert selected_agent_id == "agent_1"

        # Verify task is moved to active tasks
        assert task.task_id in task_allocator.active_tasks

        # Verify workload is updated
        assert task_allocator.agent_workloads["agent_1"] == 1

    @pytest.mark.asyncio
    async def test_complete_task(self, task_allocator):
        """Test task completion."""
        # Create and add active task
        task = IntelligentTask(
            task_id="test_task_1",
            task_type="simple_task",
            priority=TaskPriority.MEDIUM,
            complexity=TaskComplexity.SIMPLE,
            requirements=ResourceRequirements()
        )
        task_allocator.active_tasks[task.task_id] = task
        task_allocator.agent_workloads["agent_1"] = 1

        # Mock performance profile update
        task_allocator._update_agent_performance = AsyncMock()
        task_allocator._learn_from_completion = AsyncMock()
        task_allocator._store_task_completion = AsyncMock()

        # Complete task
        await task_allocator.complete_task(
            task_id="test_task_1",
            agent_id="agent_1",
            success=True,
            execution_duration=120.0,
            quality_score=0.9,
            resource_utilization={"cpu": 0.6, "memory": 0.4},
            error_count=0
        )

        # Verify task is moved to completed tasks
        assert "test_task_1" in task_allocator.completed_tasks
        assert "test_task_1" not in task_allocator.active_tasks

        # Verify workload is updated
        assert task_allocator.agent_workloads["agent_1"] == 0

        # Verify task metrics
        task_metrics = task_allocator.completed_tasks["test_task_1"]
        assert task_metrics.success is True
        assert task_metrics.execution_duration == 120.0
        assert task_metrics.quality_score == 0.9
        assert task_metrics.error_count == 0

    @pytest.mark.asyncio
    async def test_agent_performance_profile(self, task_allocator):
        """Test agent performance profile management."""
        # Create performance profile
        profile = AgentPerformanceProfile(
            agent_id="test_agent",
            task_types={"data_processing": 0.8, "analysis": 0.7},
            complexity_handling={
                TaskComplexity.SIMPLE: 0.9,
                TaskComplexity.MODERATE: 0.8,
                TaskComplexity.COMPLEX: 0.6
            },
            resource_efficiency={"cpu": 0.8, "memory": 0.9},
            reliability_score=0.85,
            throughput_score=0.9,
            quality_score=0.8,
            learning_rate=0.1,
            specializations=["machine_learning", "data_science"]
        )

        # Test performance score calculation
        score = profile.get_performance_score("data_processing", TaskComplexity.MODERATE)
        assert 0.0 <= score <= 1.0

        # Test performance update
        from intelligent_task_allocation import TaskMetrics
        metrics = TaskMetrics(
            task_id="test_task",
            allocated_agent="test_agent",
            allocation_time=datetime.now(),
            completion_time=datetime.now(),
            execution_duration=100.0,
            quality_score=0.9,
            success=True
        )

        initial_completed = profile.completed_tasks
        profile.update_performance(metrics)

        assert profile.completed_tasks == initial_completed + 1
        assert len(profile.recent_performance) > 0
        assert profile.recent_performance[-1] == 1.0  # Success

    @pytest.mark.asyncio
    async def test_task_recommendations(self, task_allocator):
        """Test task recommendations."""
        # Create agent profile
        agent_profile = AgentPerformanceProfile(
            agent_id="test_agent",
            task_types={"data_processing": 0.9, "analysis": 0.7},
            complexity_handling={TaskComplexity.SIMPLE: 0.9, TaskComplexity.MODERATE: 0.8},
            resource_efficiency={"cpu": 0.8},
            reliability_score=0.85,
            throughput_score=0.9,
            quality_score=0.8,
            learning_rate=0.1,
            specializations=[]
        )

        task_allocator.agent_profiles["test_agent"] = agent_profile

        # Create test tasks
        task1 = IntelligentTask(
            task_id="task_1",
            task_type="data_processing",
            priority=TaskPriority.HIGH,
            complexity=TaskComplexity.SIMPLE,
            requirements=ResourceRequirements()
        )

        task2 = IntelligentTask(
            task_id="task_2",
            task_type="analysis",
            priority=TaskPriority.MEDIUM,
            complexity=TaskComplexity.COMPLEX,
            requirements=ResourceRequirements()
        )

        task_allocator.task_queue = [task1, task2]

        # Get recommendations
        recommendations = await task_allocator.get_task_recommendations("test_agent", max_recommendations=2)

        assert len(recommendations) <= 2
        for task, score in recommendations:
            assert isinstance(task, IntelligentTask)
            assert 0.0 <= score <= 1.0

        # Tasks should be ordered by score
        if len(recommendations) > 1:
            assert recommendations[0][1] >= recommendations[1][1]


class TestPerformanceMonitoring:
    """Test suite for Performance Monitoring and Optimization."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)
        yield db_path
        os.unlink(db_path)

    @pytest.fixture
    def performance_monitor(self, temp_db):
        """Create performance monitor instance."""
        config = {"db_path": temp_db}
        return PerformanceMonitoringOptimization(config)

    @pytest.mark.asyncio
    async def test_record_metric(self, performance_monitor):
        """Test metric recording."""
        await performance_monitor.record_metric(
            PerformanceMetricType.RESPONSE_TIME,
            1.5,
            "test_source",
            context={"operation": "task_allocation"},
            tags={"environment": "test"}
        )

        # Verify metric is in buffer
        assert len(performance_monitor.metrics_buffer) == 1
        metric = performance_monitor.metrics_buffer[0]
        assert metric.metric_type == PerformanceMetricType.RESPONSE_TIME
        assert metric.value == 1.5
        assert metric.source == "test_source"

        # Verify metric history
        assert PerformanceMetricType.RESPONSE_TIME in performance_monitor.metric_history
        assert len(performance_monitor.metric_history[PerformanceMetricType.RESPONSE_TIME]) == 1

    @pytest.mark.asyncio
    async def test_threshold_checking(self, performance_monitor):
        """Test performance threshold checking."""
        # Record a metric that exceeds threshold
        await performance_monitor.record_metric(
            PerformanceMetricType.RESPONSE_TIME,
            6.0,  # Exceeds critical threshold of 5.0
            "test_source"
        )

        # Wait for threshold check
        await asyncio.sleep(0.1)

        # Verify alert was created
        assert len(performance_monitor.active_alerts) > 0

        # Check alert details
        alert = next(iter(performance_monitor.active_alerts.values()))
        assert alert.metric_type == PerformanceMetricType.RESPONSE_TIME
        assert alert.level == AlertLevel.CRITICAL
        assert alert.value == 6.0
        assert not alert.resolved

    @pytest.mark.asyncio
    async def test_system_health_assessment(self, performance_monitor):
        """Test system health assessment."""
        # Mock system resource monitor
        performance_monitor.system_resource_monitor = Mock()
        performance_monitor.system_resource_monitor.get_cpu_usage.return_value = 50.0
        performance_monitor.system_resource_monitor.get_memory_usage.return_value = 60.0
        performance_monitor.system_resource_monitor.get_disk_usage.return_value = 40.0

        # Record some metrics
        await performance_monitor.record_metric(
            PerformanceMetricType.TASK_COMPLETION_RATE,
            0.95,
            "test_source"
        )

        await performance_monitor.record_metric(
            PerformanceMetricType.ERROR_RATE,
            0.02,
            "test_source"
        )

        # Get system health
        health_status = await performance_monitor.get_system_health()

        assert 0.0 <= health_status.overall_health <= 1.0
        assert isinstance(health_status.component_health, dict)
        assert isinstance(health_status.active_alerts, list)
        assert isinstance(health_status.recent_metrics, dict)
        assert isinstance(health_status.optimization_recommendations, list)

    @pytest.mark.asyncio
    async def test_optimization_recommendations(self, performance_monitor):
        """Test optimization recommendation generation."""
        # Set up mock metrics that would trigger optimizations
        performance_monitor.metric_history[PerformanceMetricType.RESPONSE_TIME] = [
            Mock(value=3.0, timestamp=datetime.now())
        ]

        performance_monitor.metric_history[PerformanceMetricType.ERROR_RATE] = [
            Mock(value=0.08, timestamp=datetime.now())
        ]

        # Generate optimization recommendations
        recommendations = await performance_monitor.optimize_performance([
            PerformanceMetricType.RESPONSE_TIME,
            PerformanceMetricType.ERROR_RATE
        ])

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

        for recommendation in recommendations:
            assert hasattr(recommendation, 'action')
            assert hasattr(recommendation, 'description')
            assert hasattr(recommendation, 'confidence')
            assert hasattr(recommendation, 'impact_score')
            assert 0.0 <= recommendation.confidence <= 1.0
            assert 0.0 <= recommendation.impact_score <= 1.0

    @pytest.mark.asyncio
    async def test_performance_report(self, performance_monitor):
        """Test performance report generation."""
        # Add some historical metrics
        now = datetime.now()
        for i in range(5):
            await performance_monitor.record_metric(
                PerformanceMetricType.THROUGHPUT,
                50.0 + i * 5,
                "test_source",
                context={"iteration": i}
            )

        # Generate performance report
        report = await performance_monitor.get_performance_report(
            time_range=timedelta(hours=1)
        )

        assert 'time_range' in report
        assert 'statistics' in report
        assert 'trends' in report
        assert 'system_health' in report

        # Verify time range
        assert 'start' in report['time_range']
        assert 'end' in report['time_range']

    @pytest.mark.asyncio
    async def test_monitoring_lifecycle(self, performance_monitor):
        """Test monitoring start/stop lifecycle."""
        # Start monitoring
        await performance_monitor.start_monitoring()
        assert performance_monitor.monitoring_active is True
        assert len(performance_monitor.monitoring_tasks) > 0

        # Stop monitoring
        await performance_monitor.stop_monitoring()
        assert performance_monitor.monitoring_active is False
        assert len(performance_monitor.monitoring_tasks) == 0


class TestIntegration:
    """Integration tests for the complete intelligence framework."""

    @pytest.fixture
    def temp_db_paths(self):
        """Create temporary database files."""
        paths = {}
        for component in ['intelligence', 'coordination', 'allocation', 'monitoring']:
            db_fd, db_path = tempfile.mkstemp(suffix=f'_{component}.db')
            os.close(db_fd)
            paths[component] = db_path

        yield paths

        for db_path in paths.values():
            os.unlink(db_path)

    @pytest.fixture
    def integrated_system(self, temp_db_paths):
        """Create integrated system with all components."""
        # Create configurations
        intelligence_config = IntelligenceConfig(
            intelligence_level=IntelligenceLevel.ADVANCED,
            db_path=temp_db_paths['intelligence']
        )

        task_allocator_config = {
            'db_path': temp_db_paths['allocation']
        }

        monitoring_config = {
            'db_path': temp_db_paths['monitoring']
        }

        # Create components
        intelligence_framework = IntelligenceFramework(intelligence_config)
        coordination_protocols = AgentCoordinationProtocols("system_agent")
        task_allocator = IntelligentTaskAllocator(task_allocator_config)
        performance_monitor = PerformanceMonitoringOptimization(monitoring_config)

        # Set up component references
        performance_monitor.set_components(
            intelligence_framework,
            task_allocator,
            coordination_protocols
        )

        return {
            'intelligence': intelligence_framework,
            'coordination': coordination_protocols,
            'allocation': task_allocator,
            'monitoring': performance_monitor
        }

    @pytest.mark.asyncio
    async def test_end_to_end_task_processing(self, integrated_system):
        """Test end-to-end task processing workflow."""
        intelligence = integrated_system['intelligence']
        coordination = integrated_system['coordination']
        allocation = integrated_system['allocation']
        monitoring = integrated_system['monitoring']

        # Start systems
        await intelligence.start()
        await monitoring.start_monitoring()

        try:
            # Submit a task
            requirements = ResourceRequirements(cpu_cores=2, memory_mb=4096)
            task = await allocation.submit_task(
                task_type="data_processing",
                priority=TaskPriority.HIGH,
                complexity=TaskComplexity.MODERATE,
                requirements=requirements
            )

            # Record task submission metric
            await monitoring.record_metric(
                PerformanceMetricType.THROUGHPUT,
                1.0,
                "task_allocation",
                context={"task_id": task.task_id}
            )

            # Make decision about task allocation
            decision = await intelligence.make_decision(
                DecisionType.TASK_ALLOCATION,
                {
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "priority": task.priority.value,
                    "complexity": task.complexity.value
                }
            )

            # Verify decision was made
            assert decision is not None
            assert decision.decision_type == DecisionType.TASK_ALLOCATION
            assert decision.confidence > 0.0

            # Allocate task to agent (simulate agent allocation)
            from advanced_orchestration.models import AgentInfo, AgentStatus, AgentRegistration
            from unittest.mock import Mock

            # Create mock agent
            mock_agent = Mock()
            mock_agent.agent_id = "test_agent"
            mock_agent.active_tasks = 0
            mock_agent.error_count = 0
            mock_agent.registration = Mock()
            mock_agent.registration.capabilities = ["data_processing"]
            mock_agent.resource_allocation = Mock()
            mock_agent.resource_allocation.allocated_cpu = 4
            mock_agent.resource_allocation.allocated_memory = 8192
            mock_agent.resource_allocation.allocated_disk = 10240
            mock_agent.resource_allocation.allocated_network = 100

            # Allocate task to agent
            allocated_agent = await allocation.allocate_task(
                task,
                [mock_agent],
                AllocationStrategy.INTELLIGENT_HYBRID
            )

            assert allocated_agent == "test_agent"
            assert task.task_id in allocation.active_tasks

            # Simulate task completion
            await allocation.complete_task(
                task_id=task.task_id,
                agent_id="test_agent",
                success=True,
                execution_duration=120.0,
                quality_score=0.9,
                resource_utilization={"cpu": 0.6, "memory": 0.4}
            )

            # Record completion metric
            await monitoring.record_metric(
                PerformanceMetricType.TASK_COMPLETION_RATE,
                1.0,
                "task_allocation",
                context={"task_id": task.task_id}
            )

            # Verify task was completed
            assert task.task_id in allocation.completed_tasks

            # Get system health
            health = await monitoring.get_system_health()
            assert health.overall_health > 0.0

        finally:
            # Stop systems
            await intelligence.stop()
            await monitoring.stop_monitoring()

    @pytest.mark.asyncio
    async def test_agent_coordination_workflow(self, integrated_system):
        """Test agent coordination workflow."""
        coordination = integrated_system['coordination']
        intelligence = integrated_system['intelligence']

        # Start intelligence framework
        await intelligence.start()

        try:
            # Register agent capabilities
            capability = await coordination.register_capability(
                name="data_processing",
                description="Process data efficiently",
                performance_score=0.9,
                resource_requirements={"cpu": 4, "memory": 8192},
                availability=0.8
            )

            # Create coordination session
            session = await coordination.initiate_coordination_session(
                participants={"agent_2", "agent_3"},
                objective="Process large dataset collaboratively",
                strategy=CoordinationStrategy.PEER_TO_PEER
            )

            # Make coordination decision
            decision = await intelligence.make_decision(
                DecisionType.AGENT_COORDINATION,
                {
                    "session_id": session.session_id,
                    "participants": list(session.participants),
                    "objective": session.objective,
                    "strategy": session.strategy.value
                }
            )

            # Verify coordination decision
            assert decision is not None
            assert decision.decision_type == DecisionType.AGENT_COORDINATION

            # Verify session was created
            assert session.session_id in coordination.active_sessions
            assert len(session.participants) == 3  # Including coordinator

        finally:
            await intelligence.stop()

    @pytest.mark.asyncio
    async def test_performance_optimization_workflow(self, integrated_system):
        """Test performance optimization workflow."""
        monitoring = integrated_system['monitoring']
        intelligence = integrated_system['intelligence']
        allocation = integrated_system['allocation']

        # Start systems
        await intelligence.start()
        await monitoring.start_monitoring()

        try:
            # Record performance metrics that would trigger optimization
            await monitoring.record_metric(
                PerformanceMetricType.RESPONSE_TIME,
                3.5,  # Above warning threshold
                "system",
                context={"component": "task_allocation"}
            )

            await monitoring.record_metric(
                PerformanceMetricType.ERROR_RATE,
                0.08,  # Above warning threshold
                "system",
                context={"component": "task_processing"}
            )

            # Generate optimization recommendations
            recommendations = await monitoring.optimize_performance()

            # Verify recommendations were generated
            assert len(recommendations) > 0

            # Make performance optimization decision
            decision = await intelligence.make_decision(
                DecisionType.PERFORMANCE_TUNING,
                {
                    "current_response_time": 3.5,
                    "current_error_rate": 0.08,
                    "recommendations": [rec.to_dict() for rec in recommendations[:3]]
                }
            )

            # Verify optimization decision
            assert decision is not None
            assert decision.decision_type == DecisionType.PERFORMANCE_TUNING

            # Test optimization implementation
            if recommendations:
                implementation_result = await monitoring.implement_optimization(
                    recommendations[0].recommendation_id
                )
                assert 'success' in implementation_result

        finally:
            await intelligence.stop()
            await monitoring.stop_monitoring()

    @pytest.mark.asyncio
    async def test_system_health_monitoring(self, integrated_system):
        """Test system health monitoring."""
        monitoring = integrated_system['monitoring']
        intelligence = integrated_system['intelligence']

        # Start systems
        await intelligence.start()
        await monitoring.start_monitoring()

        try:
            # Record various metrics
            metrics_to_record = [
                (PerformanceMetricType.RESPONSE_TIME, 1.2),
                (PerformanceMetricType.THROUGHPUT, 75.0),
                (PerformanceMetricType.ERROR_RATE, 0.03),
                (PerformanceMetricType.RESOURCE_UTILIZATION, 0.65),
                (PerformanceMetricType.TASK_COMPLETION_RATE, 0.92)
            ]

            for metric_type, value in metrics_to_record:
                await monitoring.record_metric(
                    metric_type,
                    value,
                    "system_test",
                    context={"test": "health_monitoring"}
                )

            # Get system health
            health = await monitoring.get_system_health()

            # Verify health assessment
            assert 0.0 <= health.overall_health <= 1.0
            assert len(health.component_health) > 0
            assert isinstance(health.recent_metrics, dict)

            # Generate performance report
            report = await monitoring.get_performance_report(
                time_range=timedelta(minutes=5)
            )

            # Verify report structure
            assert 'time_range' in report
            assert 'statistics' in report
            assert 'system_health' in report

        finally:
            await intelligence.stop()
            await monitoring.stop_monitoring()


# Additional utility functions for testing
def create_mock_agent_info(agent_id: str) -> AgentInfo:
    """Create a mock AgentInfo for testing."""
    registration = AgentRegistration(
        agent_id=agent_id,
        capabilities=["processing", "analysis"],
        resource_requirements=ResourceRequirements(
            cpu_cores=2,
            memory_mb=4096,
            disk_mb=10240,
            network_mbps=100
        ),
        metadata=AgentMetadata(
            agent_type="worker",
            version="1.0.0",
            startup_time=datetime.now(),
            last_heartbeat=datetime.now(),
            capabilities=["processing"],
            resource_requirements=ResourceRequirements()
        )
    )

    return AgentInfo(
        agent_id=agent_id,
        status=AgentStatus.HEALTHY,
        registration=registration,
        active_tasks=0,
        error_count=0,
        last_heartbeat=datetime.now()
    )


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
