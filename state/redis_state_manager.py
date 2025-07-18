"""
Redis State Manager - High-performance ephemeral state and event queue management

Handles caching, session state, and Redis Streams for event-driven architecture.
"""

import asyncio
import redis.asyncio as aioredis
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, AsyncGenerator
from dataclasses import dataclass
import uuid

logger = logging.getLogger(__name__)


@dataclass
class RedisConfig:
    """Configuration for Redis connection and behavior."""
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: Optional[str] = None

    # Connection Pool Settings
    max_connections: int = 20
    retry_on_timeout: bool = True
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0

    # Cache Settings
    default_ttl: int = 3600  # 1 hour
    max_memory_policy: str = "allkeys-lru"

    # Stream Settings
    stream_maxlen: int = 10000
    consumer_timeout: int = 5000  # 5 seconds
    block_timeout: int = 1000     # 1 second


class RedisStateManager:
    """
    High-performance Redis-based state manager for caching, sessions,
    and event streams with connection pooling.
    """

    def __init__(self, config: RedisConfig):
        self.config = config
        self.redis: Optional[aioredis.Redis] = None
        self._initialized = False

        # Key prefixes for different data types
        self.prefixes = {
            "agent_state": "agent:state:",
            "task_cache": "task:cache:",
            "coordination": "coord:",
            "session": "session:",
            "metrics": "metrics:",
            "stream_task": "tasks:pending",
            "stream_events": "events:system",
            "stream_coord": "coord:events"
        }

    async def initialize(self) -> bool:
        """Initialize Redis connection pool and configure streams."""
        try:
            # Create Redis connection
            self.redis = aioredis.from_url(
                f"redis://{self.config.host}:{self.config.port}/{self.config.database}",
                password=self.config.password,
                max_connections=self.config.max_connections,
                retry_on_timeout=self.config.retry_on_timeout,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                decode_responses=True
            )

            # Test connection
            await self.redis.ping()

            # Configure Redis settings
            await self._configure_redis()

            # Initialize streams
            await self._initialize_streams()

            self._initialized = True
            logger.info("Redis state manager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Redis state manager: {e}")
            return False

    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            self._initialized = False

    def _ensure_initialized(self):
        """Ensure Redis is initialized."""
        if not self._initialized or not self.redis:
            raise RuntimeError("Redis state manager not initialized")

    async def _configure_redis(self):
        """Configure Redis for optimal performance."""
        try:
            # Set memory policy
            await self.redis.config_set("maxmemory-policy", self.config.max_memory_policy)

            # Enable keyspace notifications for expired keys (optional)
            await self.redis.config_set("notify-keyspace-events", "Ex")

        except Exception as e:
            logger.warning(f"Failed to configure Redis settings: {e}")

    async def _initialize_streams(self):
        """Initialize Redis Streams and consumer groups."""
        streams = [
            self.prefixes["stream_task"],
            self.prefixes["stream_events"],
            self.prefixes["stream_coord"]
        ]

        consumer_groups = {
            self.prefixes["stream_task"]: ["task_processors", "priority_processors"],
            self.prefixes["stream_events"]: ["monitoring", "analytics"],
            self.prefixes["stream_coord"]: ["coordinators"]
        }

        for stream in streams:
            try:
                # Create stream if it doesn't exist by adding a dummy message
                await self.redis.xadd(stream, {"_init": "true"}, maxlen=self.config.stream_maxlen)

                # Create consumer groups
                for group in consumer_groups.get(stream, []):
                    try:
                        await self.redis.xgroup_create(stream, group, id="0", mkstream=True)
                    except aioredis.exceptions.ResponseError as e:
                        if "BUSYGROUP" not in str(e):
                            raise

            except Exception as e:
                logger.warning(f"Failed to initialize stream {stream}: {e}")

    # Cache Operations
    async def set_agent_state(self, agent_id: str, state: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Cache agent state with TTL."""
        self._ensure_initialized()

        try:
            key = f"{self.prefixes['agent_state']}{agent_id}"
            value = json.dumps(state, default=str)

            if ttl is None:
                ttl = self.config.default_ttl

            await self.redis.setex(key, ttl, value)
            return True

        except Exception as e:
            logger.error(f"Failed to cache agent state for {agent_id}: {e}")
            return False

    async def get_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get cached agent state."""
        self._ensure_initialized()

        try:
            key = f"{self.prefixes['agent_state']}{agent_id}"
            value = await self.redis.get(key)

            if value:
                return json.loads(value)
            return None

        except Exception as e:
            logger.error(f"Failed to get cached agent state for {agent_id}: {e}")
            return None

    async def delete_agent_state(self, agent_id: str) -> bool:
        """Remove agent state from cache."""
        self._ensure_initialized()

        try:
            key = f"{self.prefixes['agent_state']}{agent_id}"
            result = await self.redis.delete(key)
            return result > 0

        except Exception as e:
            logger.error(f"Failed to delete cached agent state for {agent_id}: {e}")
            return False

    async def cache_task(self, task_id: str, task_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Cache task data."""
        self._ensure_initialized()

        try:
            key = f"{self.prefixes['task_cache']}{task_id}"
            value = json.dumps(task_data, default=str)

            if ttl is None:
                ttl = self.config.default_ttl // 2  # Tasks have shorter TTL

            await self.redis.setex(key, ttl, value)
            return True

        except Exception as e:
            logger.error(f"Failed to cache task {task_id}: {e}")
            return False

    async def get_cached_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get cached task data."""
        self._ensure_initialized()

        try:
            key = f"{self.prefixes['task_cache']}{task_id}"
            value = await self.redis.get(key)

            if value:
                return json.loads(value)
            return None

        except Exception as e:
            logger.error(f"Failed to get cached task {task_id}: {e}")
            return None

    # Session Management
    async def create_session(self, session_id: str, session_data: Dict[str, Any], ttl: int = 3600) -> bool:
        """Create a session with TTL."""
        self._ensure_initialized()

        try:
            key = f"{self.prefixes['session']}{session_id}"
            value = json.dumps(session_data, default=str)

            await self.redis.setex(key, ttl, value)
            return True

        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            return False

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        self._ensure_initialized()

        try:
            key = f"{self.prefixes['session']}{session_id}"
            value = await self.redis.get(key)

            if value:
                return json.loads(value)
            return None

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    async def extend_session(self, session_id: str, ttl: int = 3600) -> bool:
        """Extend session TTL."""
        self._ensure_initialized()

        try:
            key = f"{self.prefixes['session']}{session_id}"
            result = await self.redis.expire(key, ttl)
            return result

        except Exception as e:
            logger.error(f"Failed to extend session {session_id}: {e}")
            return False

    # Stream Operations for Event Queues
    async def queue_task(self, task: Dict[str, Any]) -> str:
        """Queue task using Redis Streams."""
        self._ensure_initialized()

        try:
            stream = self.prefixes["stream_task"]

            # Add timestamp and unique ID
            task_with_meta = {
                **task,
                "queued_at": datetime.now().isoformat(),
                "queue_id": str(uuid.uuid4())
            }

            # Convert dict values to strings for Redis
            stream_data = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                          for k, v in task_with_meta.items()}

            message_id = await self.redis.xadd(
                stream,
                stream_data,
                maxlen=self.config.stream_maxlen
            )

            return message_id

        except Exception as e:
            logger.error(f"Failed to queue task: {e}")
            return ""

    async def consume_tasks(self, consumer_group: str, consumer_name: str,
                           count: int = 1) -> List[Dict[str, Any]]:
        """Consume tasks from Redis Stream."""
        self._ensure_initialized()

        try:
            stream = self.prefixes["stream_task"]

            # Read from consumer group
            messages = await self.redis.xreadgroup(
                consumer_group,
                consumer_name,
                {stream: ">"},
                count=count,
                block=self.config.block_timeout
            )

            tasks = []
            for stream_name, stream_messages in messages:
                for message_id, fields in stream_messages:
                    # Parse the message
                    task_data = {}
                    for key, value in fields.items():
                        try:
                            # Try to parse as JSON first
                            task_data[key] = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            # Fall back to string
                            task_data[key] = value

                    task_data["message_id"] = message_id
                    task_data["stream"] = stream_name
                    tasks.append(task_data)

            return tasks

        except Exception as e:
            logger.error(f"Failed to consume tasks: {e}")
            return []

    async def acknowledge_task(self, consumer_group: str, message_id: str) -> bool:
        """Acknowledge task completion."""
        self._ensure_initialized()

        try:
            stream = self.prefixes["stream_task"]
            result = await self.redis.xack(stream, consumer_group, message_id)
            return result > 0

        except Exception as e:
            logger.error(f"Failed to acknowledge task {message_id}: {e}")
            return False

    async def publish_event(self, event: Dict[str, Any]) -> str:
        """Publish system event to stream."""
        self._ensure_initialized()

        try:
            stream = self.prefixes["stream_events"]

            # Add metadata
            event_with_meta = {
                **event,
                "published_at": datetime.now().isoformat(),
                "event_id": str(uuid.uuid4())
            }

            # Convert to strings for Redis
            stream_data = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                          for k, v in event_with_meta.items()}

            message_id = await self.redis.xadd(
                stream,
                stream_data,
                maxlen=self.config.stream_maxlen
            )

            return message_id

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return ""

    async def consume_events(self, consumer_group: str, consumer_name: str,
                            count: int = 10) -> List[Dict[str, Any]]:
        """Consume events from Redis Stream."""
        self._ensure_initialized()

        try:
            stream = self.prefixes["stream_events"]

            messages = await self.redis.xreadgroup(
                consumer_group,
                consumer_name,
                {stream: ">"},
                count=count,
                block=self.config.block_timeout
            )

            events = []
            for stream_name, stream_messages in messages:
                for message_id, fields in stream_messages:
                    event_data = {}
                    for key, value in fields.items():
                        try:
                            event_data[key] = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            event_data[key] = value

                    event_data["message_id"] = message_id
                    event_data["stream"] = stream_name
                    events.append(event_data)

            return events

        except Exception as e:
            logger.error(f"Failed to consume events: {e}")
            return []

    # Coordination State Management
    async def set_coordination_state(self, operation_id: str, state: Dict[str, Any],
                                   ttl: int = 300) -> bool:
        """Set coordination state with short TTL."""
        self._ensure_initialized()

        try:
            key = f"{self.prefixes['coordination']}{operation_id}"
            value = json.dumps(state, default=str)

            await self.redis.setex(key, ttl, value)
            return True

        except Exception as e:
            logger.error(f"Failed to set coordination state for {operation_id}: {e}")
            return False

    async def get_coordination_state(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get coordination state."""
        self._ensure_initialized()

        try:
            key = f"{self.prefixes['coordination']}{operation_id}"
            value = await self.redis.get(key)

            if value:
                return json.loads(value)
            return None

        except Exception as e:
            logger.error(f"Failed to get coordination state for {operation_id}: {e}")
            return None

    # Metrics and Monitoring
    async def increment_metric(self, metric_name: str, value: int = 1) -> int:
        """Increment a metric counter."""
        self._ensure_initialized()

        try:
            key = f"{self.prefixes['metrics']}{metric_name}"
            result = await self.redis.incrby(key, value)

            # Set TTL for automatic cleanup (24 hours)
            await self.redis.expire(key, 86400)

            return result

        except Exception as e:
            logger.error(f"Failed to increment metric {metric_name}: {e}")
            return 0

    async def get_metric(self, metric_name: str) -> int:
        """Get metric value."""
        self._ensure_initialized()

        try:
            key = f"{self.prefixes['metrics']}{metric_name}"
            result = await self.redis.get(key)
            return int(result) if result else 0

        except Exception as e:
            logger.error(f"Failed to get metric {metric_name}: {e}")
            return 0

    # Batch Operations
    async def batch_cache_agents(self, agents: Dict[str, Dict[str, Any]],
                                ttl: Optional[int] = None) -> int:
        """Batch cache multiple agent states."""
        self._ensure_initialized()

        if not agents:
            return 0

        try:
            pipe = self.redis.pipeline()

            if ttl is None:
                ttl = self.config.default_ttl

            for agent_id, state in agents.items():
                key = f"{self.prefixes['agent_state']}{agent_id}"
                value = json.dumps(state, default=str)
                pipe.setex(key, ttl, value)

            results = await pipe.execute()
            return sum(1 for r in results if r)

        except Exception as e:
            logger.error(f"Failed to batch cache agents: {e}")
            return 0

    # Health Check
    async def health_check(self) -> Dict[str, Any]:
        """Perform Redis health check."""
        try:
            health_data = {
                "timestamp": datetime.now().isoformat(),
                "redis_connected": False,
                "latency_ms": 0,
                "memory_usage": {},
                "stream_info": {}
            }

            # Test connection and measure latency
            start_time = datetime.now()
            await self.redis.ping()
            latency = (datetime.now() - start_time).total_seconds() * 1000

            health_data["redis_connected"] = True
            health_data["latency_ms"] = latency

            # Get memory info
            memory_info = await self.redis.info("memory")
            health_data["memory_usage"] = {
                "used_memory": memory_info.get("used_memory", 0),
                "used_memory_human": memory_info.get("used_memory_human", "0B"),
                "max_memory": memory_info.get("maxmemory", 0)
            }

            # Get stream info
            for stream_name in [self.prefixes["stream_task"], self.prefixes["stream_events"]]:
                try:
                    stream_info = await self.redis.xinfo_stream(stream_name)
                    health_data["stream_info"][stream_name] = {
                        "length": stream_info.get("length", 0),
                        "groups": stream_info.get("groups", 0)
                    }
                except Exception:
                    health_data["stream_info"][stream_name] = {"error": "stream_not_found"}

            return health_data

        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "redis_connected": False,
                "error": str(e)
            }


# Factory Functions
async def create_redis_manager(config: Optional[RedisConfig] = None) -> RedisStateManager:
    """Factory function to create and initialize Redis state manager."""
    if config is None:
        config = RedisConfig()

    manager = RedisStateManager(config)
    await manager.initialize()
    return manager
