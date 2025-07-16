"""
Tests for message protocol components (no Redis dependency).
"""

import pytest
import json
from datetime import datetime, timedelta

from message_bus.message_protocol import (
    Message, MessageType, MessagePriority, MessageStatus, MessageHeaders,
    create_task_assignment, create_agent_heartbeat, create_webhook_notification, create_system_command
)


class TestMessageProtocol:
    """Test message protocol without Redis dependency."""
    
    def test_message_creation(self):
        """Test basic message creation."""
        message = Message.create(
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={"task_id": "test_123", "description": "Test task"},
            source_agent="test-sender",
            target_agent="test-receiver",
            priority=MessagePriority.HIGH
        )
        
        assert message.type == MessageType.TASK_ASSIGNMENT
        assert message.payload["task_id"] == "test_123"
        assert message.source_agent == "test-sender"
        assert message.target_agent == "test-receiver"
        assert message.priority == MessagePriority.HIGH
        assert message.headers.message_id is not None
    
    def test_message_serialization(self):
        """Test message serialization to/from JSON."""
        original_message = Message.create(
            message_type=MessageType.SYSTEM_COMMAND,
            payload={"command": "ping", "data": {"test": True}},
            source_agent="sender",
            target_agent="receiver",
            priority=MessagePriority.NORMAL,
            correlation_id="corr_123",
            expiration_seconds=300
        )
        
        # Serialize to JSON
        json_data = original_message.to_json()
        assert isinstance(json_data, str)
        
        # Verify JSON is valid
        parsed_json = json.loads(json_data)
        assert "type" in parsed_json
        assert "payload" in parsed_json
        assert "headers" in parsed_json
        
        # Deserialize from JSON
        deserialized_message = Message.from_json(json_data)
        
        # Verify all fields match
        assert deserialized_message.type == original_message.type
        assert deserialized_message.payload == original_message.payload
        assert deserialized_message.source_agent == original_message.source_agent
        assert deserialized_message.target_agent == original_message.target_agent
        assert deserialized_message.priority == original_message.priority
        assert deserialized_message.headers.correlation_id == original_message.headers.correlation_id
    
    def test_message_dict_conversion(self):
        """Test message to/from dictionary conversion."""
        message = Message.create(
            message_type=MessageType.WEBHOOK_NOTIFICATION,
            payload={"event": "task_completed", "agent": "worker"},
            source_agent="system",
            priority=MessagePriority.HIGH
        )
        
        # Convert to dict
        message_dict = message.to_dict()
        assert isinstance(message_dict, dict)
        assert message_dict["type"] == "webhook_notification"
        assert message_dict["payload"]["event"] == "task_completed"
        
        # Convert back from dict
        restored_message = Message.from_dict(message_dict)
        assert restored_message.type == message.type
        assert restored_message.payload == message.payload
        assert restored_message.source_agent == message.source_agent
    
    def test_message_expiration(self):
        """Test message expiration functionality."""
        # Create message with 1 second expiration
        message = Message.create(
            message_type=MessageType.SYSTEM_COMMAND,
            payload={"command": "test"},
            expiration_seconds=1
        )
        
        # Should not be expired immediately
        assert not message.is_expired()
        
        # Create already expired message
        expired_message = Message.create(
            message_type=MessageType.SYSTEM_COMMAND,
            payload={"command": "test"},
            expiration_seconds=-1  # Already expired
        )
        
        assert expired_message.is_expired()
    
    def test_message_retry_logic(self):
        """Test message retry functionality."""
        message = Message.create(
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={"task": "test"}
        )
        
        # Initially should be retryable
        message.status = MessageStatus.FAILED
        assert message.should_retry()
        
        # Increment retries
        message.increment_retry()
        assert message.headers.retries == 1
        assert message.status == MessageStatus.RETRY
        
        # Exhaust retries
        message.headers.retries = message.headers.max_retries
        message.increment_retry()
        assert message.status == MessageStatus.DEAD_LETTER
        assert not message.should_retry()
    
    def test_message_reply_creation(self):
        """Test reply message creation."""
        original_message = Message.create(
            message_type=MessageType.RPC_REQUEST,
            payload={"method": "get_status"},
            source_agent="client",
            target_agent="server",
            correlation_id="req_123",
            reply_to="client_replies"
        )
        
        # Create reply
        reply = original_message.create_reply(
            payload={"status": "ok", "data": {"health": "good"}},
            message_type=MessageType.RPC_RESPONSE
        )
        
        assert reply.type == MessageType.RPC_RESPONSE
        assert reply.source_agent == "server"
        assert reply.target_agent == "client"
        assert reply.headers.correlation_id == original_message.headers.message_id
        assert reply.payload["status"] == "ok"
    
    def test_predefined_message_factories(self):
        """Test predefined message creation functions."""
        # Test task assignment message
        task_msg = create_task_assignment(
            task_id="task_456",
            description="Fix integration tests",
            agent="integration-specialist",
            skills=["python", "testing"],
            confidence_threshold=0.8
        )
        
        assert task_msg.type == MessageType.TASK_ASSIGNMENT
        assert task_msg.target_agent == "integration-specialist"
        assert task_msg.payload["task_id"] == "task_456"
        assert task_msg.payload["skills"] == ["python", "testing"]
        assert task_msg.priority == MessagePriority.HIGH
        
        # Test heartbeat message
        heartbeat_msg = create_agent_heartbeat(
            agent_name="worker-1",
            status="busy",
            current_task="task_789"
        )
        
        assert heartbeat_msg.type == MessageType.AGENT_HEARTBEAT
        assert heartbeat_msg.source_agent == "worker-1"
        assert heartbeat_msg.payload["status"] == "busy"
        assert heartbeat_msg.payload["current_task"] == "task_789"
        
        # Test webhook notification
        webhook_msg = create_webhook_notification(
            event_type="task_completed",
            data={"task_id": "task_123", "result": "success"},
            priority=MessagePriority.HIGH
        )
        
        assert webhook_msg.type == MessageType.WEBHOOK_NOTIFICATION
        assert webhook_msg.payload["event_type"] == "task_completed"
        assert webhook_msg.priority == MessagePriority.HIGH
        
        # Test system command
        cmd_msg = create_system_command(
            command="shutdown",
            args={"graceful": True, "timeout": 30},
            target_agent="worker-2"
        )
        
        assert cmd_msg.type == MessageType.SYSTEM_COMMAND
        assert cmd_msg.target_agent == "worker-2"
        assert cmd_msg.payload["command"] == "shutdown"
        assert cmd_msg.payload["args"]["graceful"] is True
    
    def test_message_headers(self):
        """Test message headers functionality."""
        headers = MessageHeaders(
            message_id="msg_123",
            correlation_id="corr_456",
            reply_to="replies_queue",
            routing_key="agent.worker",
            expiration=datetime.now() + timedelta(minutes=5),
            max_retries=5
        )
        
        assert headers.message_id == "msg_123"
        assert headers.correlation_id == "corr_456"
        assert headers.reply_to == "replies_queue"
        assert headers.routing_key == "agent.worker"
        assert headers.max_retries == 5
        assert headers.retries == 0
    
    def test_message_validation(self):
        """Test message validation."""
        # Valid message
        valid_message = Message.create(
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={"task": "test"},
            source_agent="sender",
            target_agent="receiver"
        )
        
        # Message should have valid structure
        assert valid_message.headers.message_id
        assert valid_message.headers.timestamp
        assert valid_message.type in MessageType
        assert valid_message.priority in MessagePriority
        assert valid_message.status in MessageStatus
    
    def test_message_string_representation(self):
        """Test message string representation."""
        message = Message.create(
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={"task": "test"},
            source_agent="sender",
            target_agent="receiver"
        )
        
        str_repr = str(message)
        assert "task_assignment" in str_repr
        assert "sender" in str_repr
        assert "receiver" in str_repr
    
    def test_message_priority_enum(self):
        """Test message priority enumeration."""
        priorities = [
            MessagePriority.LOW,
            MessagePriority.NORMAL, 
            MessagePriority.HIGH,
            MessagePriority.URGENT,
            MessagePriority.CRITICAL
        ]
        
        # Test priority values are ordered
        for i in range(len(priorities) - 1):
            assert priorities[i].value < priorities[i + 1].value
    
    def test_message_type_enum(self):
        """Test message type enumeration."""
        # Test all message types are defined
        expected_types = [
            "task_assignment",
            "task_update", 
            "task_completion",
            "agent_status",
            "agent_heartbeat",
            "system_command",
            "webhook_notification",
            "error_report",
            "metrics_update",
            "discovery_ping",
            "rpc_request",
            "rpc_response"
        ]
        
        message_type_values = [mt.value for mt in MessageType]
        
        for expected_type in expected_types:
            assert expected_type in message_type_values


def test_production_message_compatibility():
    """Test that messages are compatible with production requirements."""
    # Test message size limits
    large_payload = {"data": "x" * 10000}  # 10KB payload
    
    message = Message.create(
        message_type=MessageType.TASK_ASSIGNMENT,
        payload=large_payload
    )
    
    # Should serialize without issues
    json_data = message.to_json()
    assert len(json_data) > 10000
    
    # Should deserialize correctly
    restored = Message.from_json(json_data)
    assert restored.payload["data"] == large_payload["data"]


def test_agent_hive_message_patterns():
    """Test message patterns specific to Agent Hive system."""
    # Test PM to specialist communication pattern
    pm_to_specialist = Message.create(
        message_type=MessageType.TASK_ASSIGNMENT,
        payload={
            "task_id": "AH_2024_001",
            "description": "Implement Redis message bus integration",
            "required_skills": ["python", "redis", "message-queues"],
            "priority": "high",
            "estimated_hours": 8,
            "deadline": "2024-07-16T18:00:00Z"
        },
        source_agent="pm-agent-new",
        target_agent="integration-specialist-Jul-16-1220",
        priority=MessagePriority.HIGH,
        routing_key="tasks.integration",
        expiration_seconds=3600
    )
    
    assert pm_to_specialist.payload["task_id"].startswith("AH_")
    assert "integration" in pm_to_specialist.headers.routing_key
    assert pm_to_specialist.target_agent.startswith("integration-specialist")
    
    # Test specialist to PM status update pattern
    status_update = Message.create(
        message_type=MessageType.TASK_UPDATE,
        payload={
            "task_id": "AH_2024_001",
            "status": "in_progress",
            "progress_percentage": 75,
            "estimated_completion": "2024-07-16T17:30:00Z",
            "notes": "Message bus core implemented, testing integration"
        },
        source_agent="integration-specialist-Jul-16-1220",
        target_agent="pm-agent-new",
        priority=MessagePriority.NORMAL,
        routing_key="status.pm"
    )
    
    assert status_update.payload["progress_percentage"] == 75
    assert status_update.payload["status"] == "in_progress"
    
    # Test broadcast system notification pattern
    system_broadcast = Message.create(
        message_type=MessageType.SYSTEM_COMMAND,
        payload={
            "command": "system_maintenance",
            "args": {
                "type": "scheduled_restart",
                "start_time": "2024-07-16T20:00:00Z",
                "duration_minutes": 15,
                "affected_services": ["message_bus", "redis"]
            },
            "requires_acknowledgment": True
        },
        source_agent="system",
        target_group="all",
        priority=MessagePriority.URGENT,
        routing_key="broadcast.system"
    )
    
    assert system_broadcast.target_group == "all"
    assert system_broadcast.priority == MessagePriority.URGENT
    assert system_broadcast.payload["requires_acknowledgment"] is True
    
    print("✅ All Agent Hive message patterns validated")
    print(f"📋 PM Task Assignment: {pm_to_specialist.headers.message_id}")
    print(f"📊 Status Update: {status_update.headers.message_id}")
    print(f"📢 System Broadcast: {system_broadcast.headers.message_id}")


if __name__ == "__main__":
    # Run basic validation
    test_production_message_compatibility()
    test_agent_hive_message_patterns()
    print("🚀 Message protocol validation completed successfully!")