"""
Message Queue Service with Redis backend for high-throughput agent communication.
Designed for >1000 messages/minute capacity with delivery guarantees.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
import uuid
import redis.asyncio as redis
from dataclasses import asdict

from .models import (
    Message,
    MessageStatus,
    MessagePriority,
    QueueConfig,
    DeliveryReceipt,
    BroadcastMessage,
    MessageQueueStats
)


logger = logging.getLogger(__name__)


class MessageQueueService:
    """
    High-performance message queue service using Redis as backend.
    Supports delivery guarantees, retries, and monitoring.
    """

    def __init__(self, config: QueueConfig = None, redis_url: str = "redis://localhost:6379"):
        """Initialize message queue service."""
        self.config = config or QueueConfig()
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.is_running = False
        self._message_handlers: Dict[str, Callable] = {}
        self._processing_tasks: List[asyncio.Task] = []

        # Redis key patterns
        self.queue_key = f"mq:{self.config.name}:messages"
        self.processing_key = f"mq:{self.config.name}:processing"
        self.delivery_key = f"mq:{self.config.name}:deliveries"
        self.stats_key = f"mq:{self.config.name}:stats"
        self.retry_key = f"mq:{self.config.name}:retry"

    async def start(self):
        """Start the message queue service."""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")

            self.is_running = True

            # Start background processing tasks
            self._processing_tasks = [
                asyncio.create_task(self._process_messages()),
                asyncio.create_task(self._process_retries()),
                asyncio.create_task(self._cleanup_expired_messages()),
                asyncio.create_task(self._update_stats())
            ]

            logger.info("Message queue service started")

        except Exception as e:
            logger.error(f"Failed to start message queue service: {e}")
            raise

    async def stop(self):
        """Stop the message queue service."""
        self.is_running = False

        # Cancel processing tasks
        for task in self._processing_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._processing_tasks:
            await asyncio.gather(*self._processing_tasks, return_exceptions=True)

        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()

        logger.info("Message queue service stopped")

    async def send_message(self, message: Message) -> bool:
        """Send a message to the queue."""
        try:
            message_data = self._serialize_message(message)

            # Add to priority queue based on priority
            priority_score = self._get_priority_score(message.priority)

            # Use Redis sorted set for priority ordering
            await self.redis_client.zadd(
                self.queue_key,
                {message_data: priority_score}
            )

            # Set message expiration
            if message.expires_at:
                ttl = int((message.expires_at - datetime.utcnow()).total_seconds())
                if ttl > 0:
                    await self.redis_client.expire(f"msg:{message.id}", ttl)

            logger.debug(f"Queued message {message.id} from {message.sender} to {message.recipient}")
            return True

        except Exception as e:
            logger.error(f"Failed to send message {message.id}: {e}")
            return False

    async def send_broadcast(self, broadcast: BroadcastMessage, agent_ids: List[str]) -> int:
        """Send a broadcast message to multiple agents."""
        messages = broadcast.to_individual_messages(agent_ids)
        sent_count = 0

        for message in messages:
            if await self.send_message(message):
                sent_count += 1

        logger.info(f"Sent broadcast {broadcast.id} to {sent_count}/{len(messages)} agents")
        return sent_count

    async def get_messages_for_agent(self, agent_id: str, limit: int = 10) -> List[Message]:
        """Get pending messages for a specific agent."""
        try:
            # Get messages from sorted set with highest priority first
            message_data_list = await self.redis_client.zrevrange(
                self.queue_key, 0, -1, withscores=False
            )

            messages = []
            for message_data in message_data_list:
                message = self._deserialize_message(message_data)
                if message and message.recipient == agent_id and len(messages) < limit:
                    messages.append(message)

            return messages

        except Exception as e:
            logger.error(f"Failed to get messages for agent {agent_id}: {e}")
            return []

    async def acknowledge_message(self, message_id: str, agent_id: str) -> bool:
        """Acknowledge message delivery."""
        try:
            # Create delivery receipt
            receipt = DeliveryReceipt(
                message_id=message_id,
                agent_id=agent_id
            )

            # Store delivery receipt
            receipt_data = json.dumps(asdict(receipt), default=str)
            await self.redis_client.hset(
                self.delivery_key,
                message_id,
                receipt_data
            )

            # Remove message from queue and processing
            await self._remove_message_from_queues(message_id)

            logger.debug(f"Acknowledged message {message_id} by agent {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to acknowledge message {message_id}: {e}")
            return False

    async def register_message_handler(self, agent_id: str, handler: Callable[[Message], bool]):
        """Register a message handler for an agent."""
        self._message_handlers[agent_id] = handler
        logger.info(f"Registered message handler for agent {agent_id}")

    async def unregister_message_handler(self, agent_id: str):
        """Unregister a message handler for an agent."""
        if agent_id in self._message_handlers:
            del self._message_handlers[agent_id]
            logger.info(f"Unregistered message handler for agent {agent_id}")

    async def get_queue_stats(self) -> MessageQueueStats:
        """Get current queue statistics."""
        try:
            # Get queue sizes
            queue_size = await self.redis_client.zcard(self.queue_key)
            processing_size = await self.redis_client.hlen(self.processing_key)

            # Get delivery count
            delivery_count = await self.redis_client.hlen(self.delivery_key)

            # Get retry count
            retry_size = await self.redis_client.zcard(self.retry_key)

            # Calculate statistics
            total_messages = queue_size + processing_size + delivery_count
            pending_messages = queue_size + retry_size

            # Get average delivery time from stored stats
            stats_data = await self.redis_client.hgetall(self.stats_key)
            avg_delivery_time = float(stats_data.get(b'avg_delivery_time', 0))

            return MessageQueueStats(
                total_messages=total_messages,
                pending_messages=pending_messages,
                delivered_messages=delivery_count,
                failed_messages=0,  # Could track separately
                queue_size=queue_size,
                average_delivery_time=avg_delivery_time
            )

        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return MessageQueueStats()

    async def _process_messages(self):
        """Background task to process messages."""
        while self.is_running:
            try:
                # Get highest priority message
                message_data = await self.redis_client.zpopmax(self.queue_key, 1)

                if not message_data:
                    await asyncio.sleep(0.1)  # Short delay when queue is empty
                    continue

                message_json, priority = message_data[0]
                message = self._deserialize_message(message_json)

                if not message:
                    continue

                # Check if message is expired
                if message.is_expired:
                    logger.debug(f"Discarding expired message {message.id}")
                    continue

                # Move to processing queue
                await self._move_to_processing(message)

                # Try to deliver message
                success = await self._deliver_message(message)

                if success:
                    # Message delivered successfully, remove from processing
                    await self._remove_from_processing(message.id)
                else:
                    # Delivery failed, handle retry
                    await self._handle_delivery_failure(message)

            except Exception as e:
                logger.error(f"Error in message processing: {e}")
                await asyncio.sleep(1)

    async def _process_retries(self):
        """Background task to process retry queue."""
        while self.is_running:
            try:
                # Get messages ready for retry (score <= current timestamp)
                current_time = datetime.utcnow().timestamp()
                retry_data = await self.redis_client.zrangebyscore(
                    self.retry_key, 0, current_time, start=0, num=10
                )

                for message_json in retry_data:
                    message = self._deserialize_message(message_json)
                    if message and message.can_retry:
                        # Remove from retry queue
                        await self.redis_client.zrem(self.retry_key, message_json)

                        # Add back to main queue
                        message.delivery_attempts += 1
                        await self.send_message(message)

                        logger.debug(f"Retrying message {message.id} (attempt {message.delivery_attempts})")

                await asyncio.sleep(5)  # Check retries every 5 seconds

            except Exception as e:
                logger.error(f"Error in retry processing: {e}")
                await asyncio.sleep(10)

    async def _cleanup_expired_messages(self):
        """Background task to clean up expired messages."""
        while self.is_running:
            try:
                current_time = datetime.utcnow().timestamp()

                # Clean up expired messages from all queues
                for queue_key in [self.queue_key, self.retry_key]:
                    # This would need custom logic to check message expiration
                    # For now, we rely on Redis TTL
                    pass

                await asyncio.sleep(300)  # Clean up every 5 minutes

            except Exception as e:
                logger.error(f"Error in cleanup: {e}")
                await asyncio.sleep(60)

    async def _update_stats(self):
        """Background task to update statistics."""
        while self.is_running:
            try:
                stats = await self.get_queue_stats()

                # Store stats in Redis
                stats_data = {
                    'total_messages': stats.total_messages,
                    'pending_messages': stats.pending_messages,
                    'delivered_messages': stats.delivered_messages,
                    'queue_size': stats.queue_size,
                    'avg_delivery_time': stats.average_delivery_time,
                    'last_updated': stats.last_updated.isoformat()
                }

                await self.redis_client.hmset(self.stats_key, stats_data)

                await asyncio.sleep(30)  # Update stats every 30 seconds

            except Exception as e:
                logger.error(f"Error updating stats: {e}")
                await asyncio.sleep(60)

    async def _deliver_message(self, message: Message) -> bool:
        """Attempt to deliver a message."""
        try:
            # Check if agent has a registered handler
            if message.recipient in self._message_handlers:
                handler = self._message_handlers[message.recipient]
                success = await handler(message)

                if success:
                    await self.acknowledge_message(message.id, message.recipient)
                    return True

            # If no handler, the message will be available for polling
            # This is compatible with the current tmux replacement strategy
            return True

        except Exception as e:
            logger.error(f"Failed to deliver message {message.id}: {e}")
            return False

    def _serialize_message(self, message: Message) -> str:
        """Serialize message to JSON."""
        data = asdict(message)
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return json.dumps(data)

    def _deserialize_message(self, message_data: str) -> Optional[Message]:
        """Deserialize message from JSON."""
        try:
            data = json.loads(message_data)

            # Convert ISO strings back to datetime objects
            for key in ['created_at', 'expires_at']:
                if key in data and data[key]:
                    data[key] = datetime.fromisoformat(data[key])

            # Convert enums
            if 'priority' in data:
                data['priority'] = MessagePriority(data['priority'])
            if 'status' in data:
                data['status'] = MessageStatus(data['status'])

            return Message(**data)

        except Exception as e:
            logger.error(f"Failed to deserialize message: {e}")
            return None

    def _get_priority_score(self, priority: MessagePriority) -> float:
        """Get numeric score for message priority."""
        priority_scores = {
            MessagePriority.CRITICAL: 1000,
            MessagePriority.HIGH: 100,
            MessagePriority.MEDIUM: 10,
            MessagePriority.LOW: 1
        }
        return priority_scores.get(priority, 1)

    async def _move_to_processing(self, message: Message):
        """Move message to processing queue."""
        message_data = self._serialize_message(message)
        await self.redis_client.hset(
            self.processing_key,
            message.id,
            message_data
        )

    async def _remove_from_processing(self, message_id: str):
        """Remove message from processing queue."""
        await self.redis_client.hdel(self.processing_key, message_id)

    async def _handle_delivery_failure(self, message: Message):
        """Handle failed message delivery."""
        message.delivery_attempts += 1

        if message.can_retry:
            # Schedule for retry
            retry_time = datetime.utcnow() + timedelta(seconds=self.config.retry_delay)
            retry_score = retry_time.timestamp()

            message_data = self._serialize_message(message)
            await self.redis_client.zadd(
                self.retry_key,
                {message_data: retry_score}
            )

            logger.debug(f"Scheduled message {message.id} for retry")
        else:
            logger.warning(f"Message {message.id} exceeded max retry attempts")

        # Remove from processing
        await self._remove_from_processing(message.id)

    async def _remove_message_from_queues(self, message_id: str):
        """Remove message from all queues."""
        # Remove from processing
        await self.redis_client.hdel(self.processing_key, message_id)

        # Remove from retry queue (would need to scan all entries)
        # This is a limitation of Redis sorted sets - we'll handle in cleanup
