"""
Tests for Redis-based Message Bus System
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

from message_bus.message_bus import MessageBus, MessageBusConfig
from message_bus.message_protocol import AgentMessage, MessageType, MessagePriority
from message_bus.agent_communicator import AgentCommunicator


class TestMessageProtocol:
    """Test message protocol and serialization."""

    def test_agent_message_creation(self):
        """Test basic message creation."""
        message = AgentMessage(
            from_agent="test-agent",
            to_agent="target-agent",
            message_type=MessageType.TASK_ASSIGNMENT,
            body={"task": "test task"}
        )

        assert message.from_agent == "test-agent"
        assert message.to_agent == "target-agent"
        assert message.message_type == MessageType.TASK_ASSIGNMENT
        assert message.body == {"task": "test task"}
        assert message.priority == MessagePriority.MEDIUM
        assert message.message_id is not None
        assert message.timestamp is not None

    def test_message_serialization(self):
        """Test message to/from dict conversion."""
        original = AgentMessage(
            from_agent="test-agent",
            to_agent="target-agent",
            message_type=MessageType.INFORMATION_SHARE,
            body={"content": "test message"},
            priority=MessagePriority.HIGH
        )

        # Convert to dict and back
        message_dict = original.to_dict()
        restored = AgentMessage.from_dict(message_dict)

        assert restored.from_agent == original.from_agent
        assert restored.to_agent == original.to_agent
        assert restored.message_type == original.message_type
        assert restored.body == original.body
        assert restored.priority == original.priority
        assert restored.message_id == original.message_id

    def test_message_reply_creation(self):
        """Test creating reply messages."""
        original = AgentMessage(
            from_agent="agent-a",
            to_agent="agent-b",
            message_type=MessageType.QUESTION,
            body={"question": "How are you?"}
        )

        reply = original.create_reply(
            body={"answer": "I'm fine, thanks!"}
        )

        assert reply.from_agent == "agent-b"
        assert reply.to_agent == "agent-a"
        assert reply.message_type == MessageType.ANSWER
        assert reply.correlation_id == original.message_id
        assert reply.reply_to == original.message_id

    def test_message_validation(self):
        """Test message validation."""
        # Test empty from_agent
        with pytest.raises(ValueError, match="from_agent cannot be empty"):
            AgentMessage(
                from_agent="",
                to_agent="target",
                message_type=MessageType.NOTIFICATION,
                body={"test": "data"}
            )

        # Test empty to_agent
        with pytest.raises(ValueError, match="to_agent cannot be empty"):
            AgentMessage(
                from_agent="sender",
                to_agent="",
                message_type=MessageType.NOTIFICATION,
                body={"test": "data"}
            )

        # Test empty body
        with pytest.raises(ValueError, match="message body cannot be empty"):
            AgentMessage(
                from_agent="sender",
                to_agent="target",
                message_type=MessageType.NOTIFICATION,
                body={}
            )


@pytest.mark.asyncio
class TestMessageBus:
    """Test Redis message bus functionality."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.publish = AsyncMock(return_value=1)
        mock_redis.xadd = AsyncMock(return_value=b"1234567890-0")
        mock_redis.zadd = AsyncMock(return_value=1)
        mock_redis.setex = AsyncMock(return_value=True)
        mock_redis.close = AsyncMock()
        return mock_redis

    @pytest.fixture
    def mock_redis_pool(self, mock_redis):
        """Mock Redis connection pool."""
        mock_pool = Mock()
        mock_pool.disconnect = AsyncMock()

        with patch('redis.asyncio.ConnectionPool') as mock_pool_class:
            mock_pool_class.from_url.return_value = mock_pool
            with patch('redis.asyncio.Redis') as mock_redis_class:
                mock_redis_class.return_value = mock_redis
                yield mock_pool

    async def test_message_bus_startup_shutdown(self, mock_redis_pool, mock_redis):
        """Test message bus startup and shutdown."""
        config = MessageBusConfig(redis_url="redis://localhost:6379")
        bus = MessageBus(config)

        # Test startup
        await bus.start()
        assert bus.running

        # Test shutdown
        await bus.shutdown()
        assert not bus.running

    async def test_publish_message(self, mock_redis_pool, mock_redis):
        """Test message publishing."""
        config = MessageBusConfig()
        bus = MessageBus(config)
        await bus.start()

        try:
            message = AgentMessage(
                from_agent="sender",
                to_agent="receiver",
                message_type=MessageType.TASK_ASSIGNMENT,
                body={"task": "test task"}
            )

            result = await bus.publish_message(message)

            assert result is True
            assert message.message_id in bus.delivery_status

            # Verify Redis calls
            mock_redis.publish.assert_called_once()
            mock_redis.xadd.assert_called_once()
            mock_redis.zadd.assert_called_once()
            mock_redis.setex.assert_called_once()

        finally:
            await bus.shutdown()

    async def test_subscribe_to_agent(self, mock_redis_pool, mock_redis):
        """Test subscribing to agent messages."""
        config = MessageBusConfig()
        bus = MessageBus(config)

        # Mock pubsub
        mock_pubsub = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub

        await bus.start()

        try:
            message_handler = AsyncMock()
            await bus.subscribe_to_agent("test-agent", message_handler)

            assert "agent.test-agent" in bus.active_subscriptions
            assert bus.message_handlers["agent.test-agent"] == message_handler

            mock_pubsub.subscribe.assert_called_once_with("agent.test-agent")

        finally:
            await bus.shutdown()

    async def test_acknowledge_message(self, mock_redis_pool, mock_redis):
        """Test message acknowledgment."""
        config = MessageBusConfig()
        bus = MessageBus(config)
        await bus.start()

        try:
            # Create a message and add to delivery tracking
            message_id = "test-message-123"
            from message_bus.message_bus import MessageDeliveryStatus

            status = MessageDeliveryStatus(message_id=message_id, status='delivered')
            bus.delivery_status[message_id] = status

            # Acknowledge the message
            result = await bus.acknowledge_message(message_id)

            assert result is True
            assert bus.delivery_status[message_id].status == 'acknowledged'
            assert bus.delivery_status[message_id].acknowledged_at is not None

        finally:
            await bus.shutdown()


@pytest.mark.asyncio
class TestAgentCommunicator:
    """Test agent communicator interface."""

    @pytest.fixture
    def mock_message_bus(self):
        """Mock message bus."""
        mock_bus = AsyncMock()
        mock_bus.start = AsyncMock()
        mock_bus.subscribe_to_agent = AsyncMock()
        mock_bus.unsubscribe_from_agent = AsyncMock()
        mock_bus.publish_message = AsyncMock(return_value=True)
        mock_bus.get_agent_queue_size = AsyncMock(return_value=5)
        return mock_bus

    async def test_communicator_lifecycle(self, mock_message_bus):
        """Test communicator start/stop lifecycle."""
        communicator = AgentCommunicator("test-agent", mock_message_bus)

        # Test start
        await communicator.start()
        assert communicator.running

        mock_message_bus.start.assert_called_once()
        mock_message_bus.subscribe_to_agent.assert_called_once_with(
            "test-agent", communicator._handle_incoming_message
        )

        # Test stop
        await communicator.stop()
        assert not communicator.running

        mock_message_bus.unsubscribe_from_agent.assert_called_once_with("test-agent")

    async def test_send_message_to_agent(self, mock_message_bus):
        """Test sending messages to other agents."""
        communicator = AgentCommunicator("sender-agent", mock_message_bus)
        await communicator.start()

        result = await communicator.send_message_to_agent(
            target_agent="target-agent",
            message="Hello, target agent!",
            message_type=MessageType.INFORMATION_SHARE,
            priority=MessagePriority.HIGH
        )

        assert result is True
        mock_message_bus.publish_message.assert_called_once()

        # Verify message structure
        call_args = mock_message_bus.publish_message.call_args[0][0]
        assert call_args.from_agent == "sender-agent"
        assert call_args.to_agent == "target-agent"
        assert call_args.message_type == MessageType.INFORMATION_SHARE
        assert call_args.priority == MessagePriority.HIGH
        assert call_args.body["content"] == "Hello, target agent!"

    async def test_send_task_assignment(self, mock_message_bus):
        """Test sending task assignments."""
        communicator = AgentCommunicator("pm-agent", mock_message_bus)
        await communicator.start()

        result = await communicator.send_task_assignment(
            target_agent="dev-agent",
            task_description="Implement new feature",
            priority=MessagePriority.URGENT,
            deadline="2025-07-20",
            context={"project": "agent-hive"}
        )

        assert result is True
        mock_message_bus.publish_message.assert_called_once()

        # Verify task message structure
        call_args = mock_message_bus.publish_message.call_args[0][0]
        assert call_args.message_type == MessageType.TASK_ASSIGNMENT
        assert call_args.body["task_description"] == "Implement new feature"
        assert call_args.body["deadline"] == "2025-07-20"
        assert call_args.body["context"]["project"] == "agent-hive"

    async def test_broadcast_message(self, mock_message_bus):
        """Test broadcasting messages to multiple agents."""
        communicator = AgentCommunicator("broadcast-agent", mock_message_bus)
        await communicator.start()

        agents = ["agent-1", "agent-2", "agent-3"]
        results = await communicator.broadcast_message(
            message="System maintenance at 2 AM",
            agents=agents,
            message_type=MessageType.NOTIFICATION,
            priority=MessagePriority.HIGH
        )

        assert len(results) == 3
        assert all(results.values())  # All should be True
        assert mock_message_bus.publish_message.call_count == 3

    async def test_reply_to_message(self, mock_message_bus):
        """Test replying to received messages."""
        communicator = AgentCommunicator("responder-agent", mock_message_bus)
        await communicator.start()

        # Create original message
        original = AgentMessage(
            from_agent="questioner-agent",
            to_agent="responder-agent",
            message_type=MessageType.QUESTION,
            body={"question": "What's the status?"}
        )

        result = await communicator.reply_to_message(
            original_message=original,
            reply_content="All systems operational"
        )

        assert result is True
        mock_message_bus.publish_message.assert_called_once()

        # Verify reply structure
        call_args = mock_message_bus.publish_message.call_args[0][0]
        assert call_args.from_agent == "responder-agent"
        assert call_args.to_agent == "questioner-agent"
        assert call_args.message_type == MessageType.ANSWER
        assert call_args.correlation_id == original.message_id
        assert call_args.reply_to == original.message_id

    async def test_message_handler_callback(self, mock_message_bus):
        """Test message handler callback functionality."""
        communicator = AgentCommunicator("listener-agent", mock_message_bus)

        # Set up message handler
        received_messages = []

        async def test_handler(message: AgentMessage):
            received_messages.append(message)

        communicator.set_message_handler(test_handler)
        await communicator.start()

        # Simulate incoming message
        test_message = AgentMessage(
            from_agent="sender-agent",
            to_agent="listener-agent",
            message_type=MessageType.INFORMATION_SHARE,
            body={"content": "Test message"}
        )

        await communicator._handle_incoming_message(test_message)

        assert len(received_messages) == 1
        assert received_messages[0] == test_message

    async def test_get_pending_messages_count(self, mock_message_bus):
        """Test getting pending message count."""
        communicator = AgentCommunicator("busy-agent", mock_message_bus)
        await communicator.start()

        count = await communicator.get_pending_messages_count()

        assert count == 5  # Mock returns 5
        mock_message_bus.get_agent_queue_size.assert_called_once_with("busy-agent")


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for complete message flow."""

    @pytest.mark.skipif(
        True,  # Skip by default since requires Redis
        reason="Requires Redis server for integration testing"
    )
    async def test_end_to_end_message_flow(self):
        """Test complete message flow between two agents."""
        config = MessageBusConfig(redis_url="redis://localhost:6379")

        async with MessageBus(config).lifespan() as bus:
            # Set up sender and receiver
            sender = AgentCommunicator("sender-agent", bus)
            receiver = AgentCommunicator("receiver-agent", bus)

            # Track received messages
            received_messages = []

            async def message_handler(message: AgentMessage):
                received_messages.append(message)

            receiver.set_message_handler(message_handler)

            await sender.start()
            await receiver.start()

            try:
                # Send message
                success = await sender.send_message_to_agent(
                    target_agent="receiver-agent",
                    message="Hello from sender!",
                    message_type=MessageType.INFORMATION_SHARE
                )

                assert success

                # Give time for message processing
                await asyncio.sleep(0.5)

                # Verify message was received
                assert len(received_messages) == 1
                assert received_messages[0].from_agent == "sender-agent"
                assert received_messages[0].body["content"] == "Hello from sender!"

            finally:
                await sender.stop()
                await receiver.stop()
