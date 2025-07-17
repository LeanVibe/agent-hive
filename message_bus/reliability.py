"""
Message Reliability Components

Provides message acknowledgment, retry mechanisms, and dead letter queues
for production-grade message reliability.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
import uuid
import time

from .message_protocol import Message, MessageStatus, MessageType


logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """Retry policy configuration."""
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True


class MessageAcknowledgment:
    """
    Message acknowledgment system for reliable delivery.

    Tracks message delivery status and handles acknowledgments.
    """

    def __init__(self, redis_client):
        """
        Initialize message acknowledgment system.

        Args:
            redis_client: Redis client for persistence
        """
        self.redis_client = redis_client
        self.pending_messages: Dict[str, Message] = {}
        self.ack_timeout = 300  # 5 minutes default timeout

    async def track_message(self, message: Message, timeout: Optional[int] = None) -> None:
        """
        Track a message for acknowledgment.

        Args:
            message: Message to track
            timeout: Acknowledgment timeout in seconds
        """
        timeout = timeout or self.ack_timeout
        expiry = datetime.now() + timedelta(seconds=timeout)

        # Store in Redis with expiration
        tracking_data = {
            "message": message.to_json(),
            "sent_at": datetime.now().isoformat(),
            "expires_at": expiry.isoformat(),
            "status": "pending"
        }

        await self.redis_client.setex(
            f"ack_tracking:{message.headers.message_id}",
            timeout,
            json.dumps(tracking_data)
        )

        # Store in local cache
        self.pending_messages[message.headers.message_id] = message

        logger.debug(f"Tracking message {message.headers.message_id} for acknowledgment")

    async def acknowledge_message(self, message_id: str, response_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Acknowledge a message.

        Args:
            message_id: Message ID to acknowledge
            response_data: Optional response data

        Returns:
            True if message was acknowledged successfully
        """
        try:
            # Update tracking in Redis
            tracking_key = f"ack_tracking:{message_id}"
            tracking_data = await self.redis_client.get(tracking_key)

            if not tracking_data:
                logger.warning(f"No tracking data found for message {message_id}")
                return False

            tracking_info = json.loads(tracking_data)
            tracking_info["status"] = "acknowledged"
            tracking_info["acknowledged_at"] = datetime.now().isoformat()

            if response_data:
                tracking_info["response"] = response_data

            # Update with longer TTL for audit trail
            await self.redis_client.setex(
                tracking_key,
                86400,  # 24 hours
                json.dumps(tracking_info)
            )

            # Remove from pending
            if message_id in self.pending_messages:
                del self.pending_messages[message_id]

            logger.debug(f"Acknowledged message {message_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to acknowledge message {message_id}: {e}")
            return False

    async def check_expired_messages(self) -> List[str]:
        """
        Check for expired unacknowledged messages.

        Returns:
            List of expired message IDs
        """
        expired_messages = []
        current_time = datetime.now()

        # Check Redis for expired tracking entries
        pattern = "ack_tracking:*"
        async for key in self.redis_client.scan_iter(match=pattern):
            try:
                tracking_data = await self.redis_client.get(key)
                if not tracking_data:
                    continue

                tracking_info = json.loads(tracking_data)
                if tracking_info["status"] != "pending":
                    continue

                expires_at = datetime.fromisoformat(tracking_info["expires_at"])
                if current_time > expires_at:
                    message_id = key.decode().split(":")[-1]
                    expired_messages.append(message_id)

            except Exception as e:
                logger.error(f"Error checking expiry for {key}: {e}")

        return expired_messages

    async def get_pending_count(self) -> int:
        """Get count of pending acknowledgments."""
        pattern = "ack_tracking:*"
        count = 0

        async for key in self.redis_client.scan_iter(match=pattern):
            try:
                tracking_data = await self.redis_client.get(key)
                if tracking_data:
                    tracking_info = json.loads(tracking_data)
                    if tracking_info["status"] == "pending":
                        count += 1
            except Exception:
                continue

        return count


class RetryManager:
    """
    Message retry manager with exponential backoff.

    Handles failed message retries with configurable policies.
    """

    def __init__(self, redis_client, default_policy: Optional[RetryPolicy] = None):
        """
        Initialize retry manager.

        Args:
            redis_client: Redis client for persistence
            default_policy: Default retry policy
        """
        self.redis_client = redis_client
        self.default_policy = default_policy or RetryPolicy()
        self.retry_task: Optional[asyncio.Task] = None
        self.running = False

    async def start(self) -> None:
        """Start the retry manager."""
        if self.running:
            return

        self.running = True
        self.retry_task = asyncio.create_task(self._retry_loop())
        logger.info("Retry manager started")

    async def stop(self) -> None:
        """Stop the retry manager."""
        if not self.running:
            return

        self.running = False

        if self.retry_task:
            self.retry_task.cancel()
            try:
                await self.retry_task
            except asyncio.CancelledError:
                pass

        logger.info("Retry manager stopped")

    async def schedule_retry(self, message: Message, error: str,
                           policy: Optional[RetryPolicy] = None) -> bool:
        """
        Schedule a message for retry.

        Args:
            message: Failed message
            error: Error description
            policy: Retry policy (uses default if None)

        Returns:
            True if retry was scheduled
        """
        policy = policy or self.default_policy

        # Check if message should be retried
        if message.headers.retries >= policy.max_retries:
            logger.warning(f"Message {message.headers.message_id} exceeded max retries")
            await self._send_to_dead_letter(message, error)
            return False

        # Calculate retry delay
        retry_delay = self._calculate_delay(message.headers.retries, policy)
        retry_at = datetime.now() + timedelta(seconds=retry_delay)

        # Update message
        message.headers.retries += 1
        message.status = MessageStatus.RETRY

        # Store retry info
        retry_data = {
            "message": message.to_json(),
            "error": error,
            "retry_at": retry_at.isoformat(),
            "retry_count": message.headers.retries,
            "policy": {
                "max_retries": policy.max_retries,
                "base_delay": policy.base_delay,
                "max_delay": policy.max_delay
            }
        }

        # Store in Redis with score as retry timestamp
        await self.redis_client.zadd(
            "retry_queue",
            {json.dumps(retry_data): retry_at.timestamp()}
        )

        logger.info(f"Scheduled retry for message {message.headers.message_id} "
                   f"(attempt {message.headers.retries}/{policy.max_retries}) "
                   f"in {retry_delay:.1f}s")

        return True

    async def get_retry_stats(self) -> Dict[str, Any]:
        """Get retry statistics."""
        queue_size = await self.redis_client.zcard("retry_queue")
        dead_letter_size = await self.redis_client.zcard("dead_letter_queue")

        return {
            "retry_queue_size": queue_size,
            "dead_letter_queue_size": dead_letter_size,
            "running": self.running
        }

    def _calculate_delay(self, retry_count: int, policy: RetryPolicy) -> float:
        """Calculate retry delay with exponential backoff."""
        delay = policy.base_delay * (policy.exponential_base ** retry_count)
        delay = min(delay, policy.max_delay)

        # Add jitter to prevent thundering herd
        if policy.jitter:
            import random
            jitter = random.uniform(0.8, 1.2)
            delay *= jitter

        return delay

    async def _retry_loop(self) -> None:
        """Main retry processing loop."""
        while self.running:
            try:
                current_time = time.time()

                # Get messages ready for retry
                ready_messages = await self.redis_client.zrangebyscore(
                    "retry_queue",
                    0,
                    current_time,
                    withscores=True,
                    start=0,
                    num=10  # Process up to 10 at a time
                )

                for message_data, score in ready_messages:
                    try:
                        retry_info = json.loads(message_data)
                        message = Message.from_json(retry_info["message"])

                        # Remove from retry queue
                        await self.redis_client.zrem("retry_queue", message_data)

                        # Process retry
                        await self._process_retry(message, retry_info)

                    except Exception as e:
                        logger.error(f"Error processing retry: {e}")

                # Sleep before next check
                await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Retry loop error: {e}")
                await asyncio.sleep(10)

    async def _process_retry(self, message: Message, retry_info: Dict[str, Any]) -> None:
        """Process a message retry."""
        try:
            # Here you would resend the message through the appropriate channel
            # For now, we'll just log it
            logger.info(f"Retrying message {message.headers.message_id} "
                       f"(attempt {message.headers.retries})")

            # In a real implementation, you would:
            # 1. Resend the message through the message bus
            # 2. Track the new attempt
            # 3. Handle success/failure appropriately

        except Exception as e:
            logger.error(f"Failed to retry message {message.headers.message_id}: {e}")

            # If retry fails, schedule another retry or send to dead letter
            policy = RetryPolicy(
                max_retries=retry_info["policy"]["max_retries"],
                base_delay=retry_info["policy"]["base_delay"],
                max_delay=retry_info["policy"]["max_delay"]
            )

            if message.headers.retries < policy.max_retries:
                await self.schedule_retry(message, str(e), policy)
            else:
                await self._send_to_dead_letter(message, str(e))

    async def _send_to_dead_letter(self, message: Message, error: str) -> None:
        """Send message to dead letter queue."""
        message.status = MessageStatus.DEAD_LETTER

        dead_letter_data = {
            "message": message.to_json(),
            "final_error": error,
            "failed_at": datetime.now().isoformat(),
            "total_attempts": message.headers.retries + 1
        }

        # Add to dead letter queue with timestamp score
        await self.redis_client.zadd(
            "dead_letter_queue",
            {json.dumps(dead_letter_data): time.time()}
        )

        logger.error(f"Message {message.headers.message_id} sent to dead letter queue "
                    f"after {message.headers.retries + 1} attempts: {error}")


class DeadLetterQueue:
    """
    Dead letter queue for messages that cannot be processed.

    Provides inspection and manual recovery capabilities.
    """

    def __init__(self, redis_client):
        """
        Initialize dead letter queue.

        Args:
            redis_client: Redis client for persistence
        """
        self.redis_client = redis_client

    async def get_dead_letters(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get dead letter messages.

        Args:
            limit: Maximum number of messages to return

        Returns:
            List of dead letter messages
        """
        messages = await self.redis_client.zrevrange(
            "dead_letter_queue",
            0,
            limit - 1,
            withscores=True
        )

        dead_letters = []
        for message_data, timestamp in messages:
            try:
                dead_letter_info = json.loads(message_data)
                dead_letter_info["queue_timestamp"] = timestamp
                dead_letters.append(dead_letter_info)
            except Exception as e:
                logger.error(f"Error parsing dead letter: {e}")

        return dead_letters

    async def recover_message(self, message_id: str) -> bool:
        """
        Recover a message from dead letter queue.

        Args:
            message_id: Message ID to recover

        Returns:
            True if message was recovered
        """
        try:
            # Find the message in dead letter queue
            dead_letters = await self.get_dead_letters(1000)  # Search more thoroughly

            for dead_letter in dead_letters:
                message = Message.from_json(dead_letter["message"])
                if message.headers.message_id == message_id:
                    # Reset message for retry
                    message.headers.retries = 0
                    message.status = MessageStatus.PENDING

                    # Remove from dead letter queue
                    await self.redis_client.zrem(
                        "dead_letter_queue",
                        json.dumps({
                            k: v for k, v in dead_letter.items()
                            if k != "queue_timestamp"
                        })
                    )

                    logger.info(f"Recovered message {message_id} from dead letter queue")
                    return True

            logger.warning(f"Message {message_id} not found in dead letter queue")
            return False

        except Exception as e:
            logger.error(f"Failed to recover message {message_id}: {e}")
            return False

    async def purge_old_messages(self, older_than_days: int = 7) -> int:
        """
        Purge old messages from dead letter queue.

        Args:
            older_than_days: Messages older than this will be purged

        Returns:
            Number of messages purged
        """
        cutoff_time = time.time() - (older_than_days * 86400)

        count = await self.redis_client.zremrangebyscore(
            "dead_letter_queue",
            0,
            cutoff_time
        )

        logger.info(f"Purged {count} old messages from dead letter queue")
        return count

    async def get_statistics(self) -> Dict[str, Any]:
        """Get dead letter queue statistics."""
        total_count = await self.redis_client.zcard("dead_letter_queue")

        # Get age distribution
        now = time.time()
        day_ago = now - 86400
        week_ago = now - (7 * 86400)

        recent_count = await self.redis_client.zcount("dead_letter_queue", day_ago, now)
        week_count = await self.redis_client.zcount("dead_letter_queue", week_ago, now)

        return {
            "total_messages": total_count,
            "recent_24h": recent_count,
            "recent_7d": week_count,
            "older_than_7d": total_count - week_count
        }
