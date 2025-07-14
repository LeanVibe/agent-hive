"""
Unit tests for TaskQueue component.

Tests the priority-based task queue with dependency management.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

# Import the component under test
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / ".claude"))

from queue.task_queue import TaskQueue, Task, TaskStatus


class TestTaskQueue:
    """Test cases for TaskQueue functionality."""

    @pytest.mark.unit
    async def test_task_queue_initialization(self):
        """Test task queue initializes empty."""
        queue = TaskQueue()
        
        status = await queue.get_queue_status()
        assert status["total_tasks"] == 0
        assert status["pending_tasks"] == 0
        assert status["in_progress_tasks"] == 0
        assert status["completed_tasks"] == 0

    @pytest.mark.unit
    async def test_add_single_task(self, task_queue, sample_task):
        """Test adding a single task to the queue."""
        result = await task_queue.add_task(sample_task)
        assert result is True
        
        status = await task_queue.get_queue_status()
        assert status["total_tasks"] == 1
        assert status["pending_tasks"] == 1

    @pytest.mark.unit
    async def test_add_multiple_tasks(self, task_queue, sample_tasks):
        """Test adding multiple tasks to the queue."""
        for task in sample_tasks:
            result = await task_queue.add_task(task)
            assert result is True
        
        status = await task_queue.get_queue_status()
        assert status["total_tasks"] == len(sample_tasks)
        assert status["pending_tasks"] == len(sample_tasks)

    @pytest.mark.unit
    async def test_get_next_task_priority_order(self, task_queue, sample_tasks):
        """Test tasks are returned in priority order (highest first)."""
        # Add tasks in random order
        for task in sample_tasks:
            await task_queue.add_task(task)
        
        # Get tasks should return in priority order (highest first)
        retrieved_tasks = []
        capabilities = ["code_generation"]
        
        while True:
            task = await task_queue.get_next_task(capabilities)
            if task is None:
                break
            retrieved_tasks.append(task)
        
        # Should be sorted by priority (descending)
        priorities = [task.priority for task in retrieved_tasks]
        assert priorities == sorted(priorities, reverse=True)

    @pytest.mark.unit
    async def test_task_capability_filtering(self, task_queue):
        """Test tasks are filtered by agent capabilities."""
        # Create tasks with different types
        task1 = Task(
            id="task-1",
            type="code_generation",
            description="Generate code",
            priority=5,
            data={},
            created_at=datetime.now()
        )
        
        task2 = Task(
            id="task-2", 
            type="image_processing",
            description="Process image",
            priority=10,
            data={},
            created_at=datetime.now()
        )
        
        await task_queue.add_task(task1)
        await task_queue.add_task(task2)
        
        # Agent with only code generation capability
        code_capabilities = ["code_generation"]
        next_task = await task_queue.get_next_task(code_capabilities)
        assert next_task.id == "task-1"
        
        # Agent with only image processing capability
        image_capabilities = ["image_processing"] 
        next_task = await task_queue.get_next_task(image_capabilities)
        assert next_task.id == "task-2"

    @pytest.mark.unit
    async def test_mark_task_in_progress(self, task_queue, sample_task):
        """Test marking a task as in progress."""
        await task_queue.add_task(sample_task)
        
        # Get the task
        task = await task_queue.get_next_task(["code_generation"])
        assert task is not None
        
        # Mark as in progress
        result = await task_queue.mark_task_in_progress(task.id, "agent-1")
        assert result is True
        
        status = await task_queue.get_queue_status()
        assert status["pending_tasks"] == 0
        assert status["in_progress_tasks"] == 1

    @pytest.mark.unit
    async def test_mark_task_completed(self, task_queue, sample_task):
        """Test marking a task as completed."""
        await task_queue.add_task(sample_task)
        task = await task_queue.get_next_task(["code_generation"])
        await task_queue.mark_task_in_progress(task.id, "agent-1")
        
        # Mark as completed
        result = await task_queue.mark_task_completed(task.id)
        assert result is True
        
        status = await task_queue.get_queue_status()
        assert status["in_progress_tasks"] == 0
        assert status["completed_tasks"] == 1

    @pytest.mark.unit
    async def test_mark_task_failed_with_retry(self, task_queue, sample_task):
        """Test marking a task as failed with retry enabled."""
        await task_queue.add_task(sample_task)
        task = await task_queue.get_next_task(["code_generation"])
        await task_queue.mark_task_in_progress(task.id, "agent-1")
        
        # Mark as failed with retry
        result = await task_queue.mark_task_failed(task.id, can_retry=True)
        assert result is True
        
        status = await task_queue.get_queue_status()
        assert status["in_progress_tasks"] == 0
        assert status["pending_tasks"] == 1  # Should be back in pending

    @pytest.mark.unit
    async def test_mark_task_failed_no_retry(self, task_queue, sample_task):
        """Test marking a task as failed without retry."""
        await task_queue.add_task(sample_task)
        task = await task_queue.get_next_task(["code_generation"])
        await task_queue.mark_task_in_progress(task.id, "agent-1")
        
        # Mark as failed without retry
        result = await task_queue.mark_task_failed(task.id, can_retry=False)
        assert result is True
        
        status = await task_queue.get_queue_status()
        assert status["in_progress_tasks"] == 0
        assert status["failed_tasks"] == 1

    @pytest.mark.unit
    async def test_task_timeout_handling(self, task_queue):
        """Test handling of timed-out tasks."""
        # Create task with short timeout for testing
        task = Task(
            id="timeout-test",
            type="code_generation", 
            description="Test timeout",
            priority=5,
            data={},
            created_at=datetime.now(),
            timeout_seconds=1
        )
        
        await task_queue.add_task(task)
        retrieved_task = await task_queue.get_next_task(["code_generation"])
        await task_queue.mark_task_in_progress(retrieved_task.id, "agent-1")
        
        # Wait for timeout
        await asyncio.sleep(1.5)
        
        # Check for timed out tasks
        timed_out_tasks = await task_queue.get_timed_out_tasks()
        assert len(timed_out_tasks) == 1
        assert timed_out_tasks[0].id == "timeout-test"

    @pytest.mark.unit
    async def test_task_dependency_basic(self, task_queue):
        """Test basic task dependency functionality."""
        # Create dependent tasks
        parent_task = Task(
            id="parent",
            type="code_generation",
            description="Parent task",
            priority=5,
            data={},
            created_at=datetime.now()
        )
        
        child_task = Task(
            id="child",
            type="code_generation", 
            description="Child task",
            priority=10,  # Higher priority but should wait for parent
            data={},
            created_at=datetime.now(),
            dependencies=["parent"]
        )
        
        await task_queue.add_task(parent_task)
        await task_queue.add_task(child_task)
        
        # Should get parent task first despite child having higher priority
        next_task = await task_queue.get_next_task(["code_generation"])
        assert next_task.id == "parent"
        
        # Child should not be available yet
        next_task = await task_queue.get_next_task(["code_generation"])
        assert next_task is None

    @pytest.mark.unit
    async def test_task_dependency_resolution(self, task_queue):
        """Test task dependency resolution when parent completes."""
        # Create dependent tasks
        parent_task = Task(
            id="parent",
            type="code_generation",
            description="Parent task", 
            priority=5,
            data={},
            created_at=datetime.now()
        )
        
        child_task = Task(
            id="child",
            type="code_generation",
            description="Child task",
            priority=10,
            data={},
            created_at=datetime.now(),
            dependencies=["parent"]
        )
        
        await task_queue.add_task(parent_task)
        await task_queue.add_task(child_task)
        
        # Complete parent task
        parent = await task_queue.get_next_task(["code_generation"])
        await task_queue.mark_task_in_progress(parent.id, "agent-1")
        await task_queue.mark_task_completed(parent.id)
        
        # Now child should be available
        child = await task_queue.get_next_task(["code_generation"])
        assert child.id == "child"

    @pytest.mark.unit
    async def test_duplicate_task_prevention(self, task_queue, sample_task):
        """Test prevention of duplicate task IDs."""
        # Add task first time
        result1 = await task_queue.add_task(sample_task)
        assert result1 is True
        
        # Try to add same task again
        result2 = await task_queue.add_task(sample_task)
        assert result2 is False
        
        status = await task_queue.get_queue_status()
        assert status["total_tasks"] == 1

    @pytest.mark.unit
    async def test_queue_size_limit(self):
        """Test queue size limit enforcement."""
        # Create queue with small limit
        queue = TaskQueue(max_size=2)
        
        # Add tasks up to limit
        for i in range(2):
            task = Task(
                id=f"task-{i}",
                type="code_generation",
                description=f"Task {i}",
                priority=5,
                data={},
                created_at=datetime.now()
            )
            result = await queue.add_task(task)
            assert result is True
        
        # Try to add one more (should fail)
        overflow_task = Task(
            id="overflow",
            type="code_generation", 
            description="Overflow task",
            priority=5,
            data={},
            created_at=datetime.now()
        )
        result = await queue.add_task(overflow_task)
        assert result is False

    @pytest.mark.unit
    @pytest.mark.performance
    async def test_queue_performance(self, performance_thresholds):
        """Test queue performance with many tasks."""
        queue = TaskQueue()
        
        # Add many tasks
        num_tasks = 1000
        start_time = asyncio.get_event_loop().time()
        
        for i in range(num_tasks):
            task = Task(
                id=f"perf-task-{i}",
                type="code_generation",
                description=f"Performance task {i}",
                priority=i % 10,
                data={},
                created_at=datetime.now()
            )
            await queue.add_task(task)
        
        add_time = asyncio.get_event_loop().time() - start_time
        
        # Retrieve all tasks
        start_time = asyncio.get_event_loop().time()
        
        retrieved_count = 0
        while True:
            task = await queue.get_next_task(["code_generation"])
            if task is None:
                break
            retrieved_count += 1
        
        retrieve_time = asyncio.get_event_loop().time() - start_time
        
        # Performance assertions
        assert add_time < performance_thresholds["queue_operation_max_time"] * num_tasks
        assert retrieve_time < performance_thresholds["queue_operation_max_time"] * num_tasks
        assert retrieved_count == num_tasks

    @pytest.mark.unit
    async def test_queue_persistence_simulation(self, task_queue, sample_tasks, temp_directory):
        """Test queue state persistence simulation."""
        # Add tasks
        for task in sample_tasks:
            await task_queue.add_task(task)
        
        # Get queue state
        state = await task_queue.get_queue_state()
        
        # Simulate persistence
        import json
        state_file = temp_directory / "queue_state.json"
        with open(state_file, 'w') as f:
            json.dump(state, f, default=str)
        
        # Create new queue and restore state
        new_queue = TaskQueue()
        with open(state_file, 'r') as f:
            restored_state = json.load(f)
        
        await new_queue.restore_state(restored_state)
        
        # Verify restoration
        status = await new_queue.get_queue_status()
        assert status["total_tasks"] == len(sample_tasks)