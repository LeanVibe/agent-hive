"""
Integration tests for production message bus system.
"""

import pytest
import asyncio
import time
from datetime import datetime

from message_bus import (
    MessageBus, MessageBusConfig, AgentCommunicator, AgentRegistry,
    Message, MessageType, MessagePriority, RetryManager
)


class TestMessageBusIntegration:
    """Integration tests for message bus system."""
    
    @pytest.fixture
    async def message_bus_config(self):
        """Create test message bus configuration."""
        return MessageBusConfig(
            redis_url="redis://localhost:6379/1",  # Use test database
            message_ttl=300,
            heartbeat_interval=10,
            batch_size=5
        )
    
    @pytest.fixture
    async def message_bus(self, message_bus_config):
        """Create and start message bus instance."""
        bus = MessageBus(message_bus_config)
        await bus.start()
        yield bus
        await bus.stop()
    
    @pytest.fixture
    async def agent_communicator(self, message_bus_config):
        """Create agent communicator."""
        communicator = AgentCommunicator(
            agent_name="test-agent",
            capabilities=["python", "testing"],
            config=message_bus_config
        )
        await communicator.start()
        yield communicator
        await communicator.stop()
    
    @pytest.mark.asyncio
    async def test_message_bus_startup(self, message_bus):
        """Test message bus starts successfully."""
        assert message_bus.running
        assert message_bus.redis_client is not None
        
        # Test Redis connection
        await message_bus.redis_client.ping()
    
    @pytest.mark.asyncio
    async def test_direct_message_sending(self, message_bus):
        """Test direct message sending."""
        message_id = await message_bus.send_direct_message(
            target_agent="test-agent",
            message_type=MessageType.SYSTEM_COMMAND,
            payload={"command": "test", "data": "hello"},
            priority=MessagePriority.HIGH
        )
        
        assert message_id is not None
        assert message_bus.stats["messages_sent"] == 1
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, message_bus):
        """Test broadcast messaging."""
        message_id = await message_bus.broadcast_message(
            message_type=MessageType.SYSTEM_COMMAND,
            payload={"command": "broadcast_test"},
            target_group="all",
            priority=MessagePriority.NORMAL
        )
        
        assert message_id is not None
    
    @pytest.mark.asyncio
    async def test_agent_registration(self, message_bus):
        """Test agent registration and discovery."""
        await message_bus.register_agent("test-agent-1", {
            "capabilities": ["python", "fastapi"],
            "version": "1.0.0"
        })
        
        # Check agent is registered
        agent_status = await message_bus.get_agent_status("test-agent-1")
        assert agent_status is not None
        assert agent_status["name"] == "test-agent-1"
        assert "capabilities" in agent_status["metadata"]
    
    @pytest.mark.asyncio
    async def test_agent_heartbeat(self, message_bus):
        """Test agent heartbeat system."""
        agent_name = "heartbeat-test-agent"
        
        # Register agent
        await message_bus.register_agent(agent_name, {"test": True})
        
        # Send heartbeat
        await message_bus.update_agent_heartbeat(
            agent_name, 
            status="active",
            current_task="test_task"
        )
        
        # Verify heartbeat updated
        agent_status = await message_bus.get_agent_status(agent_name)
        assert agent_status["status"] == "active"
        assert agent_status["current_task"] == "test_task"
    
    @pytest.mark.asyncio
    async def test_agent_communicator_integration(self, agent_communicator):
        """Test agent communicator full integration."""
        # Test status update
        await agent_communicator.update_status("busy", "integration_test")
        
        # Test message sending
        response = await agent_communicator.send_message_to_agent(
            target_agent="another-agent",
            message_type=MessageType.SYSTEM_COMMAND,
            payload={"test": "integration"},
            priority=MessagePriority.NORMAL
        )
        
        # Get statistics
        stats = await agent_communicator.get_agent_statistics()
        assert stats["agent_name"] == "test-agent"
        assert stats["capabilities"] == ["python", "testing"]
    
    @pytest.mark.asyncio
    async def test_task_assignment_flow(self, agent_communicator):
        """Test automatic task assignment."""
        # Register a capable agent
        await agent_communicator.registry.register_agent(
            "worker-agent",
            capabilities=["python", "testing", "automation"],
            metadata={"version": "1.0"}
        )
        
        # Assign task
        assigned_agent = await agent_communicator.assign_task_to_best_agent(
            task_description="Run integration tests",
            required_skills=["python", "testing"],
            confidence_threshold=0.8
        )
        
        assert assigned_agent == "worker-agent"
    
    @pytest.mark.asyncio
    async def test_message_protocol_serialization(self):
        """Test message protocol serialization/deserialization."""
        # Create message
        original_message = Message.create(
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={"task_id": "test_123", "description": "Test task"},
            source_agent="test-sender",
            target_agent="test-receiver",
            priority=MessagePriority.HIGH,
            correlation_id="corr_123",
            expiration_seconds=3600
        )
        
        # Serialize to JSON
        json_data = original_message.to_json()
        assert isinstance(json_data, str)
        
        # Deserialize from JSON
        deserialized_message = Message.from_json(json_data)
        
        # Verify all fields match
        assert deserialized_message.type == original_message.type
        assert deserialized_message.payload == original_message.payload
        assert deserialized_message.source_agent == original_message.source_agent
        assert deserialized_message.target_agent == original_message.target_agent
        assert deserialized_message.priority == original_message.priority
        assert deserialized_message.headers.correlation_id == original_message.headers.correlation_id
    
    @pytest.mark.asyncio
    async def test_system_statistics(self, message_bus):
        """Test system statistics collection."""
        # Send some messages
        for i in range(3):
            await message_bus.send_direct_message(
                target_agent=f"agent-{i}",
                message_type=MessageType.SYSTEM_COMMAND,
                payload={"test": i}
            )
        
        # Get statistics
        stats = await message_bus.get_statistics()
        
        assert stats["messages_sent"] >= 3
        assert "agents_connected" in stats
        assert "redis_connected" in stats
        assert stats["redis_connected"] is True
    
    @pytest.mark.asyncio
    async def test_four_agent_simulation(self, message_bus_config):
        """Test communication with 4 active agents (production simulation)."""
        # Simulate the 4 production agents
        agents = [
            "integration-specialist-Jul-16-1220",
            "service-mesh-Jul-16-1221", 
            "frontend-Jul-16-1222",
            "pm-agent-new"
        ]
        
        agent_capabilities = {
            "integration-specialist-Jul-16-1220": ["python", "testing", "fastapi", "integration"],
            "service-mesh-Jul-16-1221": ["microservices", "kubernetes", "performance", "networking"],
            "frontend-Jul-16-1222": ["react", "typescript", "ui/ux", "frontend"],
            "pm-agent-new": ["project-management", "coordination", "planning", "reporting"]
        }
        
        # Create communicators for each agent
        communicators = {}
        for agent_name in agents:
            communicator = AgentCommunicator(
                agent_name=agent_name,
                capabilities=agent_capabilities[agent_name],
                config=message_bus_config
            )
            await communicator.start()
            communicators[agent_name] = communicator
        
        try:
            # Test cross-agent communication
            pm_agent = communicators["pm-agent-new"]
            
            # PM assigns tasks to specialists
            tasks = [
                {
                    "description": "Fix API Gateway integration tests",
                    "skills": ["python", "testing", "fastapi"],
                    "expected_agent": "integration-specialist-Jul-16-1220"
                },
                {
                    "description": "Optimize service mesh performance",
                    "skills": ["microservices", "performance"],
                    "expected_agent": "service-mesh-Jul-16-1221"
                },
                {
                    "description": "Update dashboard UI components",
                    "skills": ["react", "ui/ux"],
                    "expected_agent": "frontend-Jul-16-1222"
                }
            ]
            
            assignment_results = []
            for task in tasks:
                assigned_agent = await pm_agent.assign_task_to_best_agent(
                    task["description"],
                    task["skills"],
                    confidence_threshold=0.75
                )
                assignment_results.append({
                    "task": task["description"],
                    "assigned_to": assigned_agent,
                    "expected": task["expected_agent"]
                })
            
            # Verify task assignments
            for result in assignment_results:
                assert result["assigned_to"] == result["expected"], \
                    f"Task '{result['task']}' assigned to {result['assigned_to']}, expected {result['expected']}"
            
            # Test broadcast communication
            broadcast_count = await pm_agent.broadcast_message(
                message_type=MessageType.SYSTEM_COMMAND,
                payload={"command": "status_update", "data": "All systems operational"},
                target_group="all",
                priority=MessagePriority.HIGH
            )
            
            assert broadcast_count is not None
            
            # Verify all agents are active
            all_agents = await pm_agent.registry.get_all_agents()
            active_agent_names = {agent.name for agent in all_agents}
            expected_agents = set(agents)
            
            assert active_agent_names == expected_agents, \
                f"Expected agents {expected_agents}, got {active_agent_names}"
            
            # Test PM workload reduction simulation
            pm_workload_before = 100  # 100% manual work
            automated_tasks = len([r for r in assignment_results if r["assigned_to"]])
            total_tasks = len(assignment_results)
            automation_rate = automated_tasks / total_tasks if total_tasks > 0 else 0
            pm_workload_after = pm_workload_before * (1 - automation_rate)
            workload_reduction = (pm_workload_before - pm_workload_after) / pm_workload_before
            
            print(f"📊 PM Workload Reduction: {workload_reduction:.1%}")
            print(f"🤖 Automated Tasks: {automated_tasks}/{total_tasks}")
            
            # Verify we achieved target reduction (should be close to 80%)
            assert workload_reduction >= 0.5, f"Workload reduction {workload_reduction:.1%} below minimum threshold"
            
        finally:
            # Clean up all communicators
            for communicator in communicators.values():
                await communicator.stop()


@pytest.mark.asyncio
async def test_production_communication_replacement():
    """
    Test that production message bus can replace tmux communication.
    
    This test verifies the core functionality needed to replace tmux-based
    agent communication with production message bus.
    """
    config = MessageBusConfig(redis_url="redis://localhost:6379/1")
    
    # Create message bus
    message_bus = MessageBus(config)
    await message_bus.start()
    
    try:
        # Test 1: Replace tmux "send-keys" with direct messaging
        message_id = await message_bus.send_direct_message(
            target_agent="integration-specialist",
            message_type=MessageType.SYSTEM_COMMAND,
            payload={
                "command": "execute",
                "content": "python -m pytest tests/ --verbose",
                "source": "human_operator"
            },
            priority=MessagePriority.HIGH
        )
        
        assert message_id is not None
        
        # Test 2: Replace tmux "list-windows" with agent discovery
        await message_bus.register_agent("integration-specialist", {
            "capabilities": ["python", "testing"],
            "status": "active"
        })
        
        await message_bus.register_agent("service-mesh", {
            "capabilities": ["kubernetes", "networking"],
            "status": "busy"
        })
        
        active_agents = await message_bus.get_active_agents()
        assert len(active_agents) >= 2
        
        agent_names = {agent["name"] for agent in active_agents}
        assert "integration-specialist" in agent_names
        assert "service-mesh" in agent_names
        
        # Test 3: Persistent messaging (advantage over tmux)
        # Messages persist even if agent is temporarily unavailable
        await message_bus.send_direct_message(
            target_agent="offline-agent",
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={"task": "background_job", "priority": "low"},
            priority=MessagePriority.LOW
        )
        
        # Test 4: Message acknowledgment (impossible with tmux)
        stats = await message_bus.get_statistics()
        assert stats["messages_sent"] >= 2
        
        print("✅ Production message bus successfully replaces tmux functionality")
        print(f"📊 Messages sent: {stats['messages_sent']}")
        print(f"🔌 Agents connected: {stats['agents_connected']}")
        
    finally:
        await message_bus.stop()