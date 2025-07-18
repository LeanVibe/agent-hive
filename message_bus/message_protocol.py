#!/usr/bin/env python3
"""
Message Bus Protocol - Hub-and-Spoke Communication System
Enhanced with Redis-compatible message classes for production scaling
Based on Gemini CLI recommendations for multi-agent coordination
"""

import json
import os
from datetime import datetime
from pathlib import Path
from enum import Enum
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid

# Production-ready message protocol classes
class MessagePriority(Enum):
    """Message priority levels for queue processing"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class MessageDeliveryStatus(Enum):
    """Message delivery status tracking"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"
    ACKNOWLEDGED = "acknowledged"

class MessageType(Enum):
    """Standard message types for agent communication"""
    TASK_ASSIGNMENT = "task_assignment"
    STATUS_UPDATE = "status_update"
    COORDINATION = "coordination"
    HEARTBEAT = "heartbeat"
    ERROR_REPORT = "error_report"
    RESOURCE_REQUEST = "resource_request"
    COMPLETION_NOTICE = "completion_notice"
    BROADCAST = "broadcast"
    INFORMATION_SHARE = "information_share"
    NOTIFICATION = "notification"

class AgentMessage(BaseModel):
    """
    Production-ready agent message format with versioning support.
    Compatible with Redis message bus and file-based systems.
    """
    version: int = 1  # For backward compatibility
    message_id: str
    from_agent: str
    to_agent: str
    message_type: str
    priority: MessagePriority
    timestamp: datetime
    ttl: int = 3600  # Time to live in seconds (1 hour default)
    body: Dict[str, Any]
    delivery_options: Optional[Dict[str, Any]] = None
    delivery_status: MessageDeliveryStatus = MessageDeliveryStatus.PENDING
    
    @classmethod
    def create(cls, from_agent: str, to_agent: str, message_type: str, 
               body: Dict[str, Any], priority: MessagePriority = MessagePriority.MEDIUM,
               ttl: int = 3600, delivery_options: Optional[Dict[str, Any]] = None):
        """Convenience method to create a new agent message"""
        return cls(
            message_id=str(uuid.uuid4()),
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            priority=priority,
            timestamp=datetime.now(),
            ttl=ttl,
            body=body,
            delivery_options=delivery_options or {}
        )

# Convenience functions for common message patterns
def create_task_assignment(from_agent: str, to_agent: str, task_description: str,
                          priority: MessagePriority = MessagePriority.MEDIUM,
                          deadline: Optional[str] = None,
                          context: Optional[Dict[str, Any]] = None) -> AgentMessage:
    """Create a standardized task assignment message"""
    return AgentMessage.create(
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=MessageType.TASK_ASSIGNMENT.value,
        body={
            "task_description": task_description,
            "deadline": deadline,
            "context": context or {},
            "assignment_id": str(uuid.uuid4()),
            "created_at": datetime.now().isoformat()
        },
        priority=priority,
        delivery_options={
            "require_ack": True,
            "max_retries": 3,
            "retry_delay": 30
        }
    )

class MessageBus:
    def __init__(self, base_path="/Users/bogdan/work/leanvibe-dev/agent-hive/message_bus"):
        self.base_path = Path(base_path)
        self.inboxes = self.base_path / "inboxes"
        self.outbox = self.base_path / "outbox"
        
        # Ensure directories exist
        self.inboxes.mkdir(parents=True, exist_ok=True)
        self.outbox.mkdir(parents=True, exist_ok=True)
    
    def send_message(self, from_agent: str, to_agent: str, message_type: str, content: str, priority: str = "normal"):
        """Send message from one agent to another"""
        
        message = {
            "timestamp": datetime.now().isoformat(),
            "from": from_agent,
            "to": to_agent,
            "type": message_type,
            "content": content,
            "priority": priority,
            "id": f"{from_agent}_{datetime.now().strftime('%H%M%S')}"
        }
        
        # Save to recipient's inbox
        inbox_file = self.inboxes / f"{to_agent}.json"
        
        messages = []
        if inbox_file.exists():
            with open(inbox_file, 'r') as f:
                messages = json.load(f)
        
        messages.append(message)
        
        with open(inbox_file, 'w') as f:
            json.dump(messages, f, indent=2)
        
        print(f"📬 Message sent: {from_agent} → {to_agent} ({message_type})")
        return message["id"]
    
    def broadcast_from_pm(self, message_type: str, content: str, agents: list, priority: str = "normal"):
        """Broadcast message from PM to multiple agents"""
        
        message_ids = []
        for agent in agents:
            msg_id = self.send_message("pm-coordinator", agent, message_type, content, priority)
            message_ids.append(msg_id)
        
        print(f"📡 Broadcast sent to {len(agents)} agents")
        return message_ids

# Convenience functions for agents
def send_to_pm(agent_id: str, message_type: str, content: str, priority: str = "normal"):
    """Send message to PM agent"""
    bus = MessageBus()
    return bus.send_message(agent_id, "pm-coordinator", message_type, content, priority)

def send_status_update(agent_id: str, status: str, task: str, result: str = ""):
    """Standardized status update to PM"""
    content = f"STATUS: {status} | TASK: {task} | RESULT: {result}"
    return send_to_pm(agent_id, "status_update", content)