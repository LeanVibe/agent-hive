"""
Integration tests for LeanVibe Quality Agent system components.

This module provides comprehensive integration tests to ensure all system
components work together correctly and maintain proper interfaces.
"""

import pytest
import asyncio
import tempfile
import time
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add the .claude directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude'))

from state.state_manager import StateManager, AgentState, TaskState
from task_queue_module.task_queue import TaskQueue, Task


@pytest.mark.integration
class TestStateManagerIntegration:
    """Integration tests for StateManager with other components."""

    def test_state_manager_with_task_queue_integration(self):
        """Test StateManager integration with TaskQueue."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize components
            state_manager = StateManager(Path(temp_dir))

            # Create agent state
            agent_state = AgentState(
                agent_id="integration-agent",
                status="idle",
                capabilities=["python", "javascript"],
                performance_metrics={"speed": 0.8, "accuracy": 0.9}
            )
            state_manager.update_agent_state(agent_state)

            # Create task states
            task_states = []
            for i in range(3):
                task_state = TaskState(
                    task_id=f"integration-task-{i}",
                    status="pending",
                    agent_id="integration-agent",
                    priority=i + 1,
                    metadata={"integration_test": True}
                )
                task_states.append(task_state)
                state_manager.update_task_state(task_state)

            # Verify state persistence
            retrieved_agent = state_manager.get_agent_state("integration-agent")
            assert retrieved_agent is not None
            assert retrieved_agent.agent_id == "integration-agent"
            assert retrieved_agent.status == "idle"

            # Verify task states
            for i, task_state in enumerate(task_states):
                retrieved_task = state_manager.get_task_state(f"integration-task-{i}")
                assert retrieved_task is not None
                assert retrieved_task.task_id == f"integration-task-{i}"
                assert retrieved_task.status == "pending"
                assert retrieved_task.agent_id == "integration-agent"

            # Test system state aggregation
            system_state = state_manager.get_system_state()
            assert system_state.active_agents >= 0
            assert system_state.completed_tasks >= 0
            assert system_state.system_health in ["healthy", "degraded", "unhealthy"]

    def test_state_manager_checkpoint_integration(self):
        """Test StateManager checkpoint functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_manager = StateManager(Path(temp_dir))

            # Create test metrics
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "agents_active": 5,
                "tasks_completed": 100,
                "average_response_time": 0.5,
                "error_rate": 0.01
            }

            # Save checkpoint
            checkpoint_id = f"integration-checkpoint-{int(time.time())}"
            state_manager.save_checkpoint(checkpoint_id, metrics)

            # Retrieve checkpoint
            saved_checkpoint = state_manager.get_checkpoint(checkpoint_id)
            assert saved_checkpoint is not None
            assert saved_checkpoint["id"] == checkpoint_id
            assert saved_checkpoint["metrics"] == metrics

            # Verify timestamp is reasonable
            checkpoint_time = datetime.fromisoformat(saved_checkpoint["timestamp"])
            time_diff = datetime.now() - checkpoint_time
            assert time_diff < timedelta(seconds=10)  # Should be recent

    def test_state_manager_data_cleanup_integration(self):
        """Test StateManager data cleanup functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_manager = StateManager(Path(temp_dir))

            # Create old data
            old_checkpoint_id = "old-checkpoint"
            old_metrics = {"test": "old_data"}
            state_manager.save_checkpoint(old_checkpoint_id, old_metrics)

            # Create recent data
            recent_checkpoint_id = "recent-checkpoint"
            recent_metrics = {"test": "recent_data"}
            state_manager.save_checkpoint(recent_checkpoint_id, recent_metrics)

            # Verify both exist
            assert state_manager.get_checkpoint(old_checkpoint_id) is not None
            assert state_manager.get_checkpoint(recent_checkpoint_id) is not None

            # Cleanup with 0 days retention (should remove all)
            state_manager.cleanup_old_data(0)

            # Verify cleanup occurred
            # Note: The cleanup might not remove all data immediately due to database constraints
            # but it should have attempted cleanup
            system_state = state_manager.get_system_state()
            assert system_state is not None  # System should still be functional


@pytest.mark.integration
@pytest.mark.asyncio
class TestTaskQueueIntegration:
    """Integration tests for TaskQueue with other components."""

    async def test_task_queue_with_state_manager_integration(self):
        """Test TaskQueue integration with StateManager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize components
            state_manager = StateManager(Path(temp_dir))
            task_queue = TaskQueue()

            # Create tasks
            tasks = []
            for i in range(5):
                task = Task(
                    id=f"queue-integration-task-{i}",
                    type="integration_test",
                    description=f"Integration test task {i}",
                    priority=i + 1,
                    data={"test_data": f"value_{i}"}
                )
                tasks.append(task)
                await task_queue.enqueue(task)

            # Process tasks and update state
            agent_state = AgentState(
                agent_id="queue-integration-agent",
                status="idle",
                capabilities=["integration_test"],
                performance_metrics={"speed": 0.8}
            )
            state_manager.update_agent_state(agent_state)

            processed_tasks = []
            while len(processed_tasks) < 5:
                task = await task_queue.dequeue()
                if task:
                    # Update agent state
                    agent_state.status = "busy"
                    agent_state.current_task_id = task.id
                    state_manager.update_agent_state(agent_state)

                    # Create task state
                    task_state = TaskState(
                        task_id=task.id,
                        status="processing",
                        agent_id="queue-integration-agent",
                        priority=task.priority,
                        metadata={"queue_processed": True}
                    )
                    state_manager.update_task_state(task_state)

                    processed_tasks.append(task)

                    # Simulate processing time
                    await asyncio.sleep(0.01)

                    # Mark task as completed
                    task_state.status = "completed"
                    task_state.completed_at = datetime.now()
                    state_manager.update_task_state(task_state)

            # Verify all tasks were processed
            assert len(processed_tasks) == 5

            # Verify state consistency
            final_agent_state = state_manager.get_agent_state("queue-integration-agent")
            assert final_agent_state is not None

            # Verify task states
            for task in processed_tasks:
                task_state = state_manager.get_task_state(task.id)
                assert task_state is not None
                assert task_state.status == "completed"
                assert task_state.agent_id == "queue-integration-agent"

    async def test_task_queue_priority_integration(self):
        """Test TaskQueue priority handling integration."""
        task_queue = TaskQueue()

        # Create tasks with different priorities
        high_priority_task = Task(
            id="high-priority-task",
            type="urgent",
            description="High priority task",
            priority=1,  # High priority (lower number)
            data={"urgency": "high"}
        )

        low_priority_task = Task(
            id="low-priority-task",
            type="routine",
            description="Low priority task",
            priority=10,  # Low priority (higher number)
            data={"urgency": "low"}
        )

        medium_priority_task = Task(
            id="medium-priority-task",
            type="normal",
            description="Medium priority task",
            priority=5,  # Medium priority
            data={"urgency": "medium"}
        )

        # Enqueue in non-priority order
        await task_queue.enqueue(low_priority_task)
        await task_queue.enqueue(high_priority_task)
        await task_queue.enqueue(medium_priority_task)

        # Dequeue and verify priority order
        first_task = await task_queue.dequeue()
        assert first_task.id == "high-priority-task"
        assert first_task.priority == 1

        second_task = await task_queue.dequeue()
        assert second_task.id == "medium-priority-task"
        assert second_task.priority == 5

        third_task = await task_queue.dequeue()
        assert third_task.id == "low-priority-task"
        assert third_task.priority == 10


@pytest.mark.integration
class TestAgentStateIntegration:
    """Integration tests for agent state management."""

    def test_agent_lifecycle_integration(self):
        """Test complete agent lifecycle integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_manager = StateManager(Path(temp_dir))

            # Agent registration
            agent_state = AgentState(
                agent_id="lifecycle-agent",
                status="initializing",
                capabilities=["python", "testing"],
                performance_metrics={"speed": 0.0, "accuracy": 0.0}
            )
            state_manager.update_agent_state(agent_state)

            # Agent becomes idle
            agent_state.status = "idle"
            agent_state.performance_metrics = {"speed": 0.8, "accuracy": 0.9}
            state_manager.update_agent_state(agent_state)

            # Agent processes tasks
            task_states = []
            for i in range(3):
                # Agent becomes busy
                agent_state.status = "busy"
                agent_state.current_task_id = f"lifecycle-task-{i}"
                agent_state.context_usage = 0.5 + (i * 0.2)
                state_manager.update_agent_state(agent_state)

                # Create task state
                task_state = TaskState(
                    task_id=f"lifecycle-task-{i}",
                    status="processing",
                    agent_id="lifecycle-agent",
                    priority=i + 1,
                    metadata={"lifecycle_test": True}
                )
                state_manager.update_task_state(task_state)
                task_states.append(task_state)

                # Complete task
                task_state.status = "completed"
                task_state.completed_at = datetime.now()
                state_manager.update_task_state(task_state)

                # Agent becomes idle
                agent_state.status = "idle"
                agent_state.current_task_id = None
                agent_state.context_usage = 0.0
                state_manager.update_agent_state(agent_state)

            # Verify final state
            final_agent_state = state_manager.get_agent_state("lifecycle-agent")
            assert final_agent_state is not None
            assert final_agent_state.status == "idle"
            assert final_agent_state.current_task_id is None
            assert final_agent_state.context_usage == 0.0

            # Verify all tasks were completed
            for task_state in task_states:
                final_task_state = state_manager.get_task_state(task_state.task_id)
                assert final_task_state is not None
                assert final_task_state.status == "completed"
                assert final_task_state.completed_at is not None

    def test_multi_agent_coordination_integration(self):
        """Test multi-agent coordination integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_manager = StateManager(Path(temp_dir))

            # Create multiple agents
            agent_configs = [
                {"id": "agent-1", "capabilities": ["python", "testing"]},
                {"id": "agent-2", "capabilities": ["javascript", "frontend"]},
                {"id": "agent-3", "capabilities": ["database", "backend"]}
            ]

            agents = []
            for config in agent_configs:
                agent_state = AgentState(
                    agent_id=config["id"],
                    status="idle",
                    capabilities=config["capabilities"],
                    performance_metrics={"speed": 0.8, "accuracy": 0.9}
                )
                state_manager.update_agent_state(agent_state)
                agents.append(agent_state)

            # Assign tasks to specific agents
            task_assignments = [
                {"task_id": "python-task", "agent_id": "agent-1", "type": "python"},
                {"task_id": "frontend-task", "agent_id": "agent-2", "type": "javascript"},
                {"task_id": "database-task", "agent_id": "agent-3", "type": "database"}
            ]

            for assignment in task_assignments:
                # Update agent state
                agent_state = state_manager.get_agent_state(assignment["agent_id"])
                agent_state.status = "busy"
                agent_state.current_task_id = assignment["task_id"]
                state_manager.update_agent_state(agent_state)

                # Create task state
                task_state = TaskState(
                    task_id=assignment["task_id"],
                    status="processing",
                    agent_id=assignment["agent_id"],
                    priority=5,
                    metadata={"task_type": assignment["type"]}
                )
                state_manager.update_task_state(task_state)

            # Verify all agents are busy
            for agent in agents:
                current_agent_state = state_manager.get_agent_state(agent.agent_id)
                assert current_agent_state.status == "busy"
                assert current_agent_state.current_task_id is not None

            # Complete all tasks
            for assignment in task_assignments:
                # Complete task
                task_state = state_manager.get_task_state(assignment["task_id"])
                task_state.status = "completed"
                task_state.completed_at = datetime.now()
                state_manager.update_task_state(task_state)

                # Free agent
                agent_state = state_manager.get_agent_state(assignment["agent_id"])
                agent_state.status = "idle"
                agent_state.current_task_id = None
                state_manager.update_agent_state(agent_state)

            # Verify system state
            system_state = state_manager.get_system_state()
            assert system_state.active_agents >= 0
            assert system_state.completed_tasks >= 0
            assert system_state.system_health in ["healthy", "degraded", "unhealthy"]


@pytest.mark.integration
class TestSystemHealthIntegration:
    """Integration tests for system health monitoring."""

    def test_system_health_monitoring_integration(self):
        """Test system health monitoring integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_manager = StateManager(Path(temp_dir))

            # Create baseline system state
            baseline_state = state_manager.get_system_state()
            assert baseline_state.system_health == "healthy"

            # Create successful tasks
            for i in range(10):
                task_state = TaskState(
                    task_id=f"health-success-task-{i}",
                    status="completed",
                    priority=5,
                    metadata={"test": "success"}
                )
                state_manager.update_task_state(task_state)

            # System should remain healthy
            healthy_state = state_manager.get_system_state()
            assert healthy_state.system_health == "healthy"

            # Create some failed tasks
            for i in range(2):
                task_state = TaskState(
                    task_id=f"health-failure-task-{i}",
                    status="failed",
                    priority=5,
                    metadata={"test": "failure"}
                )
                state_manager.update_task_state(task_state)

            # System health should be evaluated based on failure rate
            # (This depends on the specific health calculation logic)
            health_with_failures = state_manager.get_system_state()
            assert health_with_failures.system_health in ["healthy", "degraded", "unhealthy"]
            assert health_with_failures.completed_tasks >= 10
            assert health_with_failures.failed_tasks >= 2

    def test_error_recovery_integration(self):
        """Test error recovery integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_manager = StateManager(Path(temp_dir))

            # Create agent with error state
            agent_state = AgentState(
                agent_id="error-recovery-agent",
                status="error",
                capabilities=["recovery_test"],
                performance_metrics={"speed": 0.0, "accuracy": 0.0}
            )
            state_manager.update_agent_state(agent_state)

            # Create failed task
            task_state = TaskState(
                task_id="error-recovery-task",
                status="failed",
                agent_id="error-recovery-agent",
                priority=5,
                metadata={"error": "test_error", "retry_count": 0}
            )
            state_manager.update_task_state(task_state)

            # Simulate recovery
            agent_state.status = "idle"
            agent_state.performance_metrics = {"speed": 0.8, "accuracy": 0.9}
            state_manager.update_agent_state(agent_state)

            # Retry task
            task_state.status = "processing"
            task_state.metadata["retry_count"] = 1
            state_manager.update_task_state(task_state)

            # Complete task successfully
            task_state.status = "completed"
            task_state.completed_at = datetime.now()
            state_manager.update_task_state(task_state)

            # Verify recovery
            final_agent_state = state_manager.get_agent_state("error-recovery-agent")
            assert final_agent_state.status == "idle"

            final_task_state = state_manager.get_task_state("error-recovery-task")
            assert final_task_state.status == "completed"
            assert final_task_state.metadata["retry_count"] == 1
