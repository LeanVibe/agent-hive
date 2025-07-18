"""
StateManager - Centralized state management system for LeanVibe Agent Hive.

Provides comprehensive state management with SQLite backend, including agent states,
task states, checkpoints, and ML integration.
"""

import asyncio
import json
import logging
import sqlite3
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class AgentState:
    """Represents the current state of an agent."""
    agent_id: str
    status: str
    current_task_id: Optional[str] = None
    context_usage: float = 0.0
    last_activity: datetime = field(default_factory=datetime.now)
    capabilities: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class TaskState:
    """Represents the current state of a task."""
    task_id: str
    status: str
    agent_id: Optional[str] = None
    priority: int = 5
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemState:
    """Represents the overall system state."""
    total_agents: int = 0
    active_agents: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    average_context_usage: float = 0.0
    quality_score: float = 0.0
    last_checkpoint: Optional[datetime] = None


class StateManager:
    """Centralized state management system with SQLite backend."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize StateManager with database connection."""
        self.db_path = db_path or "state_manager.db"
        self._agent_cache: Dict[str, AgentState] = {}
        self._task_cache: Dict[str, TaskState] = {}
        self._system_state = SystemState()
        self._initialize_database()

    def _initialize_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create agents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    current_task_id TEXT,
                    context_usage REAL DEFAULT 0.0,
                    last_activity TEXT NOT NULL,
                    capabilities TEXT NOT NULL DEFAULT '[]',
                    performance_metrics TEXT NOT NULL DEFAULT '{}'
                )
            """)

            # Create tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    agent_id TEXT,
                    priority INTEGER DEFAULT 5,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    metadata TEXT NOT NULL DEFAULT '{}'
                )
            """)

            # Create system_snapshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_agents INTEGER DEFAULT 0,
                    active_agents INTEGER DEFAULT 0,
                    total_tasks INTEGER DEFAULT 0,
                    completed_tasks INTEGER DEFAULT 0,
                    failed_tasks INTEGER DEFAULT 0,
                    average_context_usage REAL DEFAULT 0.0,
                    quality_score REAL DEFAULT 0.0
                )
            """)

            # Create checkpoints table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checkpoint_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            """)

            conn.commit()

    async def register_agent(self, agent_id: str,
                             capabilities: Optional[List[str]] = None) -> bool:
        """Register a new agent or update existing agent."""
        try:
            agent_state = AgentState(
                agent_id=agent_id,
                status="idle",
                capabilities=capabilities or []
            )

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO agents
                    (agent_id, status, current_task_id, context_usage, last_activity, capabilities, performance_metrics)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    agent_state.agent_id,
                    agent_state.status,
                    agent_state.current_task_id,
                    agent_state.context_usage,
                    agent_state.last_activity.isoformat(),
                    json.dumps(agent_state.capabilities),
                    json.dumps(agent_state.performance_metrics)
                ))
                conn.commit()

            # Update cache
            self._agent_cache[agent_id] = agent_state
            return True

        except Exception as e:
            logger.error(f"Error registering agent {agent_id}: {e}")
            return False

    async def update_agent_state(
            self,
            agent_id: str,
            status: Optional[str] = None,
            context_usage: Optional[float] = None,
            current_task_id: Optional[str] = None) -> bool:
        """Update agent state with various parameters."""
        try:
            if agent_id in self._agent_cache:
                agent_state = self._agent_cache[agent_id]
                if status is not None:
                    agent_state.status = status
                if context_usage is not None:
                    agent_state.context_usage = context_usage
                if current_task_id is not None:
                    agent_state.current_task_id = current_task_id
                agent_state.last_activity = datetime.now()

                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        UPDATE agents
                        SET status = ?, current_task_id = ?, context_usage = ?, last_activity = ?
                        WHERE agent_id = ?
                    """,
                        (agent_state.status,
                         agent_state.current_task_id,
                         agent_state.context_usage,
                         agent_state.last_activity.isoformat(),
                         agent_id))
                    conn.commit()

                return True
            return False

        except Exception as e:
            logger.error(f"Error updating agent status for {agent_id}: {e}")
            return False

    async def add_task(self, task_id: str, priority: int = 5,
                       metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Create a new task."""
        try:
            task_state = TaskState(
                task_id=task_id,
                status="pending",
                priority=priority,
                metadata=metadata or {}
            )

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO tasks
                    (task_id, status, agent_id, priority, created_at, started_at, completed_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (task_state.task_id,
                     task_state.status,
                     task_state.agent_id,
                     task_state.priority,
                     task_state.created_at.isoformat(),
                     task_state.started_at.isoformat() if task_state.started_at else None,
                     task_state.completed_at.isoformat() if task_state.completed_at else None,
                     json.dumps(
                         task_state.metadata)))
                conn.commit()

            # Update cache
            self._task_cache[task_id] = task_state
            return True

        except Exception as e:
            logger.error(f"Error creating task {task_id}: {e}")
            return False

    async def update_task_state(
            self,
            task_id: str,
            status: Optional[str] = None,
            agent_id: Optional[str] = None,
            priority: Optional[int] = None) -> bool:
        """Update task state."""
        try:
            if task_id in self._task_cache:
                task_state = self._task_cache[task_id]
                if status is not None:
                    task_state.status = status
                    if status == "in_progress" and task_state.started_at is None:
                        task_state.started_at = datetime.now()
                    elif status in ["completed", "failed"] and task_state.completed_at is None:
                        task_state.completed_at = datetime.now()

                if agent_id is not None:
                    task_state.agent_id = agent_id
                if priority is not None:
                    task_state.priority = priority

                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        UPDATE tasks
                        SET status = ?, agent_id = ?, priority = ?, started_at = ?, completed_at = ?
                        WHERE task_id = ?
                    """,
                        (task_state.status,
                         task_state.agent_id,
                         task_state.priority,
                         task_state.started_at.isoformat() if task_state.started_at else None,
                         task_state.completed_at.isoformat() if task_state.completed_at else None,
                         task_id))
                    conn.commit()

                return True
            return False

        except Exception as e:
            logger.error(f"Error updating task state for {task_id}: {e}")
            return False

    async def get_next_priority_task(self) -> Optional[TaskState]:
        """Get the next highest priority pending task."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT task_id, status, agent_id, priority, created_at, started_at, completed_at, metadata
                    FROM tasks
                    WHERE status = 'pending'
                    ORDER BY priority ASC, created_at ASC
                    LIMIT 1
                """)
                row = cursor.fetchone()

                if row:
                    return TaskState(
                        task_id=row[0],
                        status=row[1],
                        agent_id=row[2],
                        priority=row[3],
                        created_at=datetime.fromisoformat(row[4]),
                        started_at=datetime.fromisoformat(
                            row[5]) if row[5] else None,
                        completed_at=datetime.fromisoformat(
                            row[6]) if row[6] else None,
                        metadata=json.loads(row[7])
                    )
                return None

        except Exception as e:
            logger.error(f"Error getting next priority task: {e}")
            return None

    async def assign_task(self, task_id: str, agent_id: str) -> bool:
        """Assign a task to an agent."""
        try:
            if task_id in self._task_cache:
                task_state = self._task_cache[task_id]
                task_state.agent_id = agent_id
                task_state.status = "assigned"
                task_state.started_at = datetime.now()

                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE tasks
                        SET agent_id = ?, status = ?, started_at = ?
                        WHERE task_id = ?
                    """, (agent_id, "assigned", task_state.started_at.isoformat(), task_id))
                    conn.commit()

                # Update agent status
                await self.update_agent_status(agent_id, "working", task_id)
                return True
            return False

        except Exception as e:
            logger.error(
                f"Error assigning task {task_id} to agent {agent_id}: {e}")
            return False

    async def complete_task(self, task_id: str, success: bool = True) -> bool:
        """Mark a task as completed."""
        try:
            if task_id in self._task_cache:
                task_state = self._task_cache[task_id]
                task_state.status = "completed" if success else "failed"
                task_state.completed_at = datetime.now()

                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE tasks
                        SET status = ?, completed_at = ?
                        WHERE task_id = ?
                    """, (task_state.status, task_state.completed_at.isoformat(), task_id))
                    conn.commit()

                # Update agent status back to idle
                if task_state.agent_id:
                    await self.update_agent_status(task_state.agent_id, "idle")

                return True
            return False

        except Exception as e:
            logger.error(f"Error completing task {task_id}: {e}")
            return False

    async def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """Get current state of an agent."""
        # First check cache
        if agent_id in self._agent_cache:
            return self._agent_cache[agent_id]

        # If not in cache, try to load from database
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT agent_id, status, current_task_id, context_usage, last_activity, capabilities, performance_metrics
                    FROM agents WHERE agent_id = ?
                """, (agent_id,))
                row = cursor.fetchone()

                if row:
                    agent_state = AgentState(
                        agent_id=row[0],
                        status=row[1],
                        current_task_id=row[2],
                        context_usage=row[3],
                        last_activity=datetime.fromisoformat(row[4]),
                        capabilities=json.loads(row[5]),
                        performance_metrics=json.loads(row[6])
                    )
                    # Cache for future access
                    self._agent_cache[agent_id] = agent_state
                    return agent_state

            return None

        except Exception as e:
            logger.error(f"Error getting agent state for {agent_id}: {e}")
            return None

    async def get_task_state(self, task_id: str) -> Optional[TaskState]:
        """Get current state of a task."""
        return self._task_cache.get(task_id)

    async def get_system_state(self) -> SystemState:
        """Get current system state."""
        # Update system state from database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Count agents
            cursor.execute("SELECT COUNT(*) FROM agents")
            self._system_state.total_agents = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM agents WHERE status != 'idle'")
            self._system_state.active_agents = cursor.fetchone()[0]

            # Count tasks
            cursor.execute("SELECT COUNT(*) FROM tasks")
            self._system_state.total_tasks = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
            self._system_state.completed_tasks = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM tasks WHERE status = 'failed'")
            self._system_state.failed_tasks = cursor.fetchone()[0]

            # Calculate average context usage
            cursor.execute("SELECT AVG(context_usage) FROM agents")
            result = cursor.fetchone()[0]
            self._system_state.average_context_usage = result if result else 0.0

        return self._system_state

    async def create_checkpoint(self,
                                checkpoint_name: str,
                                data: Optional[Dict[str,
                                                    Any]] = None,
                                agent_id: Optional[str] = None) -> Optional[str]:
        """Create a system checkpoint."""
        try:
            checkpoint_data = data or {}
            if agent_id:
                checkpoint_data["agent_id"] = agent_id

            timestamp = datetime.now()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO checkpoints (checkpoint_name, timestamp, data)
                    VALUES (?, ?, ?)
                """, (checkpoint_name, timestamp.isoformat(), json.dumps(checkpoint_data)))
                checkpoint_id = cursor.lastrowid
                conn.commit()

            self._system_state.last_checkpoint = timestamp
            return f"checkpoint_{checkpoint_id}"

        except Exception as e:
            logger.error(f"Error creating checkpoint {checkpoint_name}: {e}")
            return None

    async def should_create_checkpoint(
            self, agent_id: str) -> Tuple[bool, str]:
        """Determine if a checkpoint should be created based on context usage."""
        try:
            if agent_id in self._agent_cache:
                agent_state = self._agent_cache[agent_id]
                if agent_state.context_usage >= 0.8:
                    return True, f"High context usage: {
                        agent_state.context_usage:.1%}"
                else:
                    return False, f"No checkpoint needed - context usage: {
                        agent_state.context_usage:.1%}"
            return False, "Agent not found"

        except Exception as e:
            logger.error(f"Error checking checkpoint need for {agent_id}: {e}")
            return False, f"Error: {e}"

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Count various metrics
                cursor.execute("SELECT COUNT(*) FROM agents")
                total_agents = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(*) FROM agents WHERE status != 'idle'")
                active_agents = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM tasks")
                total_tasks = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
                completed_tasks = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(*) FROM tasks WHERE status = 'failed'")
                failed_tasks = cursor.fetchone()[0]

                cursor.execute("SELECT AVG(context_usage) FROM agents")
                avg_context = cursor.fetchone()[0] or 0.0

                return {
                    "total_agents": total_agents,
                    "active_agents": active_agents,
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "failed_tasks": failed_tasks,
                    "average_context_usage": avg_context,
                    "success_rate": completed_tasks / max(total_tasks, 1) * 100
                }

        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}

    async def shutdown(self) -> bool:
        """Shutdown state manager with checkpoint creation."""
        try:
            # Create final checkpoint
            await self.create_checkpoint("shutdown", {
                "timestamp": datetime.now().isoformat(),
                "system_state": asdict(await self.get_system_state()),
                "agent_count": len(self._agent_cache),
                "task_count": len(self._task_cache)
            })
            return True

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            return False

    async def get_checkpoint(
            self, checkpoint_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a checkpoint."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT data FROM checkpoints
                    WHERE checkpoint_name = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (checkpoint_name,))
                row = cursor.fetchone()

                if row:
                    return json.loads(row[0])
            return None

        except Exception as e:
            logger.error(f"Error retrieving checkpoint {checkpoint_name}: {e}")
            return None

    async def cleanup_old_data(self, days_to_keep: int = 30) -> bool:
        """Clean up old data from the database."""
        try:
            cutoff_date = (datetime.now() -
                           timedelta(days=days_to_keep)).isoformat()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Clean old completed tasks
                cursor.execute("""
                    DELETE FROM tasks
                    WHERE status IN ('completed', 'failed')
                    AND completed_at < ?
                """, (cutoff_date,))

                # Clean old system snapshots
                cursor.execute("""
                    DELETE FROM system_snapshots
                    WHERE timestamp < ?
                """, (cutoff_date,))

                # Clean old checkpoints (keep latest 10 for each name)
                cursor.execute("""
                    DELETE FROM checkpoints
                    WHERE id NOT IN (
                        SELECT id FROM checkpoints c1
                        WHERE (
                            SELECT COUNT(*)
                            FROM checkpoints c2
                            WHERE c2.checkpoint_name = c1.checkpoint_name
                            AND c2.timestamp >= c1.timestamp
                        ) <= 10
                    )
                """)

                conn.commit()

            return True

        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            return False


def get_config():
    """Mock function for configuration - needed by tests."""
    class MockConfig:
        def get(self, key, default=None):
            return default
    return MockConfig()
