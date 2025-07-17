"""
Hybrid State Manager - Orchestrates PostgreSQL + Redis for optimal performance

Provides a unified interface that routes operations to the appropriate storage layer
based on consistency requirements and performance characteristics.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

from .postgresql_state_manager import PostgreSQLStateManager, PostgreSQLConfig
from .redis_state_manager import RedisStateManager, RedisConfig
from .distributed_state_architecture import StateManagerProtocol, ConsistencyLevel

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Defines caching strategies for different operations."""
    CACHE_FIRST = "cache_first"        # Try cache first, fallback to DB
    WRITE_THROUGH = "write_through"    # Write to both cache and DB
    WRITE_BEHIND = "write_behind"      # Write to cache first, DB async
    DB_ONLY = "db_only"               # Skip cache, use DB directly


@dataclass
class HybridConfig:
    """Configuration for hybrid state management."""
    postgresql_config: PostgreSQLConfig
    redis_config: RedisConfig
    
    # Performance tuning
    cache_agent_state: bool = True
    cache_task_data: bool = True
    agent_cache_ttl: int = 3600
    task_cache_ttl: int = 1800
    
    # Consistency settings
    strong_consistency_operations: List[str] = None
    eventual_consistency_operations: List[str] = None
    
    # Performance targets
    max_cache_latency_ms: float = 10.0
    max_db_latency_ms: float = 50.0
    cache_hit_ratio_target: float = 0.95
    
    def __post_init__(self):
        if self.strong_consistency_operations is None:
            self.strong_consistency_operations = [
                "register_agent", "create_task", "assign_task", 
                "create_checkpoint", "create_system_snapshot"
            ]
        
        if self.eventual_consistency_operations is None:
            self.eventual_consistency_operations = [
                "update_agent_state", "cache_task", "publish_event",
                "increment_metric"
            ]


class HybridStateManager(StateManagerProtocol):
    """
    High-performance hybrid state manager that combines PostgreSQL and Redis
    for optimal performance and consistency guarantees.
    """
    
    def __init__(self, config: HybridConfig):
        self.config = config
        self.postgresql: Optional[PostgreSQLStateManager] = None
        self.redis: Optional[RedisStateManager] = None
        self._initialized = False
        
        # Performance tracking
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "write_operations": 0,
            "read_operations": 0,
            "average_latency": 0.0
        }
    
    async def initialize(self) -> bool:
        """Initialize both PostgreSQL and Redis managers."""
        try:
            # Initialize PostgreSQL
            self.postgresql = PostgreSQLStateManager(self.config.postgresql_config)
            if not await self.postgresql.initialize():
                logger.error("Failed to initialize PostgreSQL manager")
                return False
            
            # Initialize Redis
            self.redis = RedisStateManager(self.config.redis_config)
            if not await self.redis.initialize():
                logger.error("Failed to initialize Redis manager")
                return False
            
            self._initialized = True
            logger.info("Hybrid state manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize hybrid state manager: {e}")
            return False
    
    async def close(self):
        """Close both connections."""
        if self.postgresql:
            await self.postgresql.close()
        if self.redis:
            await self.redis.close()
        self._initialized = False
    
    def _ensure_initialized(self):
        """Ensure both managers are initialized."""
        if not self._initialized or not self.postgresql or not self.redis:
            raise RuntimeError("Hybrid state manager not initialized")
    
    def _should_use_cache(self, operation: str) -> bool:
        """Determine if operation should use caching."""
        if operation in self.config.strong_consistency_operations:
            return False
        return True
    
    def _get_cache_strategy(self, operation: str) -> CacheStrategy:
        """Determine caching strategy for operation."""
        if operation in self.config.strong_consistency_operations:
            return CacheStrategy.DB_ONLY
        elif operation in self.config.eventual_consistency_operations:
            return CacheStrategy.WRITE_THROUGH
        else:
            return CacheStrategy.CACHE_FIRST
    
    # Agent State Management with Intelligent Caching
    async def register_agent(self, agent_id: str, capabilities: Optional[List[str]] = None) -> bool:
        """Register agent with strong consistency (PostgreSQL only)."""
        self._ensure_initialized()
        
        try:
            # Strong consistency - write to PostgreSQL first
            success = await self.postgresql.register_agent(agent_id, capabilities)
            
            if success and self.config.cache_agent_state:
                # Cache the agent state for future reads
                agent_state = await self.postgresql.get_agent_state(agent_id)
                if agent_state:
                    await self.redis.set_agent_state(
                        agent_id, 
                        agent_state, 
                        self.config.agent_cache_ttl
                    )
            
            self._stats["write_operations"] += 1
            return success
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False
    
    async def get_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent state with cache-first strategy."""
        self._ensure_initialized()
        
        start_time = datetime.now()
        
        try:
            # Try cache first if caching is enabled
            if self.config.cache_agent_state:
                cached_state = await self.redis.get_agent_state(agent_id)
                if cached_state:
                    self._stats["cache_hits"] += 1
                    self._stats["read_operations"] += 1
                    return cached_state
                
                self._stats["cache_misses"] += 1
            
            # Fallback to PostgreSQL
            db_state = await self.postgresql.get_agent_state(agent_id)
            
            # Cache the result for future reads
            if db_state and self.config.cache_agent_state:
                await self.redis.set_agent_state(
                    agent_id, 
                    db_state, 
                    self.config.agent_cache_ttl
                )
            
            self._stats["read_operations"] += 1
            return db_state
            
        except Exception as e:
            logger.error(f"Failed to get agent state for {agent_id}: {e}")
            return None
        finally:
            # Track latency
            latency = (datetime.now() - start_time).total_seconds() * 1000
            self._update_latency_stats(latency)
    
    async def update_agent_state(self, agent_id: str, state: Dict[str, Any]) -> bool:
        """Update agent state with write-through caching."""
        self._ensure_initialized()
        
        try:
            strategy = self._get_cache_strategy("update_agent_state")
            
            if strategy == CacheStrategy.WRITE_THROUGH:
                # Write to both PostgreSQL and Redis
                db_success = await self.postgresql.update_agent_state(agent_id, state)
                
                if db_success and self.config.cache_agent_state:
                    # Update cache with the new state
                    full_state = await self.postgresql.get_agent_state(agent_id)
                    if full_state:
                        await self.redis.set_agent_state(
                            agent_id, 
                            full_state, 
                            self.config.agent_cache_ttl
                        )
                
                self._stats["write_operations"] += 1
                return db_success
            
            else:
                # Direct PostgreSQL write
                result = await self.postgresql.update_agent_state(agent_id, state)
                self._stats["write_operations"] += 1
                return result
                
        except Exception as e:
            logger.error(f"Failed to update agent state for {agent_id}: {e}")
            return False
    
    async def get_active_agents(self) -> List[Dict[str, Any]]:
        """Get active agents from PostgreSQL (real-time data)."""
        self._ensure_initialized()
        
        try:
            # Always get real-time data for active agents
            agents = await self.postgresql.get_active_agents()
            self._stats["read_operations"] += 1
            return agents
            
        except Exception as e:
            logger.error(f"Failed to get active agents: {e}")
            return []
    
    # Task Management with Hybrid Storage
    async def create_task(self, task_data: Dict[str, Any]) -> Optional[str]:
        """Create task with strong consistency (PostgreSQL)."""
        self._ensure_initialized()
        
        try:
            # Strong consistency - PostgreSQL first
            task_id = await self.postgresql.create_task(task_data)
            
            if task_id and self.config.cache_task_data:
                # Cache task for quick retrieval
                task_with_id = {**task_data, "task_id": task_id}
                await self.redis.cache_task(task_id, task_with_id, self.config.task_cache_ttl)
            
            self._stats["write_operations"] += 1
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return None
    
    async def queue_task(self, task: Dict[str, Any]) -> str:
        """Queue task using Redis Streams for high throughput."""
        self._ensure_initialized()
        
        try:
            # Use Redis Streams for task queuing
            message_id = await self.redis.queue_task(task)
            self._stats["write_operations"] += 1
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to queue task: {e}")
            return ""
    
    async def consume_tasks(self, consumer_group: str, consumer_name: str = None, 
                           count: int = 1) -> List[Dict[str, Any]]:
        """Consume tasks from Redis Streams."""
        self._ensure_initialized()
        
        try:
            if consumer_name is None:
                consumer_name = f"consumer_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            tasks = await self.redis.consume_tasks(consumer_group, consumer_name, count)
            self._stats["read_operations"] += 1
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to consume tasks: {e}")
            return []
    
    async def get_pending_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending tasks from PostgreSQL."""
        self._ensure_initialized()
        
        try:
            tasks = await self.postgresql.get_pending_tasks(limit)
            self._stats["read_operations"] += 1
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to get pending tasks: {e}")
            return []
    
    async def assign_task(self, task_id: str, agent_id: str) -> bool:
        """Assign task with strong consistency (PostgreSQL)."""
        self._ensure_initialized()
        
        try:
            # Strong consistency operation
            success = await self.postgresql.assign_task(task_id, agent_id)
            
            # Invalidate cache if task was cached
            if success and self.config.cache_task_data:
                await self.redis.delete_cached_task(task_id)
            
            self._stats["write_operations"] += 1
            return success
            
        except Exception as e:
            logger.error(f"Failed to assign task {task_id} to {agent_id}: {e}")
            return False
    
    # System Monitoring and Checkpoints
    async def create_system_snapshot(self) -> bool:
        """Create system snapshot in PostgreSQL."""
        self._ensure_initialized()
        
        try:
            success = await self.postgresql.create_system_snapshot()
            self._stats["write_operations"] += 1
            return success
            
        except Exception as e:
            logger.error(f"Failed to create system snapshot: {e}")
            return False
    
    async def create_checkpoint(self, checkpoint_data: Dict[str, Any]) -> str:
        """Create checkpoint in PostgreSQL."""
        self._ensure_initialized()
        
        try:
            checkpoint_id = await self.postgresql.create_checkpoint(checkpoint_data)
            self._stats["write_operations"] += 1
            return checkpoint_id
            
        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            return ""
    
    # Event and Coordination Management
    async def publish_event(self, event: Dict[str, Any]) -> str:
        """Publish event to Redis Streams."""
        self._ensure_initialized()
        
        try:
            message_id = await self.redis.publish_event(event)
            self._stats["write_operations"] += 1
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return ""
    
    async def consume_events(self, consumer_group: str, consumer_name: str = None,
                            count: int = 10) -> List[Dict[str, Any]]:
        """Consume events from Redis Streams."""
        self._ensure_initialized()
        
        try:
            if consumer_name is None:
                consumer_name = f"event_consumer_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            events = await self.redis.consume_events(consumer_group, consumer_name, count)
            self._stats["read_operations"] += 1
            return events
            
        except Exception as e:
            logger.error(f"Failed to consume events: {e}")
            return []
    
    async def set_coordination_state(self, operation_id: str, state: Dict[str, Any], 
                                   ttl: int = 300) -> bool:
        """Set coordination state in Redis."""
        self._ensure_initialized()
        
        try:
            success = await self.redis.set_coordination_state(operation_id, state, ttl)
            self._stats["write_operations"] += 1
            return success
            
        except Exception as e:
            logger.error(f"Failed to set coordination state: {e}")
            return False
    
    async def get_coordination_state(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get coordination state from Redis."""
        self._ensure_initialized()
        
        try:
            state = await self.redis.get_coordination_state(operation_id)
            self._stats["read_operations"] += 1
            return state
            
        except Exception as e:
            logger.error(f"Failed to get coordination state: {e}")
            return None
    
    # Performance Monitoring
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        total_reads = self._stats["cache_hits"] + self._stats["cache_misses"]
        cache_hit_ratio = self._stats["cache_hits"] / total_reads if total_reads > 0 else 0
        
        return {
            "cache_hit_ratio": cache_hit_ratio,
            "cache_hits": self._stats["cache_hits"],
            "cache_misses": self._stats["cache_misses"],
            "total_reads": self._stats["read_operations"],
            "total_writes": self._stats["write_operations"],
            "average_latency_ms": self._stats["average_latency"],
            "cache_hit_ratio_target": self.config.cache_hit_ratio_target,
            "performance_ok": cache_hit_ratio >= self.config.cache_hit_ratio_target
        }
    
    def _update_latency_stats(self, latency_ms: float):
        """Update rolling average latency."""
        if self._stats["average_latency"] == 0:
            self._stats["average_latency"] = latency_ms
        else:
            # Simple exponential moving average
            self._stats["average_latency"] = (
                0.9 * self._stats["average_latency"] + 0.1 * latency_ms
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for both systems."""
        try:
            health_data = {
                "timestamp": datetime.now().isoformat(),
                "hybrid_manager_ok": True,
                "postgresql": {},
                "redis": {},
                "performance": self.get_performance_stats()
            }
            
            # Check PostgreSQL health
            if self.postgresql:
                health_data["postgresql"] = await self.postgresql.health_check()
            
            # Check Redis health  
            if self.redis:
                health_data["redis"] = await self.redis.health_check()
            
            # Overall health assessment
            pg_ok = health_data["postgresql"].get("database_connected", False)
            redis_ok = health_data["redis"].get("redis_connected", False)
            perf_ok = health_data["performance"]["performance_ok"]
            
            health_data["hybrid_manager_ok"] = pg_ok and redis_ok and perf_ok
            
            return health_data
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "hybrid_manager_ok": False,
                "error": str(e)
            }
    
    # Batch Operations for Performance
    async def batch_update_agents(self, updates: List[Dict[str, Any]]) -> int:
        """Batch update agents in PostgreSQL with cache invalidation."""
        self._ensure_initialized()
        
        try:
            # Update in PostgreSQL
            updated_count = await self.postgresql.batch_update_agents(updates)
            
            # Invalidate cache for updated agents
            if updated_count > 0 and self.config.cache_agent_state:
                for update in updates:
                    agent_id = update.get("agent_id")
                    if agent_id:
                        await self.redis.delete_agent_state(agent_id)
            
            self._stats["write_operations"] += updated_count
            return updated_count
            
        except Exception as e:
            logger.error(f"Batch update failed: {e}")
            return 0


# Factory Functions
async def create_hybrid_manager(
    postgresql_config: Optional[PostgreSQLConfig] = None,
    redis_config: Optional[RedisConfig] = None
) -> HybridStateManager:
    """Factory function to create and initialize hybrid state manager."""
    
    if postgresql_config is None:
        postgresql_config = PostgreSQLConfig()
    
    if redis_config is None:
        redis_config = RedisConfig()
    
    hybrid_config = HybridConfig(
        postgresql_config=postgresql_config,
        redis_config=redis_config
    )
    
    manager = HybridStateManager(hybrid_config)
    await manager.initialize()
    return manager