# .claude/queue/task_queue.py
"""Task queue system for LeanVibe orchestration."""

import asyncio
import heapq
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import logging

from agents.base_agent import Task

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueuedTask:
    """Task wrapper for queue management."""
    task: Task
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __lt__(self, other):
        """Support for heapq priority queue."""
        return self.task.priority > other.task.priority  # Higher priority first


class TaskQueue:
    """Intelligent task queue with priority management and dependencies."""

    def __init__(self, max_size: Optional[int] = None):
        self._queue: List[QueuedTask] = []
        self._tasks: Dict[str, QueuedTask] = {}
        self._dependencies: Dict[str, Set[str]] = {}
        self._dependents: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()
        self._max_size = max_size

    async def add_task(self, task: Task) -> bool:
        """Add a task to the queue.

        Args:
            task: Task to add

        Returns:
            True if task was added successfully
        """
        async with self._lock:
            if task.id in self._tasks:
                logger.warning(f"Task {task.id} already exists in queue")
                return False

            # Check size limit
            if self._max_size and len(self._tasks) >= self._max_size:
                logger.warning(f"Queue at maximum capacity ({self._max_size})")
                return False

            queued_task = QueuedTask(task=task)
            self._tasks[task.id] = queued_task
            heapq.heappush(self._queue, queued_task)

            # Handle dependencies
            if task.dependencies:
                self._dependencies[task.id] = set(task.dependencies)
                for dep_id in task.dependencies:
                    if dep_id not in self._dependents:
                        self._dependents[dep_id] = set()
                    self._dependents[dep_id].add(task.id)

            logger.info(f"Task {task.id} added to queue with priority {task.priority}")
            return True

    async def get_next_task(self, agent_capabilities: List[str]) -> Optional[Task]:
        """Get the next available task for an agent.

        Args:
            agent_capabilities: List of agent capabilities

        Returns:
            Next available task or None if no suitable task
        """
        async with self._lock:
            # Find the highest priority task that can be executed
            available_tasks = []

            for queued_task in self._queue:
                if (queued_task.status == TaskStatus.PENDING and
                    self._can_execute_task(queued_task, agent_capabilities)):
                    available_tasks.append(queued_task)

            if not available_tasks:
                return None

            # Sort by priority (already handled by heapq, but let's be explicit)
            available_tasks.sort(key=lambda x: x.task.priority, reverse=True)

            # Return the highest priority task
            selected_task = available_tasks[0]
            selected_task.status = TaskStatus.ASSIGNED
            selected_task.started_at = datetime.now()

            logger.info(f"Task {selected_task.task.id} assigned to agent")
            return selected_task.task

    def _can_execute_task(self, queued_task: QueuedTask, agent_capabilities: List[str]) -> bool:
        """Check if a task can be executed by an agent.

        Args:
            queued_task: Queued task to check
            agent_capabilities: Agent capabilities

        Returns:
            True if task can be executed
        """
        # Check if agent has required capabilities
        if queued_task.task.type not in agent_capabilities:
            return False

        # Check if all dependencies are completed
        task_id = queued_task.task.id
        if task_id in self._dependencies:
            for dep_id in self._dependencies[task_id]:
                if dep_id not in self._tasks:
                    return False  # Dependency not in queue
                if self._tasks[dep_id].status != TaskStatus.COMPLETED:
                    return False  # Dependency not completed

        # Check if task hasn't exceeded max attempts
        if queued_task.attempts >= queued_task.max_attempts:
            return False

        # Check deadline
        if (queued_task.task.deadline and
            queued_task.task.deadline < datetime.now()):
            return False

        return True

    async def mark_task_in_progress(self, task_id: str, agent_id: str) -> bool:
        """Mark a task as in progress.

        Args:
            task_id: Task ID
            agent_id: Agent ID

        Returns:
            True if task was marked successfully
        """
        async with self._lock:
            if task_id not in self._tasks:
                return False

            queued_task = self._tasks[task_id]
            queued_task.status = TaskStatus.IN_PROGRESS
            queued_task.assigned_agent = agent_id
            queued_task.attempts += 1

            logger.info(f"Task {task_id} marked as in progress by agent {agent_id}")
            return True

    async def mark_task_completed(self, task_id: str) -> bool:
        """Mark a task as completed.

        Args:
            task_id: Task ID

        Returns:
            True if task was marked successfully
        """
        async with self._lock:
            if task_id not in self._tasks:
                return False

            queued_task = self._tasks[task_id]
            queued_task.status = TaskStatus.COMPLETED
            queued_task.completed_at = datetime.now()

            # Remove from priority queue
            self._queue = [qt for qt in self._queue if qt.task.id != task_id]
            heapq.heapify(self._queue)

            logger.info(f"Task {task_id} marked as completed")
            return True

    async def mark_task_failed(self, task_id: str, can_retry: bool = True) -> bool:
        """Mark a task as failed.

        Args:
            task_id: Task ID
            can_retry: Whether task can be retried

        Returns:
            True if task was marked successfully
        """
        async with self._lock:
            if task_id not in self._tasks:
                return False

            queued_task = self._tasks[task_id]

            if can_retry and queued_task.attempts < queued_task.max_attempts:
                # Reset to pending for retry
                queued_task.status = TaskStatus.PENDING
                queued_task.assigned_agent = None
                logger.info(f"Task {task_id} reset for retry (attempt {queued_task.attempts})")
            else:
                # Mark as permanently failed
                queued_task.status = TaskStatus.FAILED
                queued_task.completed_at = datetime.now()

                # Remove from priority queue
                self._queue = [qt for qt in self._queue if qt.task.id != task_id]
                heapq.heapify(self._queue)

                logger.error(f"Task {task_id} marked as failed after {queued_task.attempts} attempts")

            return True

    async def get_queue_status(self) -> Dict[str, int]:
        """Get queue status summary.

        Returns:
            Dictionary with status counts
        """
        async with self._lock:
            status_counts = {}
            for status in TaskStatus:
                status_counts[status.value] = 0

            for queued_task in self._tasks.values():
                status_counts[queued_task.status.value] += 1

            return status_counts

    async def get_task_info(self, task_id: str) -> Optional[QueuedTask]:
        """Get information about a specific task.

        Args:
            task_id: Task ID

        Returns:
            QueuedTask or None if not found
        """
        async with self._lock:
            return self._tasks.get(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task.

        Args:
            task_id: Task ID

        Returns:
            True if task was cancelled successfully
        """
        async with self._lock:
            if task_id not in self._tasks:
                return False

            queued_task = self._tasks[task_id]
            if queued_task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                return False  # Cannot cancel completed or failed tasks

            queued_task.status = TaskStatus.CANCELLED
            queued_task.completed_at = datetime.now()

            # Remove from priority queue
            self._queue = [qt for qt in self._queue if qt.task.id != task_id]
            heapq.heapify(self._queue)

            logger.info(f"Task {task_id} cancelled")
            return True

    async def clear_completed_tasks(self) -> int:
        """Clear completed and failed tasks from memory.

        Returns:
            Number of tasks cleared
        """
        async with self._lock:
            cleared_count = 0
            tasks_to_remove = []

            for task_id, queued_task in self._tasks.items():
                if queued_task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    tasks_to_remove.append(task_id)

            for task_id in tasks_to_remove:
                del self._tasks[task_id]
                if task_id in self._dependencies:
                    del self._dependencies[task_id]
                if task_id in self._dependents:
                    del self._dependents[task_id]
                cleared_count += 1

            logger.info(f"Cleared {cleared_count} completed tasks")
            return cleared_count

    async def get_timed_out_tasks(self) -> List[Task]:
        """Get tasks that have exceeded their timeout.

        Returns:
            List of timed out tasks
        """
        async with self._lock:
            timed_out = []
            current_time = datetime.now()

            for queued_task in self._tasks.values():
                if (queued_task.status == TaskStatus.IN_PROGRESS and
                    queued_task.task.timeout_seconds and
                    queued_task.started_at and
                    (current_time - queued_task.started_at).total_seconds() > queued_task.task.timeout_seconds):
                    timed_out.append(queued_task.task)

            return timed_out

    async def get_queue_state(self) -> Dict[str, Any]:
        """Get complete queue state for persistence.

        Returns:
            Dictionary with complete queue state
        """
        async with self._lock:
            return {
                "tasks": {
                    task_id: {
                        "task": {
                            "id": qt.task.id,
                            "type": qt.task.type,
                            "description": qt.task.description,
                            "priority": qt.task.priority,
                            "data": qt.task.data,
                            "created_at": qt.task.created_at.isoformat(),
                            "deadline": qt.task.deadline.isoformat() if qt.task.deadline else None,
                            "dependencies": qt.task.dependencies,
                            "timeout_seconds": qt.task.timeout_seconds
                        },
                        "status": qt.status.value,
                        "assigned_agent": qt.assigned_agent,
                        "attempts": qt.attempts,
                        "max_attempts": qt.max_attempts,
                        "created_at": qt.created_at.isoformat(),
                        "started_at": qt.started_at.isoformat() if qt.started_at else None,
                        "completed_at": qt.completed_at.isoformat() if qt.completed_at else None
                    }
                    for task_id, qt in self._tasks.items()
                },
                "dependencies": {k: list(v) for k, v in self._dependencies.items()},
                "dependents": {k: list(v) for k, v in self._dependents.items()}
            }

    async def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore queue state from persistence data.

        Args:
            state: Dictionary with queue state to restore
        """
        async with self._lock:
            from datetime import datetime

            # Clear current state
            self._queue.clear()
            self._tasks.clear()
            self._dependencies.clear()
            self._dependents.clear()

            # Restore tasks
            for task_id, task_data in state.get("tasks", {}).items():
                task_info = task_data["task"]

                # Recreate Task object
                task = Task(
                    id=task_info["id"],
                    type=task_info["type"],
                    description=task_info["description"],
                    priority=task_info["priority"],
                    data=task_info["data"],
                    created_at=datetime.fromisoformat(task_info["created_at"]),
                    deadline=datetime.fromisoformat(task_info["deadline"]) if task_info["deadline"] else None,
                    dependencies=task_info["dependencies"],
                    timeout_seconds=task_info["timeout_seconds"]
                )

                # Recreate QueuedTask
                queued_task = QueuedTask(
                    task=task,
                    status=TaskStatus(task_data["status"]),
                    assigned_agent=task_data["assigned_agent"],
                    attempts=task_data["attempts"],
                    max_attempts=task_data["max_attempts"],
                    created_at=datetime.fromisoformat(task_data["created_at"]),
                    started_at=datetime.fromisoformat(task_data["started_at"]) if task_data["started_at"] else None,
                    completed_at=datetime.fromisoformat(task_data["completed_at"]) if task_data["completed_at"] else None
                )

                self._tasks[task_id] = queued_task
                if queued_task.status == TaskStatus.PENDING:
                    heapq.heappush(self._queue, queued_task)

            # Restore dependencies
            self._dependencies = {k: set(v) for k, v in state.get("dependencies", {}).items()}
            self._dependents = {k: set(v) for k, v in state.get("dependents", {}).items()}

            logger.info(f"Restored queue state with {len(self._tasks)} tasks")
