"""
Consolidated Database Manager for LeanVibe Agent Hive

Implements the new database architecture with support for:
- Context and memory management
- Task and project tracking
- Performance metrics
- Agent coordination
- Migration framework
"""

import json
import logging
import sqlite3
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import hashlib


logger = logging.getLogger(__name__)


@dataclass
class ContextSession:
    """Context session data structure."""
    session_id: str
    agent_id: str
    context_data: Dict[str, Any]
    usage_percent: float
    token_count: int
    max_tokens: int = 200000
    is_active: bool = True


@dataclass
class MemorySnapshot:
    """Memory snapshot data structure."""
    snapshot_id: str
    session_id: str
    memory_type: str  # 'working', 'consolidated', 'archived', 'critical'
    content_path: str  # Filesystem path to actual content
    content_hash: str
    compression_ratio: float
    importance_score: float = 0.5


class MemorySnapshotManager:
    """Manages filesystem storage for large memory snapshots."""
    
    def __init__(self, storage_path: Path):
        """Initialize memory snapshot manager."""
        self.storage_path = storage_path / "memory_snapshots"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"MemorySnapshotManager initialized: {self.storage_path}")
    
    def save_snapshot(self, snapshot_id: str, content: Dict[str, Any]) -> tuple[str, str]:
        """
        Save content to filesystem.
        
        Returns:
            Tuple of (file_path, content_hash)
        """
        content_json = json.dumps(content, sort_keys=True)
        content_hash = hashlib.sha256(content_json.encode()).hexdigest()
        
        file_path = self.storage_path / f"{snapshot_id}.json"
        with open(file_path, 'w') as f:
            f.write(content_json)
        
        relative_path = str(file_path.relative_to(self.storage_path.parent))
        logger.debug(f"Saved snapshot {snapshot_id}: {len(content_json)} bytes")
        return relative_path, content_hash
    
    def load_snapshot(self, file_path: str) -> Dict[str, Any]:
        """Load content from filesystem."""
        try:
            full_path = self.storage_path.parent / file_path
            with open(full_path, 'r') as f:
                content = json.load(f)
            logger.debug(f"Loaded snapshot from {file_path}")
            return content
        except FileNotFoundError:
            logger.error(f"Snapshot file not found: {file_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in snapshot {file_path}: {e}")
            return {}
    
    def delete_snapshot(self, file_path: str) -> bool:
        """Delete snapshot file."""
        try:
            full_path = self.storage_path.parent / file_path
            full_path.unlink()
            logger.info(f"Deleted snapshot: {file_path}")
            return True
        except FileNotFoundError:
            logger.warning(f"Snapshot file not found for deletion: {file_path}")
            return False


class SchemaMigration:
    """Schema migration management."""
    
    def __init__(self, db_connection):
        """Initialize migration manager."""
        self.db = db_connection
        self._init_migration_table()
    
    def _init_migration_table(self):
        """Create migration tracking table."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)
        self.db.commit()
    
    def get_current_version(self) -> int:
        """Get current schema version."""
        cursor = self.db.execute("SELECT MAX(version) FROM schema_migrations")
        result = cursor.fetchone()[0]
        return result if result is not None else 0
    
    def apply_migration(self, version: int, description: str, sql_commands: List[str]) -> bool:
        """Apply migration if not already applied."""
        current = self.get_current_version()
        if version <= current:
            logger.info(f"Migration {version} already applied")
            return False
        
        try:
            with self.db:
                # Apply all SQL commands
                for sql in sql_commands:
                    self.db.execute(sql)
                
                # Record migration
                self.db.execute(
                    "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                    (version, description)
                )
            
            logger.info(f"Applied migration {version}: {description}")
            return True
        except Exception as e:
            logger.error(f"Migration {version} failed: {e}")
            raise


class AgentHiveDatabaseManager:
    """
    Consolidated database manager for all agent hive features.
    
    Manages:
    - Context sessions and memory snapshots
    - Task and project tracking
    - Agent coordination and messaging
    - Performance metrics
    - Configuration management
    """
    
    def __init__(self, db_path: str, storage_path: Path):
        """Initialize database manager."""
        self.db_path = db_path
        self.storage_path = Path(storage_path)
        self.memory_manager = MemorySnapshotManager(self.storage_path)
        self.db = None
        self.migration = None
        
        # Initialize database
        self._init_database()
        logger.info(f"AgentHiveDatabaseManager initialized: {db_path}")
    
    def _init_database(self):
        """Initialize database connection and schema."""
        self.db = sqlite3.connect(self.db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row  # Enable column access by name
        
        # Enable WAL mode for better concurrency
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=5000")  # 5 second timeout
        self.db.execute("PRAGMA foreign_keys=ON")
        
        # Initialize migration system
        self.migration = SchemaMigration(self.db)
        
        # Apply initial schema and critical migrations
        self._apply_initial_schema()
        self._apply_critical_indexes()
    
    def _apply_initial_schema(self):
        """Apply initial database schema."""
        initial_schema = [
            # Core agent management
            """CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                agent_type TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('active', 'idle', 'crashed', 'sleeping')),
                worktree_path TEXT,
                branch_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                configuration JSON
            )""",
            
            # Task management
            """CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                agent_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL CHECK (status IN ('pending', 'in_progress', 'completed', 'failed')),
                priority TEXT NOT NULL CHECK (priority IN ('high', 'medium', 'low')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                started_at DATETIME,
                completed_at DATETIME,
                estimated_duration INTEGER,
                actual_duration INTEGER,
                confidence_score REAL,
                parent_task_id TEXT,
                tags JSON,
                metadata JSON,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
                FOREIGN KEY (parent_task_id) REFERENCES tasks(task_id)
            )""",
            
            # Context sessions
            """CREATE TABLE IF NOT EXISTS context_sessions (
                session_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                context_data JSON,
                usage_percent REAL DEFAULT 0.0,
                token_count INTEGER DEFAULT 0,
                max_tokens INTEGER DEFAULT 200000,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
            )""",
            
            # Memory snapshots (with filesystem storage)
            """CREATE TABLE IF NOT EXISTS memory_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                memory_type TEXT NOT NULL CHECK (memory_type IN ('working', 'consolidated', 'archived', 'critical')),
                content_path TEXT NOT NULL,
                content_hash TEXT,
                compression_ratio REAL,
                importance_score REAL DEFAULT 0.5,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                tags JSON,
                FOREIGN KEY (session_id) REFERENCES context_sessions(session_id)
            )""",
            
            # Performance metrics
            """CREATE TABLE IF NOT EXISTS performance_metrics (
                metric_id TEXT PRIMARY KEY,
                agent_id TEXT,
                task_id TEXT,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT,
                context JSON,
                recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
                FOREIGN KEY (task_id) REFERENCES tasks(task_id)
            )""",
            
            # Configuration management
            """CREATE TABLE IF NOT EXISTS configurations (
                config_id TEXT PRIMARY KEY,
                agent_id TEXT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value JSON NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
                UNIQUE (agent_id, category, key)
            )""",
            
            # Event logging
            """CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                agent_id TEXT,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical')),
                message TEXT NOT NULL,
                details JSON,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                correlation_id TEXT,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
            )"""
        ]
        
        self.migration.apply_migration(1, "Initial schema", initial_schema)
    
    def _apply_critical_indexes(self):
        """Apply critical indexes for performance."""
        critical_indexes = [
            # Foreign key indexes (CRITICAL for performance)
            "CREATE INDEX IF NOT EXISTS idx_tasks_agent_id ON tasks(agent_id)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_parent_task_id ON tasks(parent_task_id)",
            "CREATE INDEX IF NOT EXISTS idx_context_sessions_agent_id ON context_sessions(agent_id)",
            "CREATE INDEX IF NOT EXISTS idx_memory_snapshots_session_id ON memory_snapshots(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_performance_metrics_agent_id ON performance_metrics(agent_id)",
            "CREATE INDEX IF NOT EXISTS idx_performance_metrics_task_id ON performance_metrics(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_configurations_agent_id ON configurations(agent_id)",
            "CREATE INDEX IF NOT EXISTS idx_events_agent_id ON events(agent_id)",
            
            # Query optimization indexes
            "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_context_sessions_usage ON context_sessions(usage_percent)",
            "CREATE INDEX IF NOT EXISTS idx_memory_snapshots_importance ON memory_snapshots(importance_score)",
            "CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_configurations_category ON configurations(category, key)"
        ]
        
        self.migration.apply_migration(2, "Critical performance indexes", critical_indexes)
    
    # Context and Memory Management
    async def create_context_session(self, agent_id: str, context_data: Dict[str, Any] = None) -> str:
        """Create new context session."""
        session_id = f"ctx_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        context_data = context_data or {}
        token_count = len(json.dumps(context_data))
        usage_percent = min(token_count / 200000 * 100, 100.0)
        
        self.db.execute("""
            INSERT INTO context_sessions 
            (session_id, agent_id, context_data, usage_percent, token_count)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, agent_id, json.dumps(context_data), usage_percent, token_count))
        self.db.commit()
        
        logger.info(f"Created context session {session_id} for agent {agent_id}")
        return session_id
    
    async def save_memory_snapshot(self, session_id: str, memory_type: str, 
                                 content: Dict[str, Any], importance_score: float = 0.5) -> str:
        """Save memory snapshot to filesystem and database."""
        snapshot_id = f"snap_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Save content to filesystem
        content_path, content_hash = self.memory_manager.save_snapshot(snapshot_id, content)
        
        # Calculate compression ratio (placeholder)
        original_size = len(json.dumps(content))
        compression_ratio = 1.0  # No compression in this implementation
        
        # Save metadata to database
        self.db.execute("""
            INSERT INTO memory_snapshots 
            (snapshot_id, session_id, memory_type, content_path, content_hash, 
             compression_ratio, importance_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (snapshot_id, session_id, memory_type, content_path, content_hash,
              compression_ratio, importance_score))
        self.db.commit()
        
        logger.info(f"Saved memory snapshot {snapshot_id}: {original_size} bytes")
        return snapshot_id
    
    async def load_memory_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Load memory snapshot from filesystem."""
        cursor = self.db.execute("""
            SELECT content_path FROM memory_snapshots WHERE snapshot_id = ?
        """, (snapshot_id,))
        
        row = cursor.fetchone()
        if not row:
            logger.warning(f"Memory snapshot not found: {snapshot_id}")
            return None
        
        content = self.memory_manager.load_snapshot(row['content_path'])
        logger.debug(f"Loaded memory snapshot {snapshot_id}")
        return content
    
    # Agent Management
    async def register_agent(self, agent_id: str, agent_type: str, 
                           worktree_path: str = None, configuration: Dict[str, Any] = None) -> bool:
        """Register new agent."""
        try:
            self.db.execute("""
                INSERT INTO agents (agent_id, agent_type, status, worktree_path, configuration)
                VALUES (?, ?, 'active', ?, ?)
            """, (agent_id, agent_type, worktree_path, json.dumps(configuration or {})))
            self.db.commit()
            
            logger.info(f"Registered agent {agent_id} ({agent_type})")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Agent {agent_id} already registered")
            return False
    
    async def update_agent_activity(self, agent_id: str, status: str = None):
        """Update agent activity timestamp and status."""
        updates = ["last_activity = CURRENT_TIMESTAMP"]
        params = []
        
        if status:
            updates.append("status = ?")
            params.append(status)
        
        params.append(agent_id)
        
        self.db.execute(f"""
            UPDATE agents SET {', '.join(updates)} WHERE agent_id = ?
        """, params)
        self.db.commit()
    
    # Task Management
    async def create_task(self, agent_id: str, title: str, description: str = None,
                        priority: str = "medium", parent_task_id: str = None) -> str:
        """Create new task."""
        task_id = f"task_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        self.db.execute("""
            INSERT INTO tasks (task_id, agent_id, title, description, status, priority, parent_task_id)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
        """, (task_id, agent_id, title, description, priority, parent_task_id))
        self.db.commit()
        
        logger.info(f"Created task {task_id}: {title}")
        return task_id
    
    async def update_task_status(self, task_id: str, status: str, confidence_score: float = None):
        """Update task status."""
        updates = ["status = ?"]
        params = [status]
        
        if status == "in_progress":
            updates.append("started_at = CURRENT_TIMESTAMP")
        elif status in ["completed", "failed"]:
            updates.append("completed_at = CURRENT_TIMESTAMP")
        
        if confidence_score is not None:
            updates.append("confidence_score = ?")
            params.append(confidence_score)
        
        params.append(task_id)
        
        self.db.execute(f"""
            UPDATE tasks SET {', '.join(updates)} WHERE task_id = ?
        """, params)
        self.db.commit()
        
        logger.info(f"Updated task {task_id} status: {status}")
    
    # Performance Metrics
    async def record_metric(self, agent_id: str, metric_type: str, value: float,
                          unit: str = None, task_id: str = None, context: Dict[str, Any] = None):
        """Record performance metric."""
        metric_id = f"metric_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        self.db.execute("""
            INSERT INTO performance_metrics 
            (metric_id, agent_id, task_id, metric_type, value, unit, context)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (metric_id, agent_id, task_id, metric_type, value, unit, json.dumps(context or {})))
        self.db.commit()
        
        logger.debug(f"Recorded metric {metric_type}: {value} {unit or ''}")
    
    # Utility Methods
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {}
        tables = ['agents', 'tasks', 'context_sessions', 'memory_snapshots', 
                 'performance_metrics', 'configurations', 'events']
        
        for table in tables:
            cursor = self.db.execute(f"SELECT COUNT(*) FROM {table}")
            stats[f"{table}_count"] = cursor.fetchone()[0]
        
        # Database size
        cursor = self.db.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        cursor = self.db.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        stats["database_size_bytes"] = page_count * page_size
        
        return stats
    
    def close(self):
        """Close database connection."""
        if self.db:
            self.db.close()
            logger.info("Database connection closed")