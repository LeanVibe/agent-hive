"""
Production Redis-based Message Bus

Enterprise-grade message bus system using Redis for reliable, 
scalable agent-to-agent communication.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Callable, Any, Set
from contextlib import asynccontextmanager

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

from .message_protocol import AgentMessage, MessageDeliveryStatus, MessagePriority


logger = logging.getLogger(__name__)


class MessageBusConfig:
    """Configuration for Redis message bus."""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_connections: int = 10,
        message_ttl: int = 3600,
        retry_limit: int = 3,
        batch_size: int = 100,
        monitor_interval: int = 30
    ):
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.message_ttl = message_ttl
        self.retry_limit = retry_limit
        self.batch_size = batch_size
        self.monitor_interval = monitor_interval


class MessageBus:
    """
    Production Redis-based message bus for agent communication.
    
    Features:
    - Pub/Sub for real-time messaging
    - Streams for persistent message history
    - Priority queues for message ordering
    - Delivery tracking and acknowledgments
    - Dead letter queue for failed messages
    """
    
    def __init__(self, config: MessageBusConfig = None):
        """Initialize message bus with Redis backend."""
        self.config = config or MessageBusConfig()
        self.redis_pool: Optional[redis.ConnectionPool] = None
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        
        # Message tracking
        self.delivery_status: Dict[str, MessageDeliveryStatus] = {}
        self.active_subscriptions: Set[str] = set()
        self.message_handlers: Dict[str, Callable] = {}
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.running = False
        
        logger.info("MessageBus initialized with Redis backend")
    
    async def start(self) -> None:
        """Start the message bus and Redis connections."""
        if self.running:
            logger.warning("Message bus already running")
            return
        
        if redis is None:
            raise RuntimeError("redis[asyncio] package required for message bus")
        
        try:
            # Create Redis connection pool
            self.redis_pool = redis.ConnectionPool.from_url(
                self.config.redis_url,
                max_connections=self.config.max_connections
            )
            
            # Create Redis client
            self.redis_client = redis.Redis(connection_pool=self.redis_pool)
            
            # Test connection
            await self.redis_client.ping()
            
            # Create pub/sub client
            self.pubsub = self.redis_client.pubsub()
            
            # Start background monitoring tasks
            self.background_tasks = [
                asyncio.create_task(self._monitor_delivery_status()),
                asyncio.create_task(self._process_dead_letter_queue()),
                asyncio.create_task(self._cleanup_expired_messages())
            ]
            
            self.running = True
            logger.info("Message bus started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start message bus: {e}")
            await self.shutdown()
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the message bus and cleanup resources."""
        if not self.running:
            return
        
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Close pub/sub
        if self.pubsub:
            await self.pubsub.close()
        
        # Close Redis connections
        if self.redis_client:
            await self.redis_client.close()
        
        if self.redis_pool:
            await self.redis_pool.disconnect()
        
        logger.info("Message bus shutdown complete")
    
    @asynccontextmanager
    async def lifespan(self):
        """Context manager for message bus lifecycle."""
        await self.start()
        try:
            yield self
        finally:
            await self.shutdown()
    
    async def publish_message(self, message: AgentMessage) -> bool:
        """
        Publish a message to the bus.
        
        Args:
            message: AgentMessage to publish
            
        Returns:
            bool: True if message was published successfully
        """
        if not self.running or not self.redis_client:
            raise RuntimeError("Message bus not running")
        
        try:
            # Serialize message
            message_data = json.dumps(message.to_dict())
            
            # Create delivery tracking
            delivery_status = MessageDeliveryStatus(
                message_id=message.message_id,
                status='pending'
            )
            self.delivery_status[message.message_id] = delivery_status
            
            # Publish to pub/sub channel
            channel = f"agent.{message.to_agent}"
            await self.redis_client.publish(channel, message_data)
            
            # Store in persistent stream for replay capability
            stream_key = f"stream.{message.to_agent}"
            await self.redis_client.xadd(
                stream_key,
                {
                    'message_id': message.message_id,
                    'data': message_data,
                    'priority': message.priority.value
                },
                maxlen=1000  # Keep last 1000 messages
            )
            
            # Add to priority queue
            priority_queue = f"queue.{message.to_agent}"
            await self.redis_client.zadd(
                priority_queue,
                {message.message_id: message.priority.value}
            )
            
            # Set message TTL
            await self.redis_client.setex(
                f"message.{message.message_id}",
                message.delivery_options.ttl_seconds,
                message_data
            )
            
            delivery_status.mark_delivered()
            
            logger.debug(f"Published message {message.message_id} to {message.to_agent}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message {message.message_id}: {e}")
            if message.message_id in self.delivery_status:
                self.delivery_status[message.message_id].mark_failed(str(e))
            return False
    
    async def subscribe_to_agent(self, agent_name: str, message_handler: Callable) -> None:
        """
        Subscribe to messages for a specific agent.
        
        Args:
            agent_name: Name of agent to subscribe for
            message_handler: Async function to handle incoming messages
        """
        if not self.running or not self.pubsub:
            raise RuntimeError("Message bus not running")
        
        channel = f"agent.{agent_name}"
        
        if channel in self.active_subscriptions:
            logger.warning(f"Already subscribed to {channel}")
            return
        
        try:
            # Subscribe to pub/sub channel
            await self.pubsub.subscribe(channel)
            self.active_subscriptions.add(channel)
            self.message_handlers[channel] = message_handler
            
            # Start message processing task for this agent
            task = asyncio.create_task(self._process_messages_for_agent(agent_name))
            self.background_tasks.append(task)
            
            logger.info(f"Subscribed to messages for agent: {agent_name}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to agent {agent_name}: {e}")
            raise
    
    async def unsubscribe_from_agent(self, agent_name: str) -> None:
        """Unsubscribe from messages for a specific agent."""
        if not self.pubsub:
            return
        
        channel = f"agent.{agent_name}"
        
        if channel not in self.active_subscriptions:
            return
        
        try:
            await self.pubsub.unsubscribe(channel)
            self.active_subscriptions.discard(channel)
            self.message_handlers.pop(channel, None)
            
            logger.info(f"Unsubscribed from agent: {agent_name}")
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from agent {agent_name}: {e}")
    
    async def acknowledge_message(self, message_id: str) -> bool:
        """
        Acknowledge receipt and processing of a message.
        
        Args:
            message_id: ID of message to acknowledge
            
        Returns:
            bool: True if acknowledgment was recorded
        """
        if message_id in self.delivery_status:
            self.delivery_status[message_id].mark_acknowledged()
            
            # Remove from Redis tracking
            if self.redis_client:
                await self.redis_client.delete(f"pending.{message_id}")
            
            logger.debug(f"Message {message_id} acknowledged")
            return True
        
        return False
    
    async def get_message_status(self, message_id: str) -> Optional[MessageDeliveryStatus]:
        """Get delivery status for a message."""
        return self.delivery_status.get(message_id)
    
    async def get_agent_queue_size(self, agent_name: str) -> int:
        """Get number of pending messages for an agent."""
        if not self.redis_client:
            return 0
        
        queue_key = f"queue.{agent_name}"
        return await self.redis_client.zcard(queue_key)
    
    async def _process_messages_for_agent(self, agent_name: str) -> None:
        """Background task to process messages for a specific agent."""
        channel = f"agent.{agent_name}"
        
        while self.running and channel in self.active_subscriptions:
            try:
                # Get message from pub/sub
                message = await self.pubsub.get_message(ignore_subscribe_messages=True)
                
                if message and message['type'] == 'message':
                    message_data = json.loads(message['data'])
                    agent_message = AgentMessage.from_dict(message_data)
                    
                    # Call message handler
                    handler = self.message_handlers.get(channel)
                    if handler:
                        try:
                            await handler(agent_message)
                            await self.acknowledge_message(agent_message.message_id)
                        except Exception as e:
                            logger.error(f"Message handler failed for {agent_message.message_id}: {e}")
                            await self._handle_message_failure(agent_message, str(e))
                
                await asyncio.sleep(0.1)  # Prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error processing messages for {agent_name}: {e}")
                await asyncio.sleep(1)
    
    async def _monitor_delivery_status(self) -> None:
        """Background task to monitor message delivery status."""
        while self.running:
            try:
                current_time = datetime.now(timezone.utc)
                expired_messages = []
                
                for message_id, status in self.delivery_status.items():
                    # Check for expired messages
                    if status.status == 'pending' and status.last_attempt:
                        time_since_attempt = current_time - status.last_attempt
                        if time_since_attempt.total_seconds() > self.config.message_ttl:
                            expired_messages.append(message_id)
                
                # Mark expired messages
                for message_id in expired_messages:
                    self.delivery_status[message_id].mark_expired()
                    logger.warning(f"Message {message_id} expired")
                
                await asyncio.sleep(self.config.monitor_interval)
                
            except Exception as e:
                logger.error(f"Error in delivery status monitoring: {e}")
                await asyncio.sleep(self.config.monitor_interval)
    
    async def _process_dead_letter_queue(self) -> None:
        """Background task to process dead letter queue."""
        while self.running:
            try:
                if self.redis_client:
                    # Process dead letter queue
                    dlq_messages = await self.redis_client.lrange("dlq", 0, self.config.batch_size - 1)
                    
                    for message_data in dlq_messages:
                        # TODO: Implement dead letter processing logic
                        pass
                
                await asyncio.sleep(self.config.monitor_interval)
                
            except Exception as e:
                logger.error(f"Error processing dead letter queue: {e}")
                await asyncio.sleep(self.config.monitor_interval)
    
    async def _cleanup_expired_messages(self) -> None:
        """Background task to cleanup expired messages."""
        while self.running:
            try:
                current_time = datetime.now(timezone.utc)
                cutoff_time = current_time - timedelta(seconds=self.config.message_ttl * 2)
                
                # Cleanup local tracking
                expired_ids = [
                    msg_id for msg_id, status in self.delivery_status.items()
                    if status.last_attempt and status.last_attempt < cutoff_time
                ]
                
                for msg_id in expired_ids:
                    del self.delivery_status[msg_id]
                
                logger.debug(f"Cleaned up {len(expired_ids)} expired message records")
                
                await asyncio.sleep(self.config.monitor_interval * 2)
                
            except Exception as e:
                logger.error(f"Error in message cleanup: {e}")
                await asyncio.sleep(self.config.monitor_interval)
    
    async def _handle_message_failure(self, message: AgentMessage, error: str) -> None:
        """Handle failed message delivery."""
        if message.message_id in self.delivery_status:
            status = self.delivery_status[message.message_id]
            status.mark_failed(error)
            
            # Retry if within limits
            if status.attempts < self.config.retry_limit:
                logger.info(f"Retrying message {message.message_id} (attempt {status.attempts + 1})")
                await asyncio.sleep(message.delivery_options.retry_delay_seconds)
                await self.publish_message(message)
            else:
                # Move to dead letter queue
                logger.error(f"Message {message.message_id} failed after {status.attempts} attempts")
                if self.redis_client:
                    await self.redis_client.lpush("dlq", json.dumps(message.to_dict()))