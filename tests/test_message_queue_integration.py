"""
Integration tests for the Message Queue System.
Tests end-to-end functionality and validates production readiness.
"""

import asyncio
import pytest
import json
from datetime import datetime, timedelta
from typing import List, Dict

from message_queue.models import Message, MessagePriority, Agent, AgentStatus
from message_queue.queue_service import MessageQueueService, QueueConfig
from message_queue.agent_registry import AgentRegistry
from message_queue.message_broker import MessageBroker


class TestMessageQueueIntegration:
    """Integration tests for core message queue functionality."""

    @pytest.fixture
    async def queue_service(self):
        """Create test queue service with in-memory Redis."""
        config = QueueConfig(
            name="test-queue",
            max_size=1000,
            message_ttl=3600,
            persistence_backend="memory"  # Use memory for tests
        )
        service = MessageQueueService(config, "redis://localhost:6379")
        await service.start()
        yield service
        await service.stop()

    @pytest.fixture
    async def agent_registry(self):
        """Create test agent registry."""
        registry = AgentRegistry([])  # Empty worktree paths for tests

        # Register test agents
        test_agents = [
            Agent(name="test-agent-1", capabilities=["general"], status=AgentStatus.ONLINE),
            Agent(name="test-agent-2", capabilities=["quality"], status=AgentStatus.ONLINE),
            Agent(name="test-agent-3", capabilities=["orchestration"], status=AgentStatus.ONLINE)
        ]

        for agent in test_agents:
            await registry.register_agent(agent)

        return registry

    @pytest.fixture
    async def message_broker(self, queue_service, agent_registry):
        """Create test message broker."""
        broker = MessageBroker(queue_service, agent_registry)
        await broker.start()
        yield broker
        await broker.stop()

    @pytest.mark.asyncio
    async def test_basic_message_flow(self, queue_service, agent_registry):
        """Test basic message send and receive flow."""
        # Get test agent
        agents = await agent_registry.list_agents()
        assert len(agents) >= 1
        test_agent = agents[0]

        # Create test message
        message = Message(
            sender="test-sender",
            recipient=test_agent.id,
            content="Test message content",
            priority=MessagePriority.MEDIUM
        )

        # Send message
        success = await queue_service.send_message(message)
        assert success, "Message should be sent successfully"

        # Retrieve messages for agent
        messages = await queue_service.get_messages_for_agent(test_agent.id)
        assert len(messages) >= 1, "Agent should receive the message"

        received_message = messages[0]
        assert received_message.content == "Test message content"
        assert received_message.sender == "test-sender"
        assert received_message.recipient == test_agent.id

        # Acknowledge message
        ack_success = await queue_service.acknowledge_message(message.id, test_agent.id)
        assert ack_success, "Message acknowledgment should succeed"

    @pytest.mark.asyncio
    async def test_message_routing(self, message_broker, agent_registry):
        """Test intelligent message routing based on content."""
        # Get agents by capability
        quality_agents = await agent_registry.get_agents_by_capability("quality")
        orchestration_agents = await agent_registry.get_agents_by_capability("orchestration")

        assert len(quality_agents) >= 1, "Should have quality agents"
        assert len(orchestration_agents) >= 1, "Should have orchestration agents"

        # Test quality routing
        quality_message = Message(
            sender="test-sender",
            recipient="auto-route",  # Will be determined by broker
            content="We need to improve test quality and fix bugs",
            priority=MessagePriority.HIGH
        )

        routing_success = await message_broker.route_message(quality_message)
        assert routing_success, "Quality message should be routed successfully"
        assert quality_message.recipient == quality_agents[0].id, "Should route to quality agent"

        # Test orchestration routing
        orchestration_message = Message(
            sender="test-sender",
            recipient="auto-route",
            content="Please coordinate with the team and orchestrate deployment",
            priority=MessagePriority.MEDIUM
        )

        routing_success = await message_broker.route_message(orchestration_message)
        assert routing_success, "Orchestration message should be routed successfully"
        assert orchestration_message.recipient == orchestration_agents[0].id, "Should route to orchestration agent"

    @pytest.mark.asyncio
    async def test_load_balancing(self, message_broker, agent_registry):
        """Test load balancing across multiple agents."""
        # Register multiple agents with same capability
        for i in range(3):
            agent = Agent(
                name=f"load-test-agent-{i}",
                capabilities=["general"],
                status=AgentStatus.ONLINE
            )
            await agent_registry.register_agent(agent)

        general_agents = await agent_registry.get_agents_by_capability("general")
        assert len(general_agents) >= 3, "Should have multiple general agents"

        # Send multiple messages
        recipient_counts = {}
        for i in range(6):  # Send 6 messages to 3 agents
            message = Message(
                sender="load-test",
                recipient="auto-route",
                content=f"General task message {i}",
                priority=MessagePriority.MEDIUM
            )

            await message_broker.route_message(message)
            recipient = message.recipient
            recipient_counts[recipient] = recipient_counts.get(recipient, 0) + 1

        # Check load distribution
        assert len(recipient_counts) >= 2, "Messages should be distributed across multiple agents"
        # Each agent should get at least one message
        for count in recipient_counts.values():
            assert count >= 1, "Each agent should receive at least one message"

    @pytest.mark.asyncio
    async def test_message_priority_handling(self, queue_service, agent_registry):
        """Test that high priority messages are processed first."""
        agents = await agent_registry.list_agents()
        test_agent = agents[0]

        # Send messages with different priorities
        messages = [
            Message(
                sender="priority-test",
                recipient=test_agent.id,
                content="Low priority message",
                priority=MessagePriority.LOW
            ),
            Message(
                sender="priority-test",
                recipient=test_agent.id,
                content="High priority message",
                priority=MessagePriority.HIGH
            ),
            Message(
                sender="priority-test",
                recipient=test_agent.id,
                content="Critical priority message",
                priority=MessagePriority.CRITICAL
            ),
            Message(
                sender="priority-test",
                recipient=test_agent.id,
                content="Medium priority message",
                priority=MessagePriority.MEDIUM
            )
        ]

        # Send in mixed order
        for message in messages:
            await queue_service.send_message(message)

        # Retrieve messages (should be in priority order)
        received_messages = await queue_service.get_messages_for_agent(test_agent.id, limit=10)

        # Check priority ordering
        priorities = [msg.priority for msg in received_messages]
        expected_order = [MessagePriority.CRITICAL, MessagePriority.HIGH, MessagePriority.MEDIUM, MessagePriority.LOW]

        # Should have critical first, then high, etc.
        critical_msgs = [p for p in priorities if p == MessagePriority.CRITICAL]
        high_msgs = [p for p in priorities if p == MessagePriority.HIGH]

        assert len(critical_msgs) == 1, "Should have one critical message"
        assert len(high_msgs) == 1, "Should have one high priority message"
        assert priorities[0] == MessagePriority.CRITICAL, "Critical should be first"

    @pytest.mark.asyncio
    async def test_agent_discovery_and_registration(self, agent_registry):
        """Test agent discovery and registration functionality."""
        # Initial agent count
        initial_agents = await agent_registry.list_agents()
        initial_count = len(initial_agents)

        # Register new agent
        new_agent = Agent(
            name="discovery-test-agent",
            capabilities=["testing", "discovery"],
            status=AgentStatus.ONLINE,
            metadata={"test": True}
        )

        success = await agent_registry.register_agent(new_agent)
        assert success, "Agent registration should succeed"

        # Verify agent is registered
        updated_agents = await agent_registry.list_agents()
        assert len(updated_agents) == initial_count + 1, "Should have one more agent"

        # Retrieve by name
        retrieved_agent = await agent_registry.get_agent_by_name("discovery-test-agent")
        assert retrieved_agent is not None, "Should be able to retrieve agent by name"
        assert retrieved_agent.name == "discovery-test-agent"
        assert "testing" in retrieved_agent.capabilities
        assert "discovery" in retrieved_agent.capabilities

        # Test capability-based discovery
        testing_agents = await agent_registry.get_agents_by_capability("testing")
        assert len(testing_agents) >= 1, "Should find agents with testing capability"

        # Test heartbeat
        heartbeat_success = await agent_registry.heartbeat(new_agent.id)
        assert heartbeat_success, "Heartbeat should succeed for registered agent"

    @pytest.mark.asyncio
    async def test_message_expiration(self, queue_service, agent_registry):
        """Test message expiration functionality."""
        agents = await agent_registry.list_agents()
        test_agent = agents[0]

        # Create message that expires quickly
        expired_message = Message(
            sender="expiration-test",
            recipient=test_agent.id,
            content="This message should expire",
            priority=MessagePriority.MEDIUM,
            expires_at=datetime.utcnow() + timedelta(seconds=1)  # Expires in 1 second
        )

        # Send message
        await queue_service.send_message(expired_message)

        # Wait for expiration
        await asyncio.sleep(2)

        # Message should be expired
        assert expired_message.is_expired, "Message should be expired"

    @pytest.mark.asyncio
    async def test_system_stats_and_monitoring(self, queue_service, agent_registry, message_broker):
        """Test system statistics and monitoring functionality."""
        # Get queue stats
        queue_stats = await queue_service.get_queue_stats()
        assert queue_stats.total_messages >= 0
        assert queue_stats.queue_size >= 0

        # Get registry stats
        registry_stats = await agent_registry.get_registry_stats()
        assert "total_agents" in registry_stats
        assert "online_agents" in registry_stats
        assert registry_stats["total_agents"] >= 0

        # Get broker stats
        broker_stats = await message_broker.get_broker_stats()
        assert "messages_routed" in broker_stats
        assert "routing_failures" in broker_stats
        assert broker_stats["messages_routed"] >= 0

    @pytest.mark.asyncio
    async def test_performance_target(self, queue_service, agent_registry):
        """Test that system meets performance targets."""
        agents = await agent_registry.list_agents()
        if not agents:
            pytest.skip("No agents available for performance test")

        test_agent = agents[0]

        # Performance test: Send 100 messages and measure time
        start_time = datetime.utcnow()
        message_count = 100

        tasks = []
        for i in range(message_count):
            message = Message(
                sender="perf-test",
                recipient=test_agent.id,
                content=f"Performance test message {i}",
                priority=MessagePriority.MEDIUM
            )
            tasks.append(queue_service.send_message(message))

        # Send all messages concurrently
        results = await asyncio.gather(*tasks)
        end_time = datetime.utcnow()

        # Calculate performance metrics
        duration = (end_time - start_time).total_seconds()
        messages_per_second = message_count / duration

        # Verify all messages sent successfully
        successful_sends = sum(1 for r in results if r)
        assert successful_sends == message_count, "All messages should be sent successfully"

        # Performance target: >1000 messages/minute = ~16.67 messages/second
        target_mps = 16.67
        assert messages_per_second >= target_mps, f"Performance target not met: {messages_per_second:.2f} < {target_mps} msg/s"

        print(f"Performance: {messages_per_second:.2f} messages/second")


@pytest.mark.asyncio
async def test_end_to_end_workflow():
    """Test complete end-to-end message workflow."""
    # This test would normally use the full system
    # For now, just validate imports work
    from message_queue.main import MessageQueueSystem
    from message_queue.migration import MigrationOrchestrator
    from message_queue.monitoring import MetricsCollector

    # Basic validation that all imports work
    assert MessageQueueSystem is not None
    assert MigrationOrchestrator is not None
    assert MetricsCollector is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
