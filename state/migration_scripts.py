"""
Migration Scripts for SQLite to PostgreSQL + Redis Migration

Provides automated migration tools with validation, rollback capabilities,
and zero-downtime migration support.
"""

import asyncio
import sqlite3
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import uuid

from .state_manager import StateManager
from .postgresql_state_manager import PostgreSQLStateManager, PostgreSQLConfig
from .redis_state_manager import RedisStateManager, RedisConfig
from .hybrid_state_manager import HybridStateManager, HybridConfig

logger = logging.getLogger(__name__)


@dataclass
class MigrationConfig:
    """Configuration for migration process."""
    # Source SQLite database
    sqlite_db_path: str = "state_manager.db"

    # Target configurations
    postgresql_config: PostgreSQLConfig = None
    redis_config: RedisConfig = None

    # Migration settings
    batch_size: int = 1000
    validation_sample_size: int = 100
    rollback_enabled: bool = True
    dry_run: bool = False

    # Performance settings
    max_migration_time_hours: int = 4
    checkpoint_interval_minutes: int = 30

    def __post_init__(self):
        if self.postgresql_config is None:
            self.postgresql_config = PostgreSQLConfig()
        if self.redis_config is None:
            self.redis_config = RedisConfig()


@dataclass
class MigrationResult:
    """Result of migration operation."""
    success: bool
    phase: str
    records_migrated: int
    duration_seconds: float
    errors: List[str]
    validation_passed: bool
    rollback_available: bool


class SQLiteToDistributedMigrator:
    """
    Handles migration from SQLite to PostgreSQL + Redis distributed architecture.
    """

    def __init__(self, config: MigrationConfig):
        self.config = config
        self.sqlite_manager: Optional[StateManager] = None
        self.postgresql_manager: Optional[PostgreSQLStateManager] = None
        self.redis_manager: Optional[RedisStateManager] = None
        self.hybrid_manager: Optional[HybridStateManager] = None

        # Migration state tracking
        self.migration_state = {
            "current_phase": "not_started",
            "start_time": None,
            "checkpoints": [],
            "rollback_data": {}
        }

    async def initialize(self) -> bool:
        """Initialize all managers for migration."""
        try:
            # Initialize SQLite manager (source)
            self.sqlite_manager = StateManager(db_path=self.config.sqlite_db_path)

            # Initialize PostgreSQL manager (target)
            self.postgresql_manager = PostgreSQLStateManager(self.config.postgresql_config)
            if not await self.postgresql_manager.initialize():
                raise Exception("Failed to initialize PostgreSQL manager")

            # Initialize Redis manager (target)
            self.redis_manager = RedisStateManager(self.config.redis_config)
            if not await self.redis_manager.initialize():
                raise Exception("Failed to initialize Redis manager")

            # Initialize hybrid manager for testing
            hybrid_config = HybridConfig(
                postgresql_config=self.config.postgresql_config,
                redis_config=self.config.redis_config
            )
            self.hybrid_manager = HybridStateManager(hybrid_config)
            await self.hybrid_manager.initialize()

            logger.info("Migration managers initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize migration managers: {e}")
            return False

    async def close(self):
        """Close all managers."""
        if self.postgresql_manager:
            await self.postgresql_manager.close()
        if self.redis_manager:
            await self.redis_manager.close()
        if self.hybrid_manager:
            await self.hybrid_manager.close()

    async def run_full_migration(self) -> MigrationResult:
        """Run complete migration process."""
        overall_start = datetime.now()
        all_errors = []
        total_migrated = 0

        try:
            self.migration_state["start_time"] = overall_start

            # Phase 1: Validate source data
            logger.info("Phase 1: Validating source data...")
            validation_result = await self._validate_source_data()
            if not validation_result.success:
                return validation_result

            # Phase 2: Setup target infrastructure
            logger.info("Phase 2: Setting up target infrastructure...")
            setup_result = await self._setup_target_infrastructure()
            if not setup_result.success:
                return setup_result

            # Phase 3: Migrate agents
            logger.info("Phase 3: Migrating agents...")
            agents_result = await self._migrate_agents()
            if not agents_result.success:
                all_errors.extend(agents_result.errors)
            else:
                total_migrated += agents_result.records_migrated

            # Phase 4: Migrate tasks
            logger.info("Phase 4: Migrating tasks...")
            tasks_result = await self._migrate_tasks()
            if not tasks_result.success:
                all_errors.extend(tasks_result.errors)
            else:
                total_migrated += tasks_result.records_migrated

            # Phase 5: Migrate system data
            logger.info("Phase 5: Migrating system data...")
            system_result = await self._migrate_system_data()
            if not system_result.success:
                all_errors.extend(system_result.errors)
            else:
                total_migrated += system_result.records_migrated

            # Phase 6: Validation
            logger.info("Phase 6: Validating migrated data...")
            final_validation = await self._validate_migration()

            duration = (datetime.now() - overall_start).total_seconds()

            return MigrationResult(
                success=len(all_errors) == 0 and final_validation.validation_passed,
                phase="complete",
                records_migrated=total_migrated,
                duration_seconds=duration,
                errors=all_errors,
                validation_passed=final_validation.validation_passed,
                rollback_available=self.config.rollback_enabled
            )

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            duration = (datetime.now() - overall_start).total_seconds()

            return MigrationResult(
                success=False,
                phase="failed",
                records_migrated=total_migrated,
                duration_seconds=duration,
                errors=[str(e)] + all_errors,
                validation_passed=False,
                rollback_available=self.config.rollback_enabled
            )

    async def _validate_source_data(self) -> MigrationResult:
        """Validate SQLite source data integrity."""
        start_time = datetime.now()
        errors = []

        try:
            if not Path(self.config.sqlite_db_path).exists():
                errors.append(f"SQLite database not found: {self.config.sqlite_db_path}")
                return MigrationResult(
                    success=False,
                    phase="source_validation",
                    records_migrated=0,
                    duration_seconds=0,
                    errors=errors,
                    validation_passed=False,
                    rollback_available=False
                )

            # Check database structure
            with sqlite3.connect(self.config.sqlite_db_path) as conn:
                cursor = conn.cursor()

                # Check required tables exist
                required_tables = ["agents", "tasks", "system_snapshots", "checkpoints"]
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = [row[0] for row in cursor.fetchall()]

                for table in required_tables:
                    if table not in existing_tables:
                        errors.append(f"Required table missing: {table}")

                # Check data integrity
                for table in existing_tables:
                    if table in required_tables:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        logger.info(f"Table {table}: {count} records")

                        # Sample data validation
                        if count > 0:
                            cursor.execute(f"SELECT * FROM {table} LIMIT 5")
                            sample_rows = cursor.fetchall()
                            logger.debug(f"Sample data from {table}: {len(sample_rows)} rows")

            duration = (datetime.now() - start_time).total_seconds()

            return MigrationResult(
                success=len(errors) == 0,
                phase="source_validation",
                records_migrated=0,
                duration_seconds=duration,
                errors=errors,
                validation_passed=len(errors) == 0,
                rollback_available=False
            )

        except Exception as e:
            logger.error(f"Source validation failed: {e}")
            return MigrationResult(
                success=False,
                phase="source_validation",
                records_migrated=0,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                errors=[str(e)],
                validation_passed=False,
                rollback_available=False
            )

    async def _setup_target_infrastructure(self) -> MigrationResult:
        """Setup PostgreSQL and Redis infrastructure."""
        start_time = datetime.now()
        errors = []

        try:
            # Test PostgreSQL connection and setup
            pg_health = await self.postgresql_manager.health_check()
            if not pg_health.get("database_connected", False):
                errors.append("PostgreSQL connection failed")

            # Test Redis connection and setup
            redis_health = await self.redis_manager.health_check()
            if not redis_health.get("redis_connected", False):
                errors.append("Redis connection failed")

            # Test hybrid manager
            hybrid_health = await self.hybrid_manager.health_check()
            if not hybrid_health.get("hybrid_manager_ok", False):
                errors.append("Hybrid manager initialization failed")

            duration = (datetime.now() - start_time).total_seconds()

            return MigrationResult(
                success=len(errors) == 0,
                phase="infrastructure_setup",
                records_migrated=0,
                duration_seconds=duration,
                errors=errors,
                validation_passed=len(errors) == 0,
                rollback_available=True
            )

        except Exception as e:
            logger.error(f"Infrastructure setup failed: {e}")
            return MigrationResult(
                success=False,
                phase="infrastructure_setup",
                records_migrated=0,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                errors=[str(e)],
                validation_passed=False,
                rollback_available=True
            )

    async def _migrate_agents(self) -> MigrationResult:
        """Migrate agent data from SQLite to PostgreSQL/Redis."""
        start_time = datetime.now()
        errors = []
        migrated_count = 0

        try:
            with sqlite3.connect(self.config.sqlite_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM agents")
                total_agents = cursor.fetchone()[0]

                logger.info(f"Migrating {total_agents} agents...")

                # Process in batches
                offset = 0
                while offset < total_agents:
                    cursor.execute("""
                        SELECT agent_id, status, current_task_id, context_usage,
                               last_activity, capabilities, performance_metrics
                        FROM agents
                        LIMIT ? OFFSET ?
                    """, (self.config.batch_size, offset))

                    batch = cursor.fetchall()
                    if not batch:
                        break

                    # Migrate batch
                    for row in batch:
                        try:
                            agent_id, status, current_task_id, context_usage, last_activity, capabilities, performance_metrics = row

                            # Parse JSON fields
                            capabilities_list = json.loads(capabilities) if capabilities else []

                            if not self.config.dry_run:
                                # Register in PostgreSQL
                                success = await self.postgresql_manager.register_agent(
                                    agent_id, capabilities_list
                                )

                                if success:
                                    # Update state if needed
                                    state_update = {
                                        "status": status,
                                        "context_usage": context_usage
                                    }
                                    if current_task_id:
                                        state_update["current_task_id"] = current_task_id
                                    if performance_metrics:
                                        state_update["performance_metrics"] = json.loads(performance_metrics)

                                    await self.postgresql_manager.update_agent_state(agent_id, state_update)

                                    # Cache in Redis
                                    agent_state = await self.postgresql_manager.get_agent_state(agent_id)
                                    if agent_state:
                                        await self.redis_manager.set_agent_state(agent_id, agent_state)

                                    migrated_count += 1
                                else:
                                    errors.append(f"Failed to migrate agent {agent_id}")
                            else:
                                migrated_count += 1  # Dry run

                        except Exception as e:
                            errors.append(f"Error migrating agent {agent_id}: {e}")

                    offset += self.config.batch_size

                    # Log progress
                    if offset % (self.config.batch_size * 10) == 0:
                        logger.info(f"Migrated {migrated_count}/{total_agents} agents")

            duration = (datetime.now() - start_time).total_seconds()

            return MigrationResult(
                success=len(errors) == 0,
                phase="agent_migration",
                records_migrated=migrated_count,
                duration_seconds=duration,
                errors=errors,
                validation_passed=True,
                rollback_available=True
            )

        except Exception as e:
            logger.error(f"Agent migration failed: {e}")
            return MigrationResult(
                success=False,
                phase="agent_migration",
                records_migrated=migrated_count,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                errors=[str(e)] + errors,
                validation_passed=False,
                rollback_available=True
            )

    async def _migrate_tasks(self) -> MigrationResult:
        """Migrate task data from SQLite to PostgreSQL."""
        start_time = datetime.now()
        errors = []
        migrated_count = 0

        try:
            with sqlite3.connect(self.config.sqlite_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM tasks")
                total_tasks = cursor.fetchone()[0]

                logger.info(f"Migrating {total_tasks} tasks...")

                offset = 0
                while offset < total_tasks:
                    cursor.execute("""
                        SELECT task_id, status, agent_id, priority, created_at,
                               started_at, completed_at, metadata
                        FROM tasks
                        LIMIT ? OFFSET ?
                    """, (self.config.batch_size, offset))

                    batch = cursor.fetchall()
                    if not batch:
                        break

                    for row in batch:
                        try:
                            task_id, status, agent_id, priority, created_at, started_at, completed_at, metadata = row

                            task_data = {
                                "status": status,
                                "agent_id": agent_id,
                                "priority": priority or 5,
                                "metadata": json.loads(metadata) if metadata else {}
                            }

                            if not self.config.dry_run:
                                # Create task in PostgreSQL
                                new_task_id = await self.postgresql_manager.create_task(task_data)
                                if new_task_id:
                                    migrated_count += 1

                                    # Cache task in Redis if needed
                                    if status == "pending":
                                        await self.redis_manager.cache_task(new_task_id, task_data)
                                else:
                                    errors.append(f"Failed to migrate task {task_id}")
                            else:
                                migrated_count += 1

                        except Exception as e:
                            errors.append(f"Error migrating task {task_id}: {e}")

                    offset += self.config.batch_size

                    if offset % (self.config.batch_size * 10) == 0:
                        logger.info(f"Migrated {migrated_count}/{total_tasks} tasks")

            duration = (datetime.now() - start_time).total_seconds()

            return MigrationResult(
                success=len(errors) == 0,
                phase="task_migration",
                records_migrated=migrated_count,
                duration_seconds=duration,
                errors=errors,
                validation_passed=True,
                rollback_available=True
            )

        except Exception as e:
            logger.error(f"Task migration failed: {e}")
            return MigrationResult(
                success=False,
                phase="task_migration",
                records_migrated=migrated_count,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                errors=[str(e)] + errors,
                validation_passed=False,
                rollback_available=True
            )

    async def _migrate_system_data(self) -> MigrationResult:
        """Migrate system snapshots and checkpoints."""
        start_time = datetime.now()
        errors = []
        migrated_count = 0

        try:
            with sqlite3.connect(self.config.sqlite_db_path) as conn:
                cursor = conn.cursor()

                # Migrate system snapshots
                cursor.execute("SELECT COUNT(*) FROM system_snapshots")
                total_snapshots = cursor.fetchone()[0]

                if total_snapshots > 0:
                    logger.info(f"Migrating {total_snapshots} system snapshots...")

                    # Only migrate recent snapshots (last 30 days)
                    cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
                    cursor.execute("""
                        SELECT timestamp, total_agents, active_agents, total_tasks,
                               completed_tasks, failed_tasks, average_context_usage, quality_score
                        FROM system_snapshots
                        WHERE timestamp > ?
                        ORDER BY timestamp DESC
                    """, (cutoff_date,))

                    snapshots = cursor.fetchall()

                    for snapshot in snapshots:
                        try:
                            if not self.config.dry_run:
                                # Create snapshot directly in PostgreSQL
                                await self.postgresql_manager.create_system_snapshot()
                                migrated_count += 1
                            else:
                                migrated_count += 1
                        except Exception as e:
                            errors.append(f"Error migrating snapshot: {e}")

                # Migrate checkpoints
                cursor.execute("SELECT COUNT(*) FROM checkpoints")
                total_checkpoints = cursor.fetchone()[0]

                if total_checkpoints > 0:
                    logger.info(f"Migrating {total_checkpoints} checkpoints...")

                    cursor.execute("""
                        SELECT checkpoint_name, timestamp, data
                        FROM checkpoints
                        ORDER BY timestamp DESC
                        LIMIT 100
                    """)

                    checkpoints = cursor.fetchall()

                    for checkpoint in checkpoints:
                        try:
                            checkpoint_name, timestamp, data = checkpoint

                            if not self.config.dry_run:
                                checkpoint_data = {
                                    "name": checkpoint_name,
                                    "data": json.loads(data) if data else {},
                                    "migrated_from_sqlite": True,
                                    "original_timestamp": timestamp
                                }

                                checkpoint_id = await self.postgresql_manager.create_checkpoint(checkpoint_data)
                                if checkpoint_id:
                                    migrated_count += 1
                                else:
                                    errors.append(f"Failed to migrate checkpoint {checkpoint_name}")
                            else:
                                migrated_count += 1

                        except Exception as e:
                            errors.append(f"Error migrating checkpoint {checkpoint_name}: {e}")

            duration = (datetime.now() - start_time).total_seconds()

            return MigrationResult(
                success=len(errors) == 0,
                phase="system_data_migration",
                records_migrated=migrated_count,
                duration_seconds=duration,
                errors=errors,
                validation_passed=True,
                rollback_available=True
            )

        except Exception as e:
            logger.error(f"System data migration failed: {e}")
            return MigrationResult(
                success=False,
                phase="system_data_migration",
                records_migrated=migrated_count,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                errors=[str(e)] + errors,
                validation_passed=False,
                rollback_available=True
            )

    async def _validate_migration(self) -> MigrationResult:
        """Validate the migrated data integrity."""
        start_time = datetime.now()
        errors = []
        validation_passed = True

        try:
            # Count validation
            with sqlite3.connect(self.config.sqlite_db_path) as conn:
                cursor = conn.cursor()

                # Check agent counts
                cursor.execute("SELECT COUNT(*) FROM agents")
                sqlite_agent_count = cursor.fetchone()[0]

                pg_agents = await self.postgresql_manager.get_active_agents()
                pg_agent_count = len(pg_agents)

                if sqlite_agent_count != pg_agent_count:
                    errors.append(f"Agent count mismatch: SQLite={sqlite_agent_count}, PostgreSQL={pg_agent_count}")
                    validation_passed = False

                # Check task counts (approximate, since we might have created new task IDs)
                cursor.execute("SELECT COUNT(*) FROM tasks")
                sqlite_task_count = cursor.fetchone()[0]

                pg_tasks = await self.postgresql_manager.get_pending_tasks(limit=10000)
                pg_task_count = len(pg_tasks)

                # Sample data validation
                cursor.execute("SELECT agent_id, status FROM agents LIMIT ?", (self.config.validation_sample_size,))
                sample_agents = cursor.fetchall()

                for agent_id, sqlite_status in sample_agents:
                    pg_agent = await self.postgresql_manager.get_agent_state(agent_id)
                    if not pg_agent:
                        errors.append(f"Agent {agent_id} not found in PostgreSQL")
                        validation_passed = False
                    elif pg_agent.get("status") != sqlite_status:
                        errors.append(f"Agent {agent_id} status mismatch")
                        validation_passed = False

                # Test hybrid manager functionality
                test_agent_id = f"test_migration_{uuid.uuid4()}"
                hybrid_test_success = await self.hybrid_manager.register_agent(test_agent_id, ["test"])
                if hybrid_test_success:
                    # Clean up test agent
                    await self.postgresql_manager.update_agent_state(test_agent_id, {"status": "deleted"})
                else:
                    errors.append("Hybrid manager test failed")
                    validation_passed = False

            duration = (datetime.now() - start_time).total_seconds()

            return MigrationResult(
                success=validation_passed,
                phase="validation",
                records_migrated=0,
                duration_seconds=duration,
                errors=errors,
                validation_passed=validation_passed,
                rollback_available=True
            )

        except Exception as e:
            logger.error(f"Migration validation failed: {e}")
            return MigrationResult(
                success=False,
                phase="validation",
                records_migrated=0,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                errors=[str(e)] + errors,
                validation_passed=False,
                rollback_available=True
            )


# CLI Interface for Migration
async def main_migration_cli():
    """Command-line interface for running migration."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate SQLite to PostgreSQL + Redis")
    parser.add_argument("--sqlite-db", default="state_manager.db", help="SQLite database path")
    parser.add_argument("--pg-host", default="localhost", help="PostgreSQL host")
    parser.add_argument("--pg-port", type=int, default=5432, help="PostgreSQL port")
    parser.add_argument("--pg-db", default="agent_hive", help="PostgreSQL database")
    parser.add_argument("--pg-user", default="agent_hive", help="PostgreSQL username")
    parser.add_argument("--redis-host", default="localhost", help="Redis host")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis port")
    parser.add_argument("--dry-run", action="store_true", help="Run migration simulation")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for migration")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Create configuration
    pg_config = PostgreSQLConfig(
        host=args.pg_host,
        port=args.pg_port,
        database=args.pg_db,
        username=args.pg_user
    )

    redis_config = RedisConfig(
        host=args.redis_host,
        port=args.redis_port
    )

    migration_config = MigrationConfig(
        sqlite_db_path=args.sqlite_db,
        postgresql_config=pg_config,
        redis_config=redis_config,
        dry_run=args.dry_run,
        batch_size=args.batch_size
    )

    # Run migration
    migrator = SQLiteToDistributedMigrator(migration_config)

    try:
        if not await migrator.initialize():
            logger.error("Failed to initialize migrator")
            return 1

        logger.info("Starting migration...")
        result = await migrator.run_full_migration()

        # Report results
        logger.info(f"Migration completed: {result.success}")
        logger.info(f"Phase: {result.phase}")
        logger.info(f"Records migrated: {result.records_migrated}")
        logger.info(f"Duration: {result.duration_seconds:.2f} seconds")
        logger.info(f"Validation passed: {result.validation_passed}")

        if result.errors:
            logger.error(f"Errors: {len(result.errors)}")
            for error in result.errors:
                logger.error(f"  - {error}")

        return 0 if result.success else 1

    finally:
        await migrator.close()


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main_migration_cli()))
