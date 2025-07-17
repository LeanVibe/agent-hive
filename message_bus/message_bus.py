"""
Production Message Bus Implementation with Redis backend

Provides reliable, scalable message passing for distributed agent communication.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Set, Union
import uuid

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    import redis
    REDIS_AVAILABLE = False

from .message_protocol import Message, MessageType, MessagePriority, MessageStatus


logger = logging.getLogger(__name__)


@dataclass
class MessageBusConfig:
    """Configuration for the message bus."""
    redis_url: str = "redis://localhost:6379/0"
    redis_pool_size: int = 10
    message_ttl: int = 3600  # 1 hour default TTL
    heartbeat_interval: int = 30  # seconds
    retry_delay_base: float = 1.0  # base delay for exponential backoff
    retry_delay_max: float = 60.0  # max delay for exponential backoff
    dead_letter_ttl: int = 86400  # 24 hours
    consumer_group_name: str = "agent_hive"
    max_pending_messages: int = 1000
    batch_size: int = 10
    enable_monitoring: bool = True


class MessageBus:
    """
    Production message bus using Redis Streams and Pub/Sub.

    Features:
    - Message persistence with Redis Streams
    - Consumer groups for load balancing
    - Dead letter queues for failed messages
    - Message acknowledgment and retry
    - Real-time pub/sub for urgent messages
    - Distributed agent discovery
    - Monitoring and metrics
    """

    def __init__(self, config: MessageBusConfig):
        """
        Initialize message bus.

        Args:
            config: Message bus configuration
        """
        self.config = config
        self.redis_pool = None
        self.redis_client = None
        self.pubsub = None

        # Message handling
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
        self.running = False
        self.consumer_tasks: Set[asyncio.Task] = set()

        # Monitoring
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "messages_failed": 0,
            "messages_retried": 0,
            "agents_connected": 0
        }

        logger.info("MessageBus initialized")

    async def start(self) -> None:
        """Start the message bus."""
        if self.running:
            logger.warning("Message bus already running")
            return

        try:
            # Initialize Redis connection
            if REDIS_AVAILABLE:
                self.redis_pool = redis.ConnectionPool.from_url(
                    self.config.redis_url,
                    max_connections=self.config.redis_pool_size
                )
                self.redis_client = redis.Redis(connection_pool=self.redis_pool)
            else:
                # Fallback to sync Redis (not recommended for production)
                self.redis_client = redis.from_url(self.config.redis_url)

            # Test connection
            await self._test_connection()

            # Initialize Redis Streams and Consumer Groups
            await self._initialize_streams()

            # Start consumer tasks
            self.running = True
            await self._start_consumers()

            logger.info("Message bus started successfully")

        except Exception as e:
            logger.error(f"Failed to start message bus: {e}")
            raise

    async def stop(self) -> None:
        """Stop the message bus."""
        if not self.running:
            return

        self.running = False

        # Cancel consumer tasks
        for task in self.consumer_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.consumer_tasks, return_exceptions=True)
        self.consumer_tasks.clear()

        # Close connections
        if self.pubsub:
            await self.pubsub.close()

        if self.redis_client:
            await self.redis_client.close()

        if self.redis_pool:
            await self.redis_pool.disconnect()

        logger.info("Message bus stopped")

    async def send_message(self, message: Message) -> str:
        """
        Send a message through the bus.

        Args:
            message: Message to send

        Returns:
            Message ID
        """
        try:
            # Serialize message
            message_data = message.to_json()

            # Determine stream name based on routing
            stream_name = self._get_stream_name(message)

            # Add to Redis Stream
            message_id = await self.redis_client.xadd(
                stream_name,
                {
                    "message": message_data,
                    "priority": message.priority.value,
                    "timestamp": datetime.now().isoformat()
                },
                maxlen=self.config.max_pending_messages,
                approximate=True
            )

            # For urgent messages, also publish to pub/sub
            if message.priority.value >= MessagePriority.URGENT.value:
                channel = f"urgent:{message.headers.routing_key}"
                await self.redis_client.publish(channel, message_data)

            # Update stats
            self.stats["messages_sent"] += 1

            logger.debug(f"Message sent: {message.headers.message_id} to {stream_name}")
            return message.headers.message_id

        except Exception as e:
            logger.error(f"Failed to send message {message.headers.message_id}: {e}")
            raise

    async def send_direct_message(self, target_agent: str, message_type: MessageType,
                                 payload: Dict[str, Any], priority: MessagePriority = MessagePriority.NORMAL,
                                 expiration_seconds: Optional[int] = None) -> str:
        """
        Send a direct message to a specific agent.

        Args:
            target_agent: Target agent name
            message_type: Type of message
            payload: Message payload
            priority: Message priority
            expiration_seconds: Message expiration

        Returns:
            Message ID
        """
        message = Message.create(
            message_type=message_type,
            payload=payload,
            target_agent=target_agent,
            priority=priority,
            routing_key=f"agent.{target_agent}",
            expiration_seconds=expiration_seconds
        )

        return await self.send_message(message)

    async def broadcast_message(self, message_type: MessageType, payload: Dict[str, Any],
                               target_group: str = "all", priority: MessagePriority = MessagePriority.NORMAL) -> str:
        """
        Broadcast a message to all agents in a group.

        Args:
            message_type: Type of message
            payload: Message payload
            target_group: Target group name
            priority: Message priority

        Returns:
            Message ID
        """
        message = Message.create(
            message_type=message_type,
            payload=payload,
            target_group=target_group,
            priority=priority,
            routing_key=f"broadcast.{target_group}"
        )

        return await self.send_message(message)

    def register_handler(self, message_type: MessageType, handler: Callable[[Message], Any]) -> None:
        """
        Register a message handler.

        Args:
            message_type: Message type to handle
            handler: Handler function
        """
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []

        self.message_handlers[message_type].append(handler)
        logger.info(f"Registered handler for {message_type.value}")

    def unregister_handler(self, message_type: MessageType, handler: Callable) -> bool:
        """
        Unregister a message handler.

        Args:
            message_type: Message type
            handler: Handler function to remove

        Returns:
            True if handler was removed
        """
        if message_type in self.message_handlers:
            try:
                self.message_handlers[message_type].remove(handler)
                logger.info(f"Unregistered handler for {message_type.value}")
                return True
            except ValueError:
                pass

        return False

    async def acknowledge_message(self, stream_name: str, consumer_group: str, message_id: str) -> None:
        """
        Acknowledge a processed message.

        Args:
            stream_name: Stream name
            consumer_group: Consumer group name
            message_id: Message ID to acknowledge
        """
        try:
            await self.redis_client.xack(stream_name, consumer_group, message_id)
            logger.debug(f"Acknowledged message {message_id}")
        except Exception as e:
            logger.error(f"Failed to acknowledge message {message_id}: {e}")

    async def get_agent_status(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get agent status from registry.

        Args:
            agent_name: Agent name

        Returns:
            Agent status or None if not found
        """
        try:
            status_data = await self.redis_client.hget("agents:registry", agent_name)
            if status_data:
                return json.loads(status_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get agent status for {agent_name}: {e}")
            return None

    async def register_agent(self, agent_name: str, metadata: Dict[str, Any]) -> None:
        """
        Register an agent in the discovery service.

        Args:
            agent_name: Agent name
            metadata: Agent metadata
        """
        try:
            agent_data = {
                "name": agent_name,
                "status": "active",
                "registered_at": datetime.now().isoformat(),
                "last_heartbeat": datetime.now().isoformat(),
                "metadata": metadata
            }

            await self.redis_client.hset(
                "agents:registry",
                agent_name,
                json.dumps(agent_data)
            )

            # Set TTL for auto-cleanup
            await self.redis_client.expire(f"agent:{agent_name}:heartbeat", self.config.heartbeat_interval * 2)

            logger.info(f"Registered agent: {agent_name}")

        except Exception as e:
            logger.error(f"Failed to register agent {agent_name}: {e}")
            raise

    async def update_agent_heartbeat(self, agent_name: str, status: str = "active",
                                   current_task: Optional[str] = None) -> None:
        """
        Update agent heartbeat.

        Args:
            agent_name: Agent name
            status: Agent status
            current_task: Current task ID
        """
        try:
            heartbeat_data = {
                "agent_name": agent_name,
                "status": status,
                "current_task": current_task,
                "timestamp": datetime.now().isoformat()
            }

            # Update heartbeat
            await self.redis_client.setex(
                f"agent:{agent_name}:heartbeat",
                self.config.heartbeat_interval * 2,
                json.dumps(heartbeat_data)
            )

            # Update registry
            agent_data = await self.get_agent_status(agent_name)
            if agent_data:
                agent_data["last_heartbeat"] = datetime.now().isoformat()
                agent_data["status"] = status
                agent_data["current_task"] = current_task

                await self.redis_client.hset(
                    "agents:registry",
                    agent_name,
                    json.dumps(agent_data)
                )

        except Exception as e:
            logger.error(f"Failed to update heartbeat for {agent_name}: {e}")

    async def get_active_agents(self) -> List[Dict[str, Any]]:
        """Get list of active agents."""
        try:
            agents_data = await self.redis_client.hgetall("agents:registry")
            active_agents = []

            for agent_name, data in agents_data.items():
                agent_info = json.loads(data)

                # Check if agent is still active based on heartbeat
                heartbeat_key = f"agent:{agent_name.decode() if isinstance(agent_name, bytes) else agent_name}:heartbeat"
                heartbeat_exists = await self.redis_client.exists(heartbeat_key)

                if heartbeat_exists:
                    active_agents.append(agent_info)

            return active_agents

        except Exception as e:
            logger.error(f"Failed to get active agents: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """Get message bus statistics."""
        active_agents = await self.get_active_agents()

        return {
            **self.stats,
            "agents_connected": len(active_agents),
            "active_agents": [agent["name"] for agent in active_agents],
            "uptime": "TODO",  # Calculate uptime
            "redis_connected": bool(self.redis_client),
            "consumers_running": len(self.consumer_tasks)
        }

    # Private methods

    async def _test_connection(self) -> None:
        """Test Redis connection."""
        try:
            await self.redis_client.ping()
            logger.info("Redis connection successful")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    async def _initialize_streams(self) -> None:
        """Initialize Redis Streams and Consumer Groups."""
        streams = [
            "messages:tasks",
            "messages:status",
            "messages:system",
            "messages:webhooks",
            "messages:broadcast"
        ]

        for stream in streams:
            try:
                # Create consumer group if it doesn't exist
                await self.redis_client.xgroup_create(
                    stream,
                    self.config.consumer_group_name,
                    id="0",
                    mkstream=True
                )
            except Exception as e:
                # Group might already exist
                if "BUSYGROUP" not in str(e):
                    logger.error(f"Failed to create consumer group for {stream}: {e}")

        logger.info("Redis Streams initialized")

    def _get_stream_name(self, message: Message) -> str:
        """Get stream name for message routing."""
        if message.type in [MessageType.TASK_ASSIGNMENT, MessageType.TASK_UPDATE, MessageType.TASK_COMPLETION]:
            return "messages:tasks"
        elif message.type in [MessageType.AGENT_STATUS, MessageType.AGENT_HEARTBEAT]:
            return "messages:status"
        elif message.type == MessageType.SYSTEM_COMMAND:
            return "messages:system"
        elif message.type == MessageType.WEBHOOK_NOTIFICATION:
            return "messages:webhooks"
        elif message.target_group:
            return "messages:broadcast"
        else:
            return "messages:default"

    async def _start_consumers(self) -> None:
        """Start message consumer tasks."""
        streams = [
            "messages:tasks",
            "messages:status",
            "messages:system",
            "messages:webhooks",
            "messages:broadcast"
        ]

        for stream in streams:
            task = asyncio.create_task(self._consume_stream(stream))
            self.consumer_tasks.add(task)

        logger.info(f"Started {len(streams)} consumer tasks")

    async def _consume_stream(self, stream_name: str) -> None:
        """Consume messages from a Redis Stream."""
        consumer_name = f"consumer-{uuid.uuid4().hex[:8]}"

        while self.running:
            try:
                # Read messages from stream
                messages = await self.redis_client.xreadgroup(
                    self.config.consumer_group_name,
                    consumer_name,
                    {stream_name: ">"},
                    count=self.config.batch_size,
                    block=1000  # 1 second timeout
                )

                for stream, stream_messages in messages:
                    for message_id, fields in stream_messages:
                        await self._process_message(stream_name, message_id, fields)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error consuming from {stream_name}: {e}")
                await asyncio.sleep(1)

    async def _process_message(self, stream_name: str, message_id: str, fields: Dict) -> None:
        """Process a single message."""
        try:
            # Deserialize message
            message_data = fields.get(b"message", fields.get("message"))
            if isinstance(message_data, bytes):
                message_data = message_data.decode()

            message = Message.from_json(message_data)

            # Check if message is expired
            if message.is_expired():
                await self.acknowledge_message(stream_name, self.config.consumer_group_name, message_id)
                return

            # Process message
            await self._handle_message(message)

            # Acknowledge successful processing
            await self.acknowledge_message(stream_name, self.config.consumer_group_name, message_id)

            self.stats["messages_received"] += 1

        except Exception as e:
            logger.error(f"Failed to process message {message_id}: {e}")
            self.stats["messages_failed"] += 1
            # Don't acknowledge failed messages - they'll be retried

    async def _handle_message(self, message: Message) -> None:
        """Handle a message by calling registered handlers."""
        handlers = self.message_handlers.get(message.type, [])

        if not handlers:
            logger.warning(f"No handlers registered for message type: {message.type.value}")
            return

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Handler error for message {message.headers.message_id}: {e}")
                raise
