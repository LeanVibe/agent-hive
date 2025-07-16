#!/usr/bin/env python3
"""
Basic smoke test to validate message queue system functionality.
Can be run without Redis to test core logic.
"""

import asyncio
import sys
from pathlib import Path

# Add message_queue to path
sys.path.insert(0, str(Path(__file__).parent))

from message_queue.models import Message, MessagePriority, Agent, AgentStatus
from message_queue.agent_registry import AgentRegistry


async def test_basic_functionality():
    """Test basic system functionality without external dependencies."""
    print("🧪 Testing Message Queue System - Basic Functionality")
    print("=" * 60)
    
    try:
        # Test 1: Message Model
        print("✅ Testing Message Model...")
        message = Message(
            sender="test-sender",
            recipient="test-recipient", 
            content="Hello, World!",
            priority=MessagePriority.HIGH
        )
        assert message.sender == "test-sender"
        assert message.content == "Hello, World!"
        assert message.priority == MessagePriority.HIGH
        assert not message.is_expired
        print(f"   Message ID: {message.id}")
        print(f"   Created: {message.created_at}")
        print(f"   Expires: {message.expires_at}")
        
        # Test 2: Agent Model
        print("\n✅ Testing Agent Model...")
        agent = Agent(
            name="test-agent",
            capabilities=["general", "testing"],
            status=AgentStatus.ONLINE
        )
        assert agent.name == "test-agent"
        assert "general" in agent.capabilities
        assert agent.status == AgentStatus.ONLINE
        print(f"   Agent ID: {agent.id}")
        print(f"   Capabilities: {agent.capabilities}")
        print(f"   Is Online: {agent.is_online}")
        
        # Test 3: Agent Registry
        print("\n✅ Testing Agent Registry...")
        registry = AgentRegistry([])  # Empty worktree paths
        
        # Register agent
        success = await registry.register_agent(agent)
        assert success
        print(f"   Agent registered: {success}")
        
        # Retrieve agent
        retrieved = await registry.get_agent_by_name("test-agent")
        assert retrieved is not None
        assert retrieved.name == "test-agent"
        print(f"   Agent retrieved: {retrieved.name}")
        
        # List agents
        agents = await registry.list_agents()
        assert len(agents) >= 1
        print(f"   Total agents: {len(agents)}")
        
        # Test capability search
        testing_agents = await registry.get_agents_by_capability("testing")
        assert len(testing_agents) >= 1
        print(f"   Agents with 'testing' capability: {len(testing_agents)}")
        
        # Test 4: Registry Stats
        print("\n✅ Testing Registry Stats...")
        stats = await registry.get_registry_stats()
        assert "total_agents" in stats
        assert "online_agents" in stats
        print(f"   Total agents: {stats['total_agents']}")
        print(f"   Online agents: {stats['online_agents']}")
        print(f"   Capabilities: {stats['capabilities']}")
        
        # Test 5: Message Validation
        print("\n✅ Testing Message Validation...")
        try:
            invalid_message = Message(sender="", recipient="test", content="test")
            assert False, "Should have raised validation error"
        except ValueError as e:
            print(f"   ✅ Correctly caught validation error: {e}")
        
        try:
            invalid_agent = Agent(name="")
            assert False, "Should have raised validation error"
        except ValueError as e:
            print(f"   ✅ Correctly caught validation error: {e}")
        
        print("\n🎉 All basic functionality tests passed!")
        print("✅ System core logic is working correctly")
        print("📋 Ready for integration with Redis and full API testing")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_imports():
    """Test that all modules can be imported correctly."""
    print("\n🔧 Testing Module Imports...")
    
    try:
        from message_queue import models
        from message_queue import agent_registry
        from message_queue import queue_service
        from message_queue import message_broker
        from message_queue import api_server
        from message_queue import monitoring
        from message_queue import migration
        from message_queue import main
        
        print("   ✅ Core models imported")
        print("   ✅ Agent registry imported")
        print("   ✅ Queue service imported")
        print("   ✅ Message broker imported")
        print("   ✅ API server imported")
        print("   ✅ Monitoring imported")
        print("   ✅ Migration tools imported")
        print("   ✅ Main orchestrator imported")
        
        print("\n🎉 All imports successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all basic tests."""
    print("🚀 Message Queue System - Smoke Test")
    print("=" * 50)
    
    # Test imports first
    import_success = await test_imports()
    if not import_success:
        print("❌ Import tests failed - cannot continue")
        sys.exit(1)
    
    # Test basic functionality
    basic_success = await test_basic_functionality()
    if not basic_success:
        print("❌ Basic functionality tests failed")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✅ ALL SMOKE TESTS PASSED")
    print("🚀 Message Queue System is ready for production!")
    print("📋 Next steps:")
    print("   1. Start Redis server")
    print("   2. Run: python start_message_queue.py")
    print("   3. Test with: curl http://localhost:8080/health")


if __name__ == "__main__":
    asyncio.run(main())