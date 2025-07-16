"""
Message Protocol Specification for Agent Communication

Defines the standardized message format, types, and priorities for 
inter-agent communication in the LeanVibe Agent Hive system.
"""

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum, auto
from typing import Dict, Any, Optional, List


class MessageType(Enum):
    """Standardized message types for agent communication."""
    
    # Task management
    TASK_ASSIGNMENT = "task_assignment"
    TASK_UPDATE = "task_update" 
    TASK_COMPLETION = "task_completion"
    TASK_CANCELLATION = "task_cancellation"
    
    # Coordination
    COORDINATION_REQUEST = "coordination_request"
    COORDINATION_RESPONSE = "coordination_response"
    STATUS_UPDATE = "status_update"
    HEALTH_CHECK = "health_check"
    
    # Information sharing
    INFORMATION_SHARE = "information_share"
    QUESTION = "question"
    ANSWER = "answer"
    NOTIFICATION = "notification"
    
    # System events
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    SYSTEM_ALERT = "system_alert"
    EMERGENCY = "emergency"


class MessagePriority(Enum):
    """Message priority levels for routing and processing."""
    
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4
    EMERGENCY = 5


@dataclass
class DeliveryOptions:
    """Message delivery configuration."""
    
    require_ack: bool = True
    max_retries: int = 3
    retry_delay_seconds: int = 30
    ttl_seconds: int = 3600
    persistent: bool = True


@dataclass
class AgentMessage:
    """Standardized message format for agent communication."""
    
    # Required fields
    from_agent: str
    to_agent: str
    message_type: MessageType
    body: Dict[str, Any]
    
    # Auto-generated fields
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Optional fields
    priority: MessagePriority = MessagePriority.MEDIUM
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    delivery_options: DeliveryOptions = field(default_factory=DeliveryOptions)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate message after initialization."""
        if not self.from_agent:
            raise ValueError("from_agent cannot be empty")
        if not self.to_agent:
            raise ValueError("to_agent cannot be empty")
        if not self.body:
            raise ValueError("message body cannot be empty")
        
        # Ensure timestamp is timezone-aware
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        data = asdict(self)
        
        # Convert enums to string values
        data['message_type'] = self.message_type.value
        data['priority'] = self.priority.value
        data['timestamp'] = self.timestamp.isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Create message from dictionary."""
        # Convert string values back to enums
        data['message_type'] = MessageType(data['message_type'])
        data['priority'] = MessagePriority(data['priority'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        
        # Handle delivery_options
        if 'delivery_options' in data and isinstance(data['delivery_options'], dict):
            data['delivery_options'] = DeliveryOptions(**data['delivery_options'])
        
        return cls(**data)
    
    def create_reply(self, body: Dict[str, Any], message_type: MessageType = None) -> 'AgentMessage':
        """Create a reply message."""
        return AgentMessage(
            from_agent=self.to_agent,
            to_agent=self.from_agent,
            message_type=message_type or MessageType.ANSWER,
            body=body,
            correlation_id=self.message_id,
            reply_to=self.message_id,
            priority=self.priority
        )
    
    def is_expired(self) -> bool:
        """Check if message has expired based on TTL."""
        if not self.delivery_options.ttl_seconds:
            return False
        
        expiry_time = self.timestamp + timedelta(seconds=self.delivery_options.ttl_seconds)
        return datetime.now(timezone.utc) > expiry_time


@dataclass
class MessageDeliveryStatus:
    """Tracks delivery status of a message."""
    
    message_id: str
    status: str  # 'pending', 'delivered', 'acknowledged', 'failed', 'expired'
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    error_message: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    
    def mark_delivered(self):
        """Mark message as delivered."""
        self.status = 'delivered'
        self.last_attempt = datetime.now(timezone.utc)
        self.attempts += 1
    
    def mark_acknowledged(self):
        """Mark message as acknowledged by recipient."""
        self.status = 'acknowledged'
        self.acknowledged_at = datetime.now(timezone.utc)
    
    def mark_failed(self, error: str):
        """Mark message delivery as failed."""
        self.status = 'failed'
        self.error_message = error
        self.last_attempt = datetime.now(timezone.utc)
        self.attempts += 1
    
    def mark_expired(self):
        """Mark message as expired."""
        self.status = 'expired'


# Helper functions for common message patterns

def create_task_assignment(
    from_agent: str,
    to_agent: str, 
    task_description: str,
    priority: MessagePriority = MessagePriority.MEDIUM,
    deadline: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> AgentMessage:
    """Create a task assignment message."""
    
    body = {
        "task_description": task_description,
        "deadline": deadline,
        "context": context or {}
    }
    
    return AgentMessage(
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=MessageType.TASK_ASSIGNMENT,
        body=body,
        priority=priority
    )


def create_status_update(
    from_agent: str,
    to_agent: str,
    status: str,
    progress: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None
) -> AgentMessage:
    """Create a status update message."""
    
    body = {
        "status": status,
        "progress": progress,
        "details": details or {}
    }
    
    return AgentMessage(
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=MessageType.STATUS_UPDATE,
        body=body,
        priority=MessagePriority.LOW
    )


def create_emergency_alert(
    from_agent: str,
    alert_message: str,
    affected_systems: List[str] = None
) -> AgentMessage:
    """Create an emergency alert message broadcast."""
    
    body = {
        "alert_message": alert_message,
        "affected_systems": affected_systems or [],
        "requires_immediate_attention": True
    }
    
    return AgentMessage(
        from_agent=from_agent,
        to_agent="broadcast",  # Special routing for broadcasts
        message_type=MessageType.EMERGENCY,
        body=body,
        priority=MessagePriority.EMERGENCY,
        delivery_options=DeliveryOptions(
            require_ack=True,
            max_retries=5,
            retry_delay_seconds=10,
            ttl_seconds=300  # 5 minutes
        )
    )