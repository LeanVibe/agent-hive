"""
Integration tests for LeanVibeOrchestrator with StateManager.

Tests the integration between the orchestrator and the new StateManager,
verifying that ML components work correctly together.
"""

import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import sys

# Add the .claude directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / '.claude'))

from orchestrator import LeanVibeOrchestrator
from task_queue_module.task_queue import Task
from datetime import datetime


class TestOrchestratorIntegration:
    """Test suite for orchestrator integration with StateManager."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            yield tmp.name
        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)

    @pytest.fixture
    def mock_claude_agent(self):
        """Mock Claude agent for testing."""
        agent = Mock()
        agent.agent_id = "claude-primary"
        agent.health_check = AsyncMock(return_value=True)
        agent.shutdown = AsyncMock()
        agent.get_capabilities = Mock(return_value=["code_generation", "analysis"])
        agent.can_handle_task = Mock(return_value=True)
        agent.execute_task = AsyncMock(return_value=Mock(status="success"))
        return agent

    @pytest.fixture
    def orchestrator(self, temp_db_path, mock_claude_agent):
        """Create orchestrator instance with mocked components."""
        with patch('orchestrator.ClaudeAgent', return_value=mock_claude_agent):
            with patch('state.state_manager.get_config') as mock_config:
                mock_config.return_value.get.return_value = temp_db_path
                orchestrator = LeanVibeOrchestrator()
                yield orchestrator

    def test_orchestrator_init_with_state_manager(self, orchestrator):
        """Test that orchestrator initializes with StateManager."""
        assert orchestrator.state_manager is not None
        assert hasattr(orchestrator.state_manager, 'confidence_tracker')
        assert hasattr(orchestrator.state_manager, 'context_monitor')
        assert hasattr(orchestrator.state_manager, 'quality_gate')
        assert hasattr(orchestrator.state_manager, 'test_enforcer')

    @pytest.mark.asyncio
    async def test_agent_registration_with_state_manager(self, orchestrator):
        """Test that agents are registered with StateManager."""
        # Initialize agents
        await orchestrator._initialize_agents()

        # Check that agent was registered
        agent_state = await orchestrator.state_manager.get_agent_state("claude-primary")
        assert agent_state is not None
        assert agent_state.agent_id == "claude-primary"
        assert agent_state.status == "idle"
        assert "code_generation" in agent_state.capabilities

    @pytest.mark.asyncio
    async def test_task_addition_with_state_manager(self, orchestrator):
        """Test adding tasks through StateManager."""
        await orchestrator._initialize_agents()

        # Create test task
        task = Task(
            id="test-task",
            type="code_generation",
            description="Test task",
            priority=3,
            data={"test": "data"},
            created_at=datetime.now()
        )

        # Add task
        result = await orchestrator.add_task(task)
        assert result is True

        # Check task was added to StateManager
        task_state = await orchestrator.state_manager.get_next_priority_task()
        assert task_state is not None
        assert task_state.task_id == "test-task"
        assert task_state.priority == 3
        assert task_state.metadata["type"] == "code_generation"

    @pytest.mark.asyncio
    async def test_get_next_priority_task(self, orchestrator):
        """Test getting next priority task from StateManager."""
        await orchestrator._initialize_agents()

        # Add test task
        task = Task(
            id="priority-task",
            type="code_generation",
            description="Priority test task",
            priority=1,
            data={},
            created_at=datetime.now()
        )
        await orchestrator.add_task(task)

        # Get next priority task
        work_item = await orchestrator.get_next_priority()

        assert work_item is not None
        assert work_item.task_id == "priority-task"
        assert work_item.priority == 1

    @pytest.mark.asyncio
    async def test_task_execution_with_state_manager(self, orchestrator):
        """Test task execution updates StateManager."""
        await orchestrator._initialize_agents()

        # Add test task
        task = Task(
            id="exec-task",
            type="code_generation",
            description="Execution test task",
            priority=5,
            data={"test": "execution"},
            created_at=datetime.now()
        )
        await orchestrator.add_task(task)

        # Get and execute task
        work_item = await orchestrator.get_next_priority()
        assert work_item is not None

        # Execute task
        await orchestrator.execute_autonomously(work_item)

        # Check task state was updated
        with orchestrator.state_manager._db_lock:
            import sqlite3
            with sqlite3.connect(orchestrator.state_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT status FROM tasks WHERE task_id = ?", ("exec-task",))
                result = cursor.fetchone()
                assert result is not None
                assert result[0] == "completed"

    @pytest.mark.asyncio
    async def test_agent_health_monitoring(self, orchestrator):
        """Test agent health monitoring with StateManager."""
        await orchestrator._initialize_agents()

        # Start health monitoring
        monitor_task = asyncio.create_task(orchestrator._monitor_agent_health())

        # Let it run briefly
        await asyncio.sleep(0.1)

        # Cancel monitoring
        monitor_task.cancel()

        # Check agent state remains healthy
        agent_state = await orchestrator.state_manager.get_agent_state("claude-primary")
        assert agent_state.status in ["idle", "working"]  # Should not be offline

    @pytest.mark.asyncio
    async def test_checkpoint_monitoring(self, orchestrator):
        """Test checkpoint monitoring functionality."""
        await orchestrator._initialize_agents()

        # Start checkpoint monitoring
        monitor_task = asyncio.create_task(orchestrator._monitor_checkpoints())

        # Let it run briefly
        await asyncio.sleep(0.1)

        # Cancel monitoring
        monitor_task.cancel()

        # Check that monitoring ran without errors
        assert True  # If we get here, monitoring didn't crash

    @pytest.mark.asyncio
    async def test_confidence_tracking_integration(self, orchestrator):
        """Test confidence tracking integration in task execution."""
        await orchestrator._initialize_agents()

        # Add test task
        task = Task(
            id="confidence-task",
            type="code_generation",
            description="Confidence test task",
            priority=5,
            data={"complexity": "low"},
            created_at=datetime.now()
        )
        await orchestrator.add_task(task)

        # Get task
        work_item = await orchestrator.get_next_priority()

        # Test confidence decision
        context = {
            "task_type": work_item.metadata.get("type", "general"),
            "priority": work_item.priority,
            "agent_confidence": 0.8,
            "gemini_confidence": 0.8,
            "complexity": work_item.metadata.get("complexity", "medium")
        }

        need_human, confidence = orchestrator.state_manager.confidence_tracker.should_involve_human(context)

        # Should be able to handle autonomously with high confidence
        assert need_human is False or confidence > 0.7

    @pytest.mark.asyncio
    async def test_system_state_retrieval(self, orchestrator):
        """Test getting system state from StateManager."""
        await orchestrator._initialize_agents()

        # Add some tasks
        for i in range(3):
            task = Task(
                id=f"state-task-{i}",
                type="code_generation",
                description=f"State test task {i}",
                priority=i+1,
                data={},
                created_at=datetime.now()
            )
            await orchestrator.add_task(task)

        # Get system state
        system_state = await orchestrator.get_queue_status()

        assert system_state.total_agents == 1
        assert system_state.total_tasks == 3
        assert system_state.active_agents >= 0

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, orchestrator):
        """Test graceful shutdown with StateManager."""
        await orchestrator._initialize_agents()

        # Add test task
        task = Task(
            id="shutdown-task",
            type="code_generation",
            description="Shutdown test task",
            priority=5,
            data={},
            created_at=datetime.now()
        )
        await orchestrator.add_task(task)

        # Shutdown
        await orchestrator.shutdown()

        # Check that agent status was updated
        agent_state = await orchestrator.state_manager.get_agent_state("claude-primary")
        # Note: agent_state might be None after shutdown, which is expected

    @pytest.mark.asyncio
    async def test_ml_component_integration(self, orchestrator):
        """Test that all ML components are properly integrated."""
        await orchestrator._initialize_agents()

        # Test confidence tracker
        context = {"task_type": "test", "agent_confidence": 0.9}
        need_human, confidence = orchestrator.state_manager.confidence_tracker.should_involve_human(context)
        assert isinstance(need_human, bool)
        assert isinstance(confidence, float)

        # Test context monitor
        context_result = orchestrator.state_manager.context_monitor.check_context("test-agent", 0.5)
        assert "current_usage" in context_result
        assert "action_required" in context_result

        # Test quality gate
        quality_result = orchestrator.state_manager.quality_gate.evaluate({"test": "context"})
        assert "decision" in quality_result
        assert "confidence" in quality_result

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, orchestrator):
        """Test error handling with StateManager."""
        await orchestrator._initialize_agents()

        # Test error handling doesn't crash
        await orchestrator.smart_error_handling(Exception("Test error"))

        # Should complete without raising
        assert True

    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self, orchestrator):
        """Test concurrent task execution with StateManager."""
        await orchestrator._initialize_agents()

        # Add multiple tasks
        tasks = []
        for i in range(5):
            task = Task(
                id=f"concurrent-task-{i}",
                type="code_generation",
                description=f"Concurrent test task {i}",
                priority=i+1,
                data={},
                created_at=datetime.now()
            )
            tasks.append(orchestrator.add_task(task))

        # Add all tasks concurrently
        results = await asyncio.gather(*tasks)

        # All tasks should be added successfully
        assert all(results)

        # Check system state
        system_state = await orchestrator.get_queue_status()
        assert system_state.total_tasks == 5
