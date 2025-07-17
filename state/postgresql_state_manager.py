"""
PostgreSQL State Manager - High-performance concurrent state management

Replaces SQLite with PostgreSQL for ACID compliance, connection pooling,
and concurrent agent operations support.
"""

import asyncio
import asyncpg
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import uuid

from .distributed_state_architecture import StateManagerProtocol, ConsistencyLevel

logger = logging.getLogger(__name__)


@dataclass
class PostgreSQLConfig:
    """Configuration for PostgreSQL connection and behavior."""
    host: str = "localhost"
    port: int = 5432
    database: str = "agent_hive"
    username: str = "agent_hive"
    password: str = ""
    
    # Connection Pool Settings
    min_connections: int = 5
    max_connections: int = 20
    command_timeout: float = 10.0
    
    # Performance Settings
    statement_cache_size: int = 100
    max_cached_statement_lifetime: int = 300
    max_inactive_connection_lifetime: float = 300.0


class PostgreSQLStateManager(StateManagerProtocol):
    """
    High-performance PostgreSQL-based state manager with connection pooling
    and optimized concurrent operations.
    """
    
    def __init__(self, config: PostgreSQLConfig):
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize PostgreSQL connection pool and database schema."""
        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                min_size=self.config.min_connections,
                max_size=self.config.max_connections,
                command_timeout=self.config.command_timeout,
                statement_cache_size=self.config.statement_cache_size,
                max_cached_statement_lifetime=self.config.max_cached_statement_lifetime,
                max_inactive_connection_lifetime=self.config.max_inactive_connection_lifetime
            )
            
            await self._create_schema()
            self._initialized = True
            logger.info(f"PostgreSQL state manager initialized with pool size {self.config.min_connections}-{self.config.max_connections}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL state manager: {e}")
            return False
    
    async def close(self):
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            self._initialized = False
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool with proper error handling."""
        if not self._initialized or not self.pool:
            raise RuntimeError("PostgreSQL state manager not initialized")
        
        conn = await self.pool.acquire()
        try:
            yield conn
        finally:
            await self.pool.release(conn)
    
    async def _create_schema(self):
        """Create optimized database schema for concurrent operations."""
        schema_queries = [
            # Agents table with optimized indexes
            """
            CREATE TABLE IF NOT EXISTS agents (
                agent_id VARCHAR(255) PRIMARY KEY,
                status VARCHAR(50) NOT NULL DEFAULT 'idle',
                current_task_id UUID,
                context_usage DECIMAL(5,4) DEFAULT 0.0,
                last_activity TIMESTAMPTZ DEFAULT NOW(),
                capabilities JSONB DEFAULT '[]'::jsonb,
                performance_metrics JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
            """,
            
            # Optimized indexes for agents
            "CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status)",
            "CREATE INDEX IF NOT EXISTS idx_agents_last_activity ON agents(last_activity)",
            "CREATE INDEX IF NOT EXISTS idx_agents_capabilities ON agents USING GIN(capabilities)",
            
            # Tasks table with UUID primary key and foreign key
            """
            CREATE TABLE IF NOT EXISTS tasks (
                task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                agent_id VARCHAR(255),
                priority INTEGER DEFAULT 5,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                started_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ,
                metadata JSONB DEFAULT '{}'::jsonb,
                result JSONB,
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE SET NULL
            )
            """,
            
            # Optimized indexes for tasks
            "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_priority_status ON tasks(priority DESC, status)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_agent_id ON tasks(agent_id)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)",
            
            # System snapshots for monitoring
            """
            CREATE TABLE IF NOT EXISTS system_snapshots (
                id BIGSERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ DEFAULT NOW(),
                total_agents INTEGER DEFAULT 0,
                active_agents INTEGER DEFAULT 0,
                total_tasks INTEGER DEFAULT 0,
                completed_tasks INTEGER DEFAULT 0,
                failed_tasks INTEGER DEFAULT 0,
                average_context_usage DECIMAL(5,4) DEFAULT 0.0,
                quality_score DECIMAL(5,4) DEFAULT 0.0,
                metadata JSONB DEFAULT '{}'::jsonb
            )
            """,
            
            "CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON system_snapshots(timestamp)",
            
            # Checkpoints table
            """
            CREATE TABLE IF NOT EXISTS checkpoints (
                id BIGSERIAL PRIMARY KEY,
                checkpoint_name VARCHAR(255) NOT NULL,
                timestamp TIMESTAMPTZ DEFAULT NOW(),
                data JSONB NOT NULL
            )
            """,
            
            "CREATE INDEX IF NOT EXISTS idx_checkpoints_name ON checkpoints(checkpoint_name)",
            "CREATE INDEX IF NOT EXISTS idx_checkpoints_timestamp ON checkpoints(timestamp)",
            
            # Update triggers for automatic timestamp management
            """
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ language 'plpgsql'
            """,
            
            """
            CREATE TRIGGER IF NOT EXISTS update_agents_updated_at 
                BEFORE UPDATE ON agents 
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
            """,
            
            """
            CREATE TRIGGER IF NOT EXISTS update_tasks_updated_at 
                BEFORE UPDATE ON tasks 
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
            """
        ]
        
        async with self.get_connection() as conn:
            for query in schema_queries:
                await conn.execute(query)
    
    # Agent State Management
    async def register_agent(self, agent_id: str, capabilities: Optional[List[str]] = None) -> bool:
        """Register a new agent with optimized upsert operation."""
        try:
            query = """
                INSERT INTO agents (agent_id, status, capabilities, last_activity)
                VALUES ($1, 'idle', $2, NOW())
                ON CONFLICT (agent_id) 
                DO UPDATE SET 
                    capabilities = $2,
                    last_activity = NOW(),
                    updated_at = NOW()
            """
            
            async with self.get_connection() as conn:
                await conn.execute(query, agent_id, json.dumps(capabilities or []))
            
            logger.debug(f"Agent {agent_id} registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False
    
    async def get_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent state with efficient single query."""
        try:
            query = """
                SELECT agent_id, status, current_task_id, context_usage, 
                       last_activity, capabilities, performance_metrics
                FROM agents 
                WHERE agent_id = $1
            """
            
            async with self.get_connection() as conn:
                row = await conn.fetchrow(query, agent_id)
            
            if not row:
                return None
            
            return {
                'agent_id': row['agent_id'],
                'status': row['status'],
                'current_task_id': str(row['current_task_id']) if row['current_task_id'] else None,
                'context_usage': float(row['context_usage']),
                'last_activity': row['last_activity'],
                'capabilities': row['capabilities'],
                'performance_metrics': row['performance_metrics']
            }
            
        except Exception as e:
            logger.error(f"Failed to get agent state for {agent_id}: {e}")
            return None
    
    async def update_agent_state(self, agent_id: str, state: Dict[str, Any]) -> bool:
        """Update agent state with atomic operation."""
        try:
            query = """
                UPDATE agents 
                SET status = COALESCE($2, status),
                    current_task_id = COALESCE($3, current_task_id),
                    context_usage = COALESCE($4, context_usage),
                    performance_metrics = COALESCE($5, performance_metrics),
                    last_activity = NOW()
                WHERE agent_id = $1
            """
            
            async with self.get_connection() as conn:
                result = await conn.execute(
                    query,
                    agent_id,
                    state.get('status'),
                    state.get('current_task_id'),
                    state.get('context_usage'),
                    json.dumps(state.get('performance_metrics')) if state.get('performance_metrics') else None
                )
            
            # Check if any rows were updated
            rows_affected = int(result.split()[-1])
            return rows_affected > 0
            
        except Exception as e:
            logger.error(f"Failed to update agent state for {agent_id}: {e}")
            return False
    
    async def get_active_agents(self) -> List[Dict[str, Any]]:
        """Get all active agents efficiently."""
        try:
            query = """
                SELECT agent_id, status, current_task_id, context_usage, 
                       last_activity, capabilities
                FROM agents 
                WHERE status IN ('idle', 'busy') 
                  AND last_activity > NOW() - INTERVAL '1 hour'
                ORDER BY last_activity DESC
            """
            
            async with self.get_connection() as conn:
                rows = await conn.fetch(query)
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get active agents: {e}")
            return []
    
    # Task Management
    async def create_task(self, task_data: Dict[str, Any]) -> Optional[str]:
        """Create a new task and return task ID."""
        try:
            query = """
                INSERT INTO tasks (status, agent_id, priority, metadata)
                VALUES ($1, $2, $3, $4)
                RETURNING task_id
            """
            
            async with self.get_connection() as conn:
                task_id = await conn.fetchval(
                    query,
                    task_data.get('status', 'pending'),
                    task_data.get('agent_id'),
                    task_data.get('priority', 5),
                    json.dumps(task_data.get('metadata', {}))
                )
            
            return str(task_id)
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return None
    
    async def get_pending_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending tasks ordered by priority."""
        try:
            query = """
                SELECT task_id, status, agent_id, priority, created_at, metadata
                FROM tasks 
                WHERE status = 'pending'
                ORDER BY priority DESC, created_at ASC
                LIMIT $1
            """
            
            async with self.get_connection() as conn:
                rows = await conn.fetch(query, limit)
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get pending tasks: {e}")
            return []
    
    async def assign_task(self, task_id: str, agent_id: str) -> bool:
        """Assign task to agent atomically."""
        try:
            query = """
                UPDATE tasks 
                SET agent_id = $2, status = 'assigned', started_at = NOW()
                WHERE task_id = $1 AND status = 'pending'
            """
            
            async with self.get_connection() as conn:
                result = await conn.execute(query, uuid.UUID(task_id), agent_id)
            
            rows_affected = int(result.split()[-1])
            return rows_affected > 0
            
        except Exception as e:
            logger.error(f"Failed to assign task {task_id} to {agent_id}: {e}")
            return False
    
    # System Monitoring
    async def create_system_snapshot(self) -> bool:
        """Create system snapshot with aggregated metrics."""
        try:
            query = """
                WITH agent_stats AS (
                    SELECT 
                        COUNT(*) as total_agents,
                        COUNT(*) FILTER (WHERE status IN ('idle', 'busy')) as active_agents,
                        AVG(context_usage) as avg_context_usage
                    FROM agents
                ),
                task_stats AS (
                    SELECT 
                        COUNT(*) as total_tasks,
                        COUNT(*) FILTER (WHERE status = 'completed') as completed_tasks,
                        COUNT(*) FILTER (WHERE status = 'failed') as failed_tasks
                    FROM tasks
                )
                INSERT INTO system_snapshots (
                    total_agents, active_agents, total_tasks, 
                    completed_tasks, failed_tasks, average_context_usage
                )
                SELECT 
                    a.total_agents, a.active_agents, t.total_tasks,
                    t.completed_tasks, t.failed_tasks, a.avg_context_usage
                FROM agent_stats a, task_stats t
            """
            
            async with self.get_connection() as conn:
                await conn.execute(query)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create system snapshot: {e}")
            return False
    
    async def create_checkpoint(self, checkpoint_data: Dict[str, Any]) -> str:
        """Create system checkpoint with JSON data."""
        try:
            checkpoint_name = checkpoint_data.get('name', f"checkpoint_{datetime.now().isoformat()}")
            
            query = """
                INSERT INTO checkpoints (checkpoint_name, data)
                VALUES ($1, $2)
                RETURNING id
            """
            
            async with self.get_connection() as conn:
                checkpoint_id = await conn.fetchval(
                    query,
                    checkpoint_name,
                    json.dumps(checkpoint_data)
                )
            
            return str(checkpoint_id)
            
        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            return ""
    
    # Performance and Health Checks
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            health_data = {
                "timestamp": datetime.now().isoformat(),
                "database_connected": False,
                "pool_status": {},
                "query_performance": {}
            }
            
            # Test connection
            start_time = datetime.now()
            async with self.get_connection() as conn:
                await conn.fetchval("SELECT 1")
                health_data["database_connected"] = True
                
                # Pool status
                health_data["pool_status"] = {
                    "size": self.pool.get_size(),
                    "min_size": self.pool.get_min_size(),
                    "max_size": self.pool.get_max_size(),
                    "idle_connections": self.pool.get_idle_size()
                }
                
                # Query performance test
                query_start = datetime.now()
                await conn.fetchval("SELECT COUNT(*) FROM agents")
                query_time = (datetime.now() - query_start).total_seconds() * 1000
                
                health_data["query_performance"] = {
                    "simple_query_ms": query_time,
                    "connection_acquire_ms": (query_start - start_time).total_seconds() * 1000
                }
            
            return health_data
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "database_connected": False,
                "error": str(e)
            }
    
    # Batch Operations for Performance
    async def batch_update_agents(self, updates: List[Dict[str, Any]]) -> int:
        """Batch update multiple agents for performance."""
        if not updates:
            return 0
        
        try:
            async with self.get_connection() as conn:
                async with conn.transaction():
                    updated_count = 0
                    for update in updates:
                        result = await conn.execute("""
                            UPDATE agents 
                            SET status = COALESCE($2, status),
                                context_usage = COALESCE($3, context_usage),
                                last_activity = NOW()
                            WHERE agent_id = $1
                        """, 
                        update['agent_id'],
                        update.get('status'),
                        update.get('context_usage')
                        )
                        updated_count += int(result.split()[-1])
                    
                    return updated_count
                    
        except Exception as e:
            logger.error(f"Batch update failed: {e}")
            return 0


# Factory Functions
async def create_postgresql_manager(config: Optional[PostgreSQLConfig] = None) -> PostgreSQLStateManager:
    """Factory function to create and initialize PostgreSQL state manager."""
    if config is None:
        config = PostgreSQLConfig()
    
    manager = PostgreSQLStateManager(config)
    await manager.initialize()
    return manager