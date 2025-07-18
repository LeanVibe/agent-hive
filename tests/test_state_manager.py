"""
Unit tests for StateManager - Centralized state management system.

Tests the comprehensive state management system with SQLite backend,
including agent states, task states, checkpoints, and ML integration.
"""

import asyncio
import json
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from state.state_manager import (
    AgentState,
    StateManager,
    SystemState,
    TaskState,
)

# Add the .claude directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / '.claude'))


class TestAgentState:
    """Test suite for AgentState dataclass."""

    def test_agent_state_creation(self):
        """Test AgentState creation with defaults."""
        state = AgentState(agent_id="test-agent", status="idle")

        assert state.agent_id == "test-agent"
        assert state.status == "idle"
        assert state.current_task_id is None
        assert state.context_usage == 0.0
        assert state.last_activity is not None
        assert state.capabilities == []
        assert state.performance_metrics == {}

    def test_agent_state_with_data(self):
        """Test AgentState creation with full data."""
        now = datetime.now()
        state = AgentState(
            agent_id="test-agent",
            status="working",
            current_task_id="task-123",
            context_usage=0.75,
            last_activity=now,
            capabilities=["python", "javascript"],
            performance_metrics={"speed": 0.8, "accuracy": 0.9}
        )

        assert state.agent_id == "test-agent"
        assert state.status == "working"
        assert state.current_task_id == "task-123"
        assert state.context_usage == 0.75
        assert state.last_activity == now
        assert state.capabilities == ["python", "javascript"]
        assert state.performance_metrics == {"speed": 0.8, "accuracy": 0.9}


class TestTaskState:
    """Test suite for TaskState dataclass."""

    def test_task_state_creation(self):
        """Test TaskState creation with defaults."""
        state = TaskState(task_id="test-task", status="pending")

        assert state.task_id == "test-task"
        assert state.status == "pending"
        assert state.agent_id is None
        assert state.priority == 5
        assert state.created_at is not None
        assert state.started_at is None
        assert state.completed_at is None
        assert state.metadata == {}

    def test_task_state_with_data(self):
        """Test TaskState creation with full data."""
        now = datetime.now()
        state = TaskState(
            task_id="test-task",
            status="in_progress",
            agent_id="agent-123",
            priority=1,
            created_at=now,
            started_at=now,
            metadata={"type": "code_generation", "complexity": "high"}
        )

        assert state.task_id == "test-task"
        assert state.status == "in_progress"
        assert state.agent_id == "agent-123"
        assert state.priority == 1
        assert state.created_at == now
        assert state.started_at == now
        assert state.metadata == {
            "type": "code_generation", "complexity": "high"}


class TestSystemState:
    """Test suite for SystemState dataclass."""

    def test_system_state_creation(self):
        """Test SystemState creation with defaults."""
        state = SystemState()

        assert state.total_agents == 0
        assert state.active_agents == 0
        assert state.total_tasks == 0
        assert state.completed_tasks == 0
        assert state.failed_tasks == 0
        assert state.average_context_usage == 0.0
        assert state.quality_score == 0.0
        assert state.last_checkpoint is None

    def test_system_state_with_data(self):
        """Test SystemState creation with data."""
        now = datetime.now()
        state = SystemState(
            total_agents=5,
            active_agents=3,
            total_tasks=100,
            completed_tasks=80,
            failed_tasks=5,
            average_context_usage=0.65,
            quality_score=0.85,
            last_checkpoint=now
        )

        assert state.total_agents == 5
        assert state.active_agents == 3
        assert state.total_tasks == 100
        assert state.completed_tasks == 80
        assert state.failed_tasks == 5
        assert state.average_context_usage == 0.65
        assert state.quality_score == 0.85
        assert state.last_checkpoint == now


class TestStateManager:
    """Test suite for StateManager functionality."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            yield tmp.name
        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)

    @pytest.fixture
    def state_manager(self, temp_db_path):
        """Create StateManager instance with temporary database."""
        with patch('state.state_manager.get_config') as mock_config:
            mock_config.return_value.get.return_value = temp_db_path
            manager = StateManager(db_path=temp_db_path)
            yield manager

    def test_init_creates_database_schema(self, temp_db_path):
        """Test that StateManager initialization creates proper database schema."""
        StateManager(db_path=temp_db_path)

        # Check database file exists
        assert Path(temp_db_path).exists()

        # Check schema exists
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()

            # Check tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            expected_tables = ['agents', 'tasks',
                               'system_snapshots', 'checkpoints']
            for table in expected_tables:
                assert table in tables

    @pytest.mark.asyncio
    async def test_register_agent_success(self, state_manager):
        """Test successful agent registration."""
        result = await state_manager.register_agent("test-agent", ["python", "javascript"])

        assert result is True

        # Check database
        with sqlite3.connect(state_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM agents WHERE agent_id = ?", ("test-agent",))
            row = cursor.fetchone()

            assert row is not None
            assert row[0] == "test-agent"  # agent_id
            assert row[1] == "idle"  # status
            assert json.loads(row[5]) == [
                "python", "javascript"]  # capabilities

    @pytest.mark.asyncio
    async def test_register_agent_updates_cache(self, state_manager):
        """Test that agent registration updates the cache."""
        await state_manager.register_agent("test-agent", ["python"])

        # Check cache
        assert "test-agent" in state_manager._agent_cache
        agent_state = state_manager._agent_cache["test-agent"]
        assert agent_state.agent_id == "test-agent"
        assert agent_state.status == "idle"
        assert agent_state.capabilities == ["python"]

    @pytest.mark.asyncio
    async def test_update_agent_state_success(self, state_manager):
        """Test successful agent state update."""
        await state_manager.register_agent("test-agent")

        result = await state_manager.update_agent_state(
            "test-agent",
            status="working",
            context_usage=0.6,
            current_task_id="task-123"
        )

        assert result is True

        # Check database
        with sqlite3.connect(state_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status, context_usage, current_task_id FROM agents WHERE agent_id = ?",
                ("test-agent",
                 ))
            row = cursor.fetchone()

            assert row[0] == "working"
            assert row[1] == 0.6
            assert row[2] == "task-123"

    @pytest.mark.asyncio
    async def test_update_agent_state_updates_cache(self, state_manager):
        """Test that agent state update updates the cache."""
        await state_manager.register_agent("test-agent")

        await state_manager.update_agent_state("test-agent", status="working", context_usage=0.8)

        # Check cache
        agent_state = state_manager._agent_cache["test-agent"]
        assert agent_state.status == "working"
        assert agent_state.context_usage == 0.8

    @pytest.mark.asyncio
    async def test_update_agent_state_nonexistent_agent(self, state_manager):
        """Test updating nonexistent agent returns False."""
        result = await state_manager.update_agent_state("nonexistent", status="working")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_agent_state_from_cache(self, state_manager):
        """Test getting agent state from cache."""
        await state_manager.register_agent("test-agent", ["python"])

        agent_state = await state_manager.get_agent_state("test-agent")

        assert agent_state is not None
        assert agent_state.agent_id == "test-agent"
        assert agent_state.status == "idle"
        assert agent_state.capabilities == ["python"]

    @pytest.mark.asyncio
    async def test_get_agent_state_from_database(self, state_manager):
        """Test getting agent state from database when not in cache."""
        # Clear cache first
        state_manager._agent_cache.clear()

        # Add directly to database
        with sqlite3.connect(state_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agents (agent_id, status, capabilities)
                VALUES (?, ?, ?)
            """, ("test-agent", "idle", json.dumps(["python"])))

        agent_state = await state_manager.get_agent_state("test-agent")

        assert agent_state is not None
        assert agent_state.agent_id == "test-agent"
        assert agent_state.status == "idle"
        assert agent_state.capabilities == ["python"]

        # Check that it's now in cache
        assert "test-agent" in state_manager._agent_cache

    @pytest.mark.asyncio
    async def test_get_agent_state_nonexistent(self, state_manager):
        """Test getting nonexistent agent state returns None."""
        agent_state = await state_manager.get_agent_state("nonexistent")

        assert agent_state is None

    @pytest.mark.asyncio
    async def test_add_task_success(self, state_manager):
        """Test successful task addition."""
        result = await state_manager.add_task("test-task", priority=3, metadata={"type": "test"})

        assert result is True

        # Check database
        with sqlite3.connect(state_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM tasks WHERE task_id = ?", ("test-task",))
            row = cursor.fetchone()

            assert row is not None
            assert row[0] == "test-task"  # task_id
            assert row[1] == "pending"  # status
            assert row[3] == 3  # priority
            assert json.loads(row[7]) == {"type": "test"}  # metadata

    @pytest.mark.asyncio
    async def test_add_task_updates_cache(self, state_manager):
        """Test that task addition updates the cache."""
        await state_manager.add_task("test-task", priority=2)

        # Check cache
        assert "test-task" in state_manager._task_cache
        task_state = state_manager._task_cache["test-task"]
        assert task_state.task_id == "test-task"
        assert task_state.status == "pending"
        assert task_state.priority == 2

    @pytest.mark.asyncio
    async def test_update_task_state_success(self, state_manager):
        """Test successful task state update."""
        await state_manager.add_task("test-task")

        result = await state_manager.update_task_state(
            "test-task",
            status="in_progress",
            agent_id="agent-123",
            priority=1
        )

        assert result is True

        # Check database
        with sqlite3.connect(state_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status, agent_id, priority, started_at FROM tasks WHERE task_id = ?",
                ("test-task",
                 ))
            row = cursor.fetchone()

            assert row[0] == "in_progress"
            assert row[1] == "agent-123"
            assert row[2] == 1
            assert row[3] is not None  # started_at should be set

    @pytest.mark.asyncio
    async def test_update_task_state_sets_timestamps(self, state_manager):
        """Test that task state updates set appropriate timestamps."""
        await state_manager.add_task("test-task")

        # Update to in_progress should set started_at
        await state_manager.update_task_state("test-task", status="in_progress")
        task_state = state_manager._task_cache["test-task"]
        assert task_state.started_at is not None

        # Update to completed should set completed_at
        await state_manager.update_task_state("test-task", status="completed")
        task_state = state_manager._task_cache["test-task"]
        assert task_state.completed_at is not None

    @pytest.mark.asyncio
    async def test_get_next_priority_task_success(self, state_manager):
        """Test getting next priority task."""
        # Add tasks with different priorities
        await state_manager.add_task("task-1", priority=5)
        await state_manager.add_task("task-2", priority=2)
        await state_manager.add_task("task-3", priority=8)

        # Get next priority task
        task = await state_manager.get_next_priority_task()

        assert task is not None
        assert task.task_id == "task-2"  # Priority 2 is highest
        assert task.priority == 2

    @pytest.mark.asyncio
    async def test_get_next_priority_task_none_available(self, state_manager):
        """Test getting next priority task when none available."""
        # Add completed task
        await state_manager.add_task("task-1")
        await state_manager.update_task_state("task-1", status="completed")

        task = await state_manager.get_next_priority_task()

        assert task is None

    @pytest.mark.asyncio
    async def test_get_system_state_success(self, state_manager):
        """Test getting system state."""
        # Add some agents and tasks
        await state_manager.register_agent("agent-1")
        await state_manager.register_agent("agent-2")
        await state_manager.update_agent_state("agent-1", status="working", context_usage=0.7)

        await state_manager.add_task("task-1")
        await state_manager.add_task("task-2")
        await state_manager.update_task_state("task-1", status="completed")
        await state_manager.update_task_state("task-2", status="failed")

        system_state = await state_manager.get_system_state()

        assert system_state.total_agents == 2
        assert system_state.active_agents == 2
        assert system_state.total_tasks == 2
        assert system_state.completed_tasks == 1
        assert system_state.failed_tasks == 1
        assert system_state.average_context_usage == 0.7

    @pytest.mark.asyncio
    async def test_create_checkpoint_success(self, state_manager):
        """Test successful checkpoint creation."""
        await state_manager.register_agent("agent-1")

        checkpoint_id = await state_manager.create_checkpoint("manual", agent_id="agent-1")

        assert checkpoint_id is not None
        assert checkpoint_id.startswith("checkpoint_")

        # Check database
        with sqlite3.connect(state_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM checkpoints WHERE checkpoint_id = ?", (checkpoint_id,))
            row = cursor.fetchone()

            assert row is not None
            assert row[1] == "manual"  # checkpoint_type
            assert row[2] == "agent-1"  # agent_id
            assert row[3] is not None  # state_data

    @pytest.mark.asyncio
    async def test_should_create_checkpoint_high_context_usage(
            self, state_manager):
        """Test checkpoint recommendation for high context usage."""
        await state_manager.register_agent("agent-1")
        await state_manager.update_agent_state("agent-1", context_usage=0.9)

        should_create, reason = await state_manager.should_create_checkpoint("agent-1")

        assert should_create is True
        assert "context usage" in reason.lower()

    @pytest.mark.asyncio
    async def test_should_create_checkpoint_low_context_usage(
            self, state_manager):
        """Test no checkpoint recommendation for low context usage."""
        await state_manager.register_agent("agent-1")
        await state_manager.update_agent_state("agent-1", context_usage=0.3)

        should_create, reason = await state_manager.should_create_checkpoint("agent-1")

        assert should_create is False
        assert "no checkpoint needed" in reason.lower()

    @pytest.mark.asyncio
    async def test_cleanup_old_data(self, state_manager):
        """Test cleanup of old data."""
        # Add some old data
        old_date = datetime.now() - timedelta(days=40)

        with sqlite3.connect(state_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (task_id, status, completed_at, created_at)
                VALUES (?, ?, ?, ?)
            """, ("old-task", "completed", old_date, old_date))

            cursor.execute("""
                INSERT INTO checkpoints (checkpoint_id, checkpoint_type, state_data, created_at)
                VALUES (?, ?, ?, ?)
            """, ("old-checkpoint", "auto", "{}", old_date))

        # Add recent data
        await state_manager.add_task("new-task")
        await state_manager.update_task_state("new-task", status="completed")

        # Cleanup
        deleted_count = await state_manager.cleanup_old_data(days_to_keep=30)

        assert deleted_count >= 1  # Should have deleted at least the old task

        # Check that new data remains
        with sqlite3.connect(state_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM tasks WHERE task_id = ?", ("new-task",))
            count = cursor.fetchone()[0]
            assert count == 1

    @pytest.mark.asyncio
    async def test_get_performance_metrics(self, state_manager):
        """Test getting performance metrics."""
        await state_manager.register_agent("agent-1")
        await state_manager.add_task("task-1")

        metrics = await state_manager.get_performance_metrics()

        assert 'system_state' in metrics
        assert 'confidence_tracking' in metrics
        assert 'context_monitoring' in metrics
        assert 'quality_gate' in metrics
        assert 'cache_size' in metrics
        assert 'database_size' in metrics

        # Check system state metrics
        system_state = metrics['system_state']
        assert system_state['total_agents'] == 1
        assert system_state['total_tasks'] == 1

    @pytest.mark.asyncio
    async def test_shutdown_creates_checkpoint(self, state_manager):
        """Test that shutdown creates a final checkpoint."""
        await state_manager.register_agent("agent-1")

        # Count checkpoints before shutdown
        with sqlite3.connect(state_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM checkpoints")
            count_before = cursor.fetchone()[0]

        await state_manager.shutdown()

        # Count checkpoints after shutdown
        with sqlite3.connect(state_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM checkpoints")
            count_after = cursor.fetchone()[0]

        assert count_after == count_before + 1

        # Check caches are cleared
        assert len(state_manager._agent_cache) == 0
        assert len(state_manager._task_cache) == 0

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, state_manager):
        """Test concurrent operations on state manager."""
        # Create multiple agents concurrently
        tasks = [
            state_manager.register_agent(f"agent-{i}", [f"skill-{i}"])
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks)

        # All registrations should succeed
        assert all(results)

        # All agents should be in cache
        assert len(state_manager._agent_cache) == 10

        # Update all agents concurrently
        update_tasks = [
            state_manager.update_agent_state(
                f"agent-{i}", context_usage=i * 0.1)
            for i in range(10)
        ]

        update_results = await asyncio.gather(*update_tasks)
        assert all(update_results)

    @pytest.mark.asyncio
    async def test_database_transaction_rollback(self, state_manager):
        """Test database transaction rollback on error."""
        await state_manager.register_agent("agent-1")

        # Try to update with invalid data type (should cause error)
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.execute.side_effect = sqlite3.Error("Database error")
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value.__enter__.return_value = mock_conn

            result = await state_manager.update_agent_state("agent-1", status="working")

            # Should return False on error
            assert result is False

    @pytest.mark.asyncio
    async def test_ml_component_integration(self, state_manager):
        """Test integration with ML components."""
        # Test confidence tracker integration
        assert state_manager.confidence_tracker is not None

        # Test context monitor integration
        assert state_manager.context_monitor is not None

        # Test quality gate integration
        assert state_manager.quality_gate is not None

        # Test that quality gate uses confidence tracker
        assert state_manager.quality_gate.confidence_tracker is state_manager.confidence_tracker

        # Test checkpoint decision with context monitor
        await state_manager.register_agent("agent-1")
        await state_manager.update_agent_state("agent-1", context_usage=0.9)

        should_create, reason = await state_manager.should_create_checkpoint("agent-1")

        # Should recommend checkpoint due to high context usage
        assert should_create is True
        assert "context usage" in reason.lower()

    def test_thread_safety(self, state_manager):
        """Test thread safety of state manager operations."""
        import threading

        results = []
        errors = []

        def register_agent(agent_id):
            try:
                # Use asyncio.run to create new event loop for each thread
                result = asyncio.run(state_manager.register_agent(agent_id))
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=register_agent,
                                      args=(f"thread-agent-{i}",))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        assert all(results)
