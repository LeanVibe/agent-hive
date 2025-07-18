#!/usr/bin/env python3
"""
Enhanced State Manager for LeanVibe Agent Hive
Database-backed persistent state management to replace file-based memory system.

Based on Gemini expert analysis recommendations:
- SQLite backend for atomic, transactional state persistence
- Agent lifecycle management with automatic recovery
- Working memory integration with Redis (future enhancement)
- Semantic memory support with vector databases (future enhancement)
"""

import sqlite3
import json
import time
import logging
import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    """Agent status states following Gemini's recommendations"""
    RUNNING = "running"
    SLEEPING = "sleeping"
    RECOVERING = "recovering"
    CRASHED = "crashed"
    TERMINATED = "terminated"

@dataclass
class AgentState:
    """Agent state data structure"""
    agent_id: str
    status: AgentStatus
    current_task_id: Optional[str] = None
    process_id: Optional[int] = None
    last_heartbeat: Optional[str] = None
    working_memory: Optional[Dict[str, Any]] = None
    session_context: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass
class TaskState:
    """Task state tracking"""
    task_id: str
    agent_id: str
    description: str
    status: str
    priority: int
    created_at: str
    updated_at: str
    metadata: Optional[Dict[str, Any]] = None

class EnhancedStateManager:
    """
    Enhanced state manager implementing Gemini's recommendations for
    database-backed agent state persistence and recovery.
    """

    def __init__(self, db_path: str = ".claude/state/agent_hive.db"):
        """Initialize the state manager with SQLite backend"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        logger.info(f"Enhanced State Manager initialized with database: {self.db_path}")

    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Agents table - core agent state
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    current_task_id TEXT,
                    process_id INTEGER,
                    last_heartbeat TEXT,
                    working_memory TEXT,  -- JSON blob
                    session_context TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (current_task_id) REFERENCES tasks (task_id)
                )
            """)

            # Tasks table - task state tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER DEFAULT 5,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT,  -- JSON blob
                    FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
                )
            """)

            # Memory snapshots table - for sleep/wake protocol
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    snapshot_type TEXT NOT NULL,  -- 'sleep', 'checkpoint', 'crash'
                    memory_data TEXT NOT NULL,   -- JSON blob
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
                )
            """)

            # Agent communications log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_communications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_agent TEXT,
                    to_agent TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    message_content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    delivered BOOLEAN DEFAULT FALSE
                )
            """)

            conn.commit()
            logger.info("Database schema initialized successfully")

    def register_agent(self, agent_id: str, process_id: Optional[int] = None) -> bool:
        """Register a new agent or update existing agent state"""
        try:
            now = datetime.now().isoformat()

            with sqlite3.connect(self.db_path) as conn:
                # Check if agent exists
                cursor = conn.execute(
                    "SELECT agent_id FROM agents WHERE agent_id = ?",
                    (agent_id,)
                )

                if cursor.fetchone():
                    # Update existing agent
                    conn.execute("""
                        UPDATE agents
                        SET status = ?, process_id = ?, last_heartbeat = ?, updated_at = ?
                        WHERE agent_id = ?
                    """, (AgentStatus.RUNNING.value, process_id, now, now, agent_id))
                    logger.info(f"Updated existing agent: {agent_id}")
                else:
                    # Create new agent
                    conn.execute("""
                        INSERT INTO agents
                        (agent_id, status, process_id, last_heartbeat, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (agent_id, AgentStatus.RUNNING.value, process_id, now, now, now))
                    logger.info(f"Registered new agent: {agent_id}")

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False

    def update_agent_status(self, agent_id: str, status: AgentStatus,
                           task_id: Optional[str] = None) -> bool:
        """Update agent status atomically"""
        try:
            now = datetime.now().isoformat()

            with sqlite3.connect(self.db_path) as conn:
                if task_id:
                    conn.execute("""
                        UPDATE agents
                        SET status = ?, current_task_id = ?, last_heartbeat = ?, updated_at = ?
                        WHERE agent_id = ?
                    """, (status.value, task_id, now, now, agent_id))
                else:
                    conn.execute("""
                        UPDATE agents
                        SET status = ?, last_heartbeat = ?, updated_at = ?
                        WHERE agent_id = ?
                    """, (status.value, now, now, agent_id))

                conn.commit()
                logger.info(f"Updated agent {agent_id} status to {status.value}")
                return True

        except Exception as e:
            logger.error(f"Failed to update agent status: {e}")
            return False

    def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """Retrieve agent state"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM agents WHERE agent_id = ?
                """, (agent_id,))

                row = cursor.fetchone()
                if row:
                    working_memory = json.loads(row['working_memory']) if row['working_memory'] else None

                    return AgentState(
                        agent_id=row['agent_id'],
                        status=AgentStatus(row['status']),
                        current_task_id=row['current_task_id'],
                        process_id=row['process_id'],
                        last_heartbeat=row['last_heartbeat'],
                        working_memory=working_memory,
                        session_context=row['session_context'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
                return None

        except Exception as e:
            logger.error(f"Failed to get agent state: {e}")
            return None

    def save_memory_snapshot(self, agent_id: str, memory_data: Dict[str, Any],
                           snapshot_type: str = "checkpoint") -> str:
        """Save agent memory snapshot for sleep/wake protocol"""
        try:
            snapshot_id = f"{agent_id}_{snapshot_type}_{int(time.time())}"
            now = datetime.now().isoformat()

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO memory_snapshots
                    (snapshot_id, agent_id, snapshot_type, memory_data, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (snapshot_id, agent_id, snapshot_type, json.dumps(memory_data), now))

                conn.commit()
                logger.info(f"Saved memory snapshot: {snapshot_id}")
                return snapshot_id

        except Exception as e:
            logger.error(f"Failed to save memory snapshot: {e}")
            return ""

    def load_latest_memory_snapshot(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Load latest memory snapshot for agent recovery"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT memory_data FROM memory_snapshots
                    WHERE agent_id = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (agent_id,))

                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return None

        except Exception as e:
            logger.error(f"Failed to load memory snapshot: {e}")
            return None

    def get_crashed_agents(self, timeout_minutes: int = 5) -> List[str]:
        """Get agents that haven't sent heartbeat within timeout"""
        try:
            cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
            cutoff_str = cutoff_time.isoformat()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT agent_id FROM agents
                    WHERE status = ? AND (last_heartbeat < ? OR last_heartbeat IS NULL)
                """, (AgentStatus.RUNNING.value, cutoff_str))

                return [row[0] for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get crashed agents: {e}")
            return []

    def heartbeat(self, agent_id: str, working_memory: Optional[Dict[str, Any]] = None) -> bool:
        """Send agent heartbeat with optional working memory update"""
        try:
            now = datetime.now().isoformat()
            memory_json = json.dumps(working_memory) if working_memory else None

            with sqlite3.connect(self.db_path) as conn:
                if memory_json:
                    conn.execute("""
                        UPDATE agents
                        SET last_heartbeat = ?, working_memory = ?, updated_at = ?
                        WHERE agent_id = ?
                    """, (now, memory_json, now, agent_id))
                else:
                    conn.execute("""
                        UPDATE agents
                        SET last_heartbeat = ?, updated_at = ?
                        WHERE agent_id = ?
                    """, (now, now, agent_id))

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to send heartbeat for {agent_id}: {e}")
            return False

    def sleep_agent(self, agent_id: str, final_memory: Dict[str, Any]) -> bool:
        """Implement sleep protocol with memory consolidation"""
        try:
            # Save final memory snapshot
            snapshot_id = self.save_memory_snapshot(agent_id, final_memory, "sleep")

            if snapshot_id:
                # Update agent status to sleeping
                return self.update_agent_status(agent_id, AgentStatus.SLEEPING)

            return False

        except Exception as e:
            logger.error(f"Failed to sleep agent {agent_id}: {e}")
            return False

    def wake_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Implement wake protocol with memory restoration"""
        try:
            # Load latest memory snapshot
            memory_data = self.load_latest_memory_snapshot(agent_id)

            # Update agent status to running
            if self.update_agent_status(agent_id, AgentStatus.RUNNING):
                logger.info(f"Agent {agent_id} awakened successfully")
                return memory_data

            return None

        except Exception as e:
            logger.error(f"Failed to wake agent {agent_id}: {e}")
            return None

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Count agents by status
                cursor = conn.execute("""
                    SELECT status, COUNT(*) FROM agents GROUP BY status
                """)
                status_counts = dict(cursor.fetchall())

                # Get total agents
                cursor = conn.execute("SELECT COUNT(*) FROM agents")
                total_agents = cursor.fetchone()[0]

                # Get recent activity
                cursor = conn.execute("""
                    SELECT agent_id, status, last_heartbeat
                    FROM agents
                    ORDER BY updated_at DESC
                    LIMIT 10
                """)
                recent_activity = [
                    {"agent_id": row[0], "status": row[1], "last_heartbeat": row[2]}
                    for row in cursor.fetchall()
                ]

                return {
                    "total_agents": total_agents,
                    "status_counts": status_counts,
                    "recent_activity": recent_activity,
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {}

# CLI interface for enhanced state management
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced State Manager CLI")
    parser.add_argument("--action", choices=["status", "register", "heartbeat", "sleep", "wake", "crashed"],
                       required=True, help="Action to perform")
    parser.add_argument("--agent-id", help="Agent ID")
    parser.add_argument("--process-id", type=int, help="Process ID")
    parser.add_argument("--memory-file", help="Memory file path for sleep/wake")

    args = parser.parse_args()

    state_manager = EnhancedStateManager()

    if args.action == "status":
        status = state_manager.get_system_status()
        print(json.dumps(status, indent=2))

    elif args.action == "register" and args.agent_id:
        success = state_manager.register_agent(args.agent_id, args.process_id)
        print(f"Agent registration: {'SUCCESS' if success else 'FAILED'}")

    elif args.action == "heartbeat" and args.agent_id:
        success = state_manager.heartbeat(args.agent_id)
        print(f"Heartbeat: {'SUCCESS' if success else 'FAILED'}")

    elif args.action == "crashed":
        crashed = state_manager.get_crashed_agents()
        print(f"Crashed agents: {crashed}")

    else:
        print("Invalid arguments. Use --help for usage information.")
