"""
Tests for Database Manager - Consolidated database architecture
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path

from external_api.database_manager import (
    AgentHiveDatabaseManager,
    MemorySnapshotManager,
    SchemaMigration
)


class TestMemorySnapshotManager:
    """Test suite for MemorySnapshotManager."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def memory_manager(self, temp_storage):
        """Create MemorySnapshotManager instance."""
        return MemorySnapshotManager(temp_storage)

    def test_initialization(self, memory_manager, temp_storage):
        """Test memory manager initialization."""
        expected_path = temp_storage / "memory_snapshots"
        assert memory_manager.storage_path == expected_path
        assert expected_path.exists()

    def test_save_and_load_snapshot(self, memory_manager):
        """Test saving and loading memory snapshots."""
        snapshot_id = "test_snapshot_001"
        content = {
            "context": "Test context data",
            "memory": ["item1", "item2", "item3"],
            "metadata": {"importance": 0.8}
        }

        # Save snapshot
        file_path, content_hash = memory_manager.save_snapshot(snapshot_id, content)
        assert file_path.endswith(f"{snapshot_id}.json")
        assert content_hash is not None
        assert len(content_hash) == 64  # SHA256 hash length

        # Load snapshot
        loaded_content = memory_manager.load_snapshot(file_path)
        assert loaded_content == content

    def test_load_nonexistent_snapshot(self, memory_manager):
        """Test loading non-existent snapshot."""
        result = memory_manager.load_snapshot("nonexistent/path.json")
        assert result == {}

    def test_delete_snapshot(self, memory_manager):
        """Test deleting snapshots."""
        snapshot_id = "test_delete_001"
        content = {"test": "data"}

        # Save and then delete
        file_path, _ = memory_manager.save_snapshot(snapshot_id, content)
        assert memory_manager.delete_snapshot(file_path) is True

        # Try to delete again
        assert memory_manager.delete_snapshot(file_path) is False


class TestSchemaMigration:
    """Test suite for SchemaMigration."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        db = sqlite3.connect(db_path)
        yield db

        db.close()
        Path(db_path).unlink()

    @pytest.fixture
    def migration(self, temp_db):
        """Create SchemaMigration instance."""
        return SchemaMigration(temp_db)

    def test_initialization(self, migration, temp_db):
        """Test migration system initialization."""
        # Check migration table exists
        cursor = temp_db.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='schema_migrations'
        """)
        assert cursor.fetchone() is not None

    def test_initial_version(self, migration):
        """Test initial schema version."""
        assert migration.get_current_version() == 0

    def test_apply_migration(self, migration):
        """Test applying migrations."""
        sql_commands = [
            "CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)",
            "CREATE INDEX idx_test_name ON test_table(name)"
        ]

        # Apply migration
        result = migration.apply_migration(1, "Test migration", sql_commands)
        assert result is True
        assert migration.get_current_version() == 1

        # Try to apply same migration again
        result = migration.apply_migration(1, "Test migration", sql_commands)
        assert result is False  # Already applied


class TestAgentHiveDatabaseManager:
    """Test suite for AgentHiveDatabaseManager."""

    @pytest.fixture
    def temp_setup(self):
        """Create temporary database and storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_path = temp_path / "test_agent_hive.db"
            yield str(db_path), temp_path

    @pytest.fixture
    def db_manager(self, temp_setup):
        """Create AgentHiveDatabaseManager instance."""
        db_path, storage_path = temp_setup
        manager = AgentHiveDatabaseManager(db_path, storage_path)
        yield manager
        manager.close()

    def test_initialization(self, db_manager):
        """Test database manager initialization."""
        assert db_manager.db is not None
        assert db_manager.migration is not None
        assert db_manager.memory_manager is not None

        # Check initial schema version
        assert db_manager.migration.get_current_version() >= 1

    def test_database_stats(self, db_manager):
        """Test database statistics."""
        stats = db_manager.get_database_stats()

        # Check required tables exist
        expected_tables = ['agents', 'tasks', 'context_sessions', 'memory_snapshots',
                          'performance_metrics', 'configurations', 'events']

        for table in expected_tables:
            assert f"{table}_count" in stats
            assert isinstance(stats[f"{table}_count"], int)

        assert "database_size_bytes" in stats

    @pytest.mark.asyncio
    async def test_agent_management(self, db_manager):
        """Test agent registration and management."""
        agent_id = "test_agent_001"
        agent_type = "service-mesh"
        config = {"test": "configuration"}

        # Register agent
        result = await db_manager.register_agent(agent_id, agent_type, configuration=config)
        assert result is True

        # Try to register same agent again
        result = await db_manager.register_agent(agent_id, agent_type)
        assert result is False  # Already exists

        # Update agent activity
        await db_manager.update_agent_activity(agent_id, "idle")

    @pytest.mark.asyncio
    async def test_context_session_management(self, db_manager):
        """Test context session creation and management."""
        agent_id = "test_agent_002"
        await db_manager.register_agent(agent_id, "integration")

        # Create context session
        context_data = {"current_task": "testing", "variables": {"count": 42}}
        session_id = await db_manager.create_context_session(agent_id, context_data)

        assert session_id.startswith(f"ctx_{agent_id}")

        # Verify session in database
        cursor = db_manager.db.execute("""
            SELECT agent_id, usage_percent, token_count
            FROM context_sessions WHERE session_id = ?
        """, (session_id,))
        row = cursor.fetchone()

        assert row['agent_id'] == agent_id
        assert row['usage_percent'] > 0
        assert row['token_count'] > 0

    @pytest.mark.asyncio
    async def test_memory_snapshot_management(self, db_manager):
        """Test memory snapshot save and load."""
        agent_id = "test_agent_003"
        await db_manager.register_agent(agent_id, "pm")

        session_id = await db_manager.create_context_session(agent_id)

        # Save memory snapshot
        content = {
            "working_memory": ["task1", "task2"],
            "consolidated": {"key": "value"},
            "importance": 0.9
        }

        snapshot_id = await db_manager.save_memory_snapshot(
            session_id, "working", content, importance_score=0.9
        )

        assert snapshot_id.startswith(f"snap_{session_id}")

        # Load memory snapshot
        loaded_content = await db_manager.load_memory_snapshot(snapshot_id)
        assert loaded_content == content

        # Try to load non-existent snapshot
        missing_content = await db_manager.load_memory_snapshot("nonexistent")
        assert missing_content is None

    @pytest.mark.asyncio
    async def test_task_management(self, db_manager):
        """Test task creation and management."""
        agent_id = "test_agent_004"
        await db_manager.register_agent(agent_id, "frontend")

        # Create task
        title = "Test task"
        description = "Testing task management"
        task_id = await db_manager.create_task(agent_id, title, description, priority="high")

        assert task_id.startswith(f"task_{agent_id}")

        # Update task status
        await db_manager.update_task_status(task_id, "in_progress", confidence_score=0.8)
        await db_manager.update_task_status(task_id, "completed", confidence_score=0.95)

        # Verify task in database
        cursor = db_manager.db.execute("""
            SELECT title, status, confidence_score, started_at, completed_at
            FROM tasks WHERE task_id = ?
        """, (task_id,))
        row = cursor.fetchone()

        assert row['title'] == title
        assert row['status'] == "completed"
        assert row['confidence_score'] == 0.95
        assert row['started_at'] is not None
        assert row['completed_at'] is not None

    @pytest.mark.asyncio
    async def test_performance_metrics(self, db_manager):
        """Test performance metrics recording."""
        agent_id = "test_agent_005"
        await db_manager.register_agent(agent_id, "quality")

        task_id = await db_manager.create_task(agent_id, "Performance test")

        # Record metrics
        await db_manager.record_metric(
            agent_id, "duration", 125.5, unit="seconds",
            task_id=task_id, context={"operation": "code_generation"}
        )

        await db_manager.record_metric(
            agent_id, "confidence", 0.92, unit="percentage"
        )

        # Verify metrics in database
        cursor = db_manager.db.execute("""
            SELECT COUNT(*) FROM performance_metrics WHERE agent_id = ?
        """, (agent_id,))
        count = cursor.fetchone()[0]
        assert count == 2

    def test_critical_indexes_exist(self, db_manager):
        """Test that critical indexes were created."""
        # Get all indexes
        cursor = db_manager.db.execute("""
            SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'
        """)
        indexes = [row[0] for row in cursor.fetchall()]

        # Check critical foreign key indexes exist
        critical_indexes = [
            'idx_tasks_agent_id',
            'idx_context_sessions_agent_id',
            'idx_memory_snapshots_session_id',
            'idx_performance_metrics_agent_id',
            'idx_events_agent_id'
        ]

        for index in critical_indexes:
            assert index in indexes, f"Critical index {index} not found"

    def test_foreign_key_constraints(self, db_manager):
        """Test foreign key constraints are enforced."""
        # Try to create task with non-existent agent
        with pytest.raises(sqlite3.IntegrityError):
            db_manager.db.execute("""
                INSERT INTO tasks (task_id, agent_id, title, status, priority)
                VALUES ('invalid_task', 'nonexistent_agent', 'Test', 'pending', 'medium')
            """)
            db_manager.db.commit()

    def test_check_constraints(self, db_manager):
        """Test CHECK constraints are enforced."""
        # Register valid agent first
        agent_id = "test_agent_006"
        db_manager.db.execute("""
            INSERT INTO agents (agent_id, agent_type, status)
            VALUES (?, 'test', 'active')
        """, (agent_id,))
        db_manager.db.commit()

        # Try to create task with invalid priority
        with pytest.raises(sqlite3.IntegrityError):
            db_manager.db.execute("""
                INSERT INTO tasks (task_id, agent_id, title, status, priority)
                VALUES ('test_task', ?, 'Test', 'pending', 'invalid_priority')
            """, (agent_id,))
            db_manager.db.commit()
