"""
State Manager for LeanVibe Agent Hive system.

Manages agent states, task states, and system-wide state information.
"""

import json
import sqlite3
import time
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    import git
except ImportError:
    git = None


class AgentState(Enum):
    """Agent state enumeration."""
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class TaskState(Enum):
    """Task state enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SystemState(Enum):
    """System state enumeration."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    SHUTDOWN = "shutdown"


@dataclass
class TaskInfo:
    """Task information."""
    id: str
    agent: str
    status: TaskState
    confidence: float
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AgentInfo:
    """Agent information."""
    name: str
    state: AgentState
    last_heartbeat: datetime
    current_task: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class StateManager:
    """
    Manages system state including agents, tasks, and checkpoints.
    """

    def __init__(self, base_path: Path):
        """
        Initialize state manager.

        Args:
            base_path: Base path for state storage
        """
        try:
            self.base_path = base_path
            self.db_path = base_path / ".claude" / "state.db"
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            self.db = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.db.row_factory = sqlite3.Row

            if git:
                try:
                    self.repo = git.Repo(base_path)
                except (git.InvalidGitRepositoryError, git.NoSuchPathError):
                    self.repo = None
            else:
                self.repo = None

            self._init_db()

        except Exception as e:
            print(f"State init error: {e}")
            raise

    def _init_db(self):
        """Initialize database schema."""
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                id TEXT PRIMARY KEY,
                git_tag TEXT,
                metrics JSON,
                timestamp DATETIME,
                description TEXT
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                agent TEXT,
                status TEXT,
                confidence REAL,
                created_at DATETIME,
                updated_at DATETIME,
                metadata JSON
            );

            CREATE TABLE IF NOT EXISTS agents (
                name TEXT PRIMARY KEY,
                state TEXT,
                last_heartbeat DATETIME,
                current_task TEXT,
                metadata JSON
            );

            CREATE TABLE IF NOT EXISTS performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT,
                task_id TEXT,
                duration REAL,
                success BOOL,
                timestamp DATETIME
            );

            CREATE TABLE IF NOT EXISTS system_state (
                key TEXT PRIMARY KEY,
                value JSON,
                updated_at DATETIME
            );
        """)
        self.db.commit()

    def checkpoint(self, name: str, description: str = ""):
        """
        Create a system checkpoint.

        Args:
            name: Checkpoint name
            description: Optional description
        """
        try:
            git_tag = None
            if self.repo:
                try:
                    tag = self.repo.create_tag(name)
                    git_tag = tag.name
                except Exception as e:
                    print(f"Git tag creation failed: {e}")

            metrics = self._collect_metrics()

            self.db.execute(
                "INSERT OR REPLACE INTO checkpoints VALUES (?, ?, ?, ?, ?)",
                (name, git_tag, json.dumps(metrics), time.time(), description),
            )
            self.db.commit()

        except Exception as e:
            print(f"Checkpoint error: {e}")
            # Auto-rollback to last if critical
            self.rollback("last-good")

    def rollback(self, checkpoint_id: str):
        """
        Rollback to a specific checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier
        """
        try:
            if self.repo:
                self.repo.git.checkout(checkpoint_id)

            # Restore DB state if needed
            cursor = self.db.cursor()
            cursor.execute(
                "SELECT timestamp FROM checkpoints WHERE id = ?",
                (checkpoint_id,)
            )
            result = cursor.fetchone()

            if result:
                checkpoint_time = result[0]
                # Remove tasks created after checkpoint
                self.db.execute(
                    "DELETE FROM tasks WHERE created_at > ?",
                    (checkpoint_time,)
                )
                self.db.commit()

        except Exception as e:
            print(f"Rollback error: {e}")
            raise

    def _collect_metrics(self) -> Dict[str, Any]:
        """Collect system metrics for checkpoint."""
        cursor = self.db.cursor()

        # Average confidence
        cursor.execute("SELECT AVG(confidence) FROM tasks WHERE status = 'completed'")
        avg_confidence = cursor.fetchone()[0] or 0.8

        # Task success rate
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
        completed_tasks = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'failed'")
        failed_tasks = cursor.fetchone()[0] or 0

        total_tasks = completed_tasks + failed_tasks
        success_rate = completed_tasks / total_tasks if total_tasks > 0 else 1.0

        # Active agents
        cursor.execute("SELECT COUNT(*) FROM agents WHERE state IN ('active', 'busy')")
        active_agents = cursor.fetchone()[0] or 0

        return {
            "avg_confidence": avg_confidence,
            "success_rate": success_rate,
            "active_agents": active_agents,
            "total_tasks": total_tasks,
            "timestamp": datetime.now().isoformat()
        }

    def create_task(self, task_id: str, agent: str, confidence: float = 0.8, metadata: Optional[Dict[str, Any]] = None) -> TaskInfo:
        """
        Create a new task.

        Args:
            task_id: Unique task identifier
            agent: Agent name assigned to task
            confidence: Initial confidence level
            metadata: Optional task metadata

        Returns:
            Created task information
        """
        now = datetime.now()
        task = TaskInfo(
            id=task_id,
            agent=agent,
            status=TaskState.PENDING,
            confidence=confidence,
            created_at=now,
            updated_at=now,
            metadata=metadata
        )

        self.db.execute(
            "INSERT OR REPLACE INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?)",
            (task_id, agent, task.status.value, confidence,
             now.isoformat(), now.isoformat(), json.dumps(metadata or {}))
        )
        self.db.commit()

        return task

    def update_task(self, task_id: str, status: Optional[TaskState] = None,
                   confidence: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update task information.

        Args:
            task_id: Task identifier
            status: New task status
            confidence: New confidence level
            metadata: Updated metadata

        Returns:
            True if task was updated, False if not found
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        if not row:
            return False

        updates = []
        params = []

        if status is not None:
            updates.append("status = ?")
            params.append(status.value)

        if confidence is not None:
            updates.append("confidence = ?")
            params.append(confidence)

        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(task_id)

        self.db.execute(
            f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
            params
        )
        self.db.commit()

        return True

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """
        Get task information.

        Args:
            task_id: Task identifier

        Returns:
            Task information or None if not found
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return TaskInfo(
            id=row["id"],
            agent=row["agent"],
            status=TaskState(row["status"]),
            confidence=row["confidence"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else None
        )

    def register_agent(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> AgentInfo:
        """
        Register an agent.

        Args:
            name: Agent name
            metadata: Optional agent metadata

        Returns:
            Agent information
        """
        now = datetime.now()
        agent = AgentInfo(
            name=name,
            state=AgentState.IDLE,
            last_heartbeat=now,
            metadata=metadata
        )

        self.db.execute(
            "INSERT OR REPLACE INTO agents VALUES (?, ?, ?, ?, ?)",
            (name, agent.state.value, now.isoformat(), None, json.dumps(metadata or {}))
        )
        self.db.commit()

        return agent

    def update_agent(self, name: str, state: Optional[AgentState] = None,
                    current_task: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update agent information.

        Args:
            name: Agent name
            state: New agent state
            current_task: Current task ID
            metadata: Updated metadata

        Returns:
            True if agent was updated, False if not found
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM agents WHERE name = ?", (name,))
        row = cursor.fetchone()

        if not row:
            return False

        updates = ["last_heartbeat = ?"]
        params = [datetime.now().isoformat()]

        if state is not None:
            updates.append("state = ?")
            params.append(state.value)

        if current_task is not None:
            updates.append("current_task = ?")
            params.append(current_task)

        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        params.append(name)

        self.db.execute(
            f"UPDATE agents SET {', '.join(updates)} WHERE name = ?",
            params
        )
        self.db.commit()

        return True

    def get_agent(self, name: str) -> Optional[AgentInfo]:
        """
        Get agent information.

        Args:
            name: Agent name

        Returns:
            Agent information or None if not found
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM agents WHERE name = ?", (name,))
        row = cursor.fetchone()

        if not row:
            return None

        return AgentInfo(
            name=row["name"],
            state=AgentState(row["state"]),
            last_heartbeat=datetime.fromisoformat(row["last_heartbeat"]),
            current_task=row["current_task"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else None
        )

    def get_system_state(self, key: str) -> Optional[Any]:
        """
        Get system state value.

        Args:
            key: State key

        Returns:
            State value or None if not found
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT value FROM system_state WHERE key = ?", (key,))
        row = cursor.fetchone()

        if not row:
            return None

        return json.loads(row["value"])

    def set_system_state(self, key: str, value: Any):
        """
        Set system state value.

        Args:
            key: State key
            value: State value
        """
        self.db.execute(
            "INSERT OR REPLACE INTO system_state VALUES (?, ?, ?)",
            (key, json.dumps(value), datetime.now().isoformat())
        )
        self.db.commit()

    def get_active_tasks(self) -> List[TaskInfo]:
        """Get all active tasks."""
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM tasks WHERE status IN ('pending', 'running')")

        tasks = []
        for row in cursor.fetchall():
            tasks.append(TaskInfo(
                id=row["id"],
                agent=row["agent"],
                status=TaskState(row["status"]),
                confidence=row["confidence"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                metadata=json.loads(row["metadata"]) if row["metadata"] else None
            ))

        return tasks

    def get_active_agents(self) -> List[AgentInfo]:
        """Get all active agents."""
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM agents WHERE state IN ('active', 'busy')")

        agents = []
        for row in cursor.fetchall():
            agents.append(AgentInfo(
                name=row["name"],
                state=AgentState(row["state"]),
                last_heartbeat=datetime.fromisoformat(row["last_heartbeat"]),
                current_task=row["current_task"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else None
            ))

        return agents

    def close(self):
        """Close database connection."""
        if hasattr(self, 'db'):
            self.db.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
