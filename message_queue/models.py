"""
Data models for the Message Queue System.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
import uuid


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MessageStatus(Enum):
    """Message delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRY = "retry"
    EXPIRED = "expired"


class AgentStatus(Enum):
    """Agent availability status."""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    IDLE = "idle"
    ERROR = "error"


@dataclass
class Message:
    """Core message data structure."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    recipient: str = ""
    content: str = ""
    priority: MessagePriority = MessagePriority.MEDIUM
    status: MessageStatus = MessageStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    delivery_attempts: int = 0
    max_attempts: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate message data."""
        if not self.sender:
            raise ValueError("Message sender cannot be empty")
        if not self.recipient:
            raise ValueError("Message recipient cannot be empty")
        if not self.content:
            raise ValueError("Message content cannot be empty")

        # Set default expiration if not provided (24 hours)
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(hours=24)

    @property
    def is_expired(self) -> bool:
        """Check if message has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def can_retry(self) -> bool:
        """Check if message can be retried."""
        return (self.delivery_attempts < self.max_attempts and
                not self.is_expired and
                self.status in [MessageStatus.PENDING, MessageStatus.FAILED])


@dataclass
class Agent:
    """Agent registry entry."""
    id: str = ""
    name: str = ""
    capabilities: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.OFFLINE
    last_seen: datetime = field(default_factory=datetime.utcnow)
    worktree_path: Optional[str] = None
    endpoint: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate agent data."""
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.name:
            raise ValueError("Agent name cannot be empty")

    @property
    def is_online(self) -> bool:
        """Check if agent is considered online."""
        # Agent is online if last seen within 5 minutes
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        return self.status == AgentStatus.ONLINE and self.last_seen > cutoff


@dataclass
class DeliveryReceipt:
    """Message delivery confirmation."""
    message_id: str = ""
    agent_id: str = ""
    delivered_at: datetime = field(default_factory=datetime.utcnow)
    acknowledgment_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate delivery receipt."""
        if not self.message_id:
            raise ValueError("Message ID cannot be empty")
        if not self.agent_id:
            raise ValueError("Agent ID cannot be empty")


@dataclass
class QueueConfig:
    """Message queue configuration."""
    name: str = "agent-messages"
    max_size: int = 10000
    message_ttl: int = 86400  # 24 hours in seconds
    retry_delay: int = 60  # 1 minute
    max_retry_attempts: int = 3
    enable_persistence: bool = True
    persistence_backend: str = "redis"  # redis, sqlite, memory

    def __post_init__(self):
        """Validate queue configuration."""
        if self.max_size <= 0:
            raise ValueError("Queue max size must be positive")
        if self.message_ttl <= 0:
            raise ValueError("Message TTL must be positive")
        if self.retry_delay < 0:
            raise ValueError("Retry delay must be non-negative")


@dataclass
class MessageQueueStats:
    """Message queue statistics."""
    total_messages: int = 0
    pending_messages: int = 0
    delivered_messages: int = 0
    failed_messages: int = 0
    active_agents: int = 0
    queue_size: int = 0
    average_delivery_time: float = 0.0  # milliseconds
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BroadcastMessage:
    """Message for broadcasting to multiple agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    recipients: List[str] = field(default_factory=list)  # Empty list = all agents
    content: str = ""
    priority: MessagePriority = MessagePriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate broadcast message."""
        if not self.sender:
            raise ValueError("Broadcast sender cannot be empty")
        if not self.content:
            raise ValueError("Broadcast content cannot be empty")

        # Set default expiration if not provided (24 hours)
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(hours=24)

    def to_individual_messages(self, agent_ids: List[str]) -> List[Message]:
        """Convert broadcast to individual messages."""
        messages = []
        target_agents = self.recipients if self.recipients else agent_ids

        for agent_id in target_agents:
            message = Message(
                sender=self.sender,
                recipient=agent_id,
                content=self.content,
                priority=self.priority,
                expires_at=self.expires_at,
                metadata={**self.metadata, "broadcast_id": self.id}
            )
            messages.append(message)

        return messages
