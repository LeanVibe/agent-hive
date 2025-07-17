"""
Message Protocol for Production Agent Communication

Defines message structure, types, and serialization for reliable agent communication.
"""

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Union


class MessageType(Enum):
    """Message types for agent communication."""
    TASK_ASSIGNMENT = "task_assignment"
    TASK_UPDATE = "task_update"
    TASK_COMPLETION = "task_completion"
    AGENT_STATUS = "agent_status"
    AGENT_HEARTBEAT = "agent_heartbeat"
    SYSTEM_COMMAND = "system_command"
    WEBHOOK_NOTIFICATION = "webhook_notification"
    ERROR_REPORT = "error_report"
    METRICS_UPDATE = "metrics_update"
    DISCOVERY_PING = "discovery_ping"
    RPC_REQUEST = "rpc_request"
    RPC_RESPONSE = "rpc_response"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class MessageStatus(Enum):
    """Message processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    DEAD_LETTER = "dead_letter"


@dataclass
class MessageHeaders:
    """Message headers for routing and metadata."""
    message_id: str
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    routing_key: str = "default"
    content_type: str = "application/json"
    encoding: str = "utf-8"
    timestamp: datetime = None
    expiration: Optional[datetime] = None
    retries: int = 0
    max_retries: int = 3

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Message:
    """
    Production message structure for agent communication.

    Provides reliable, traceable message passing with acknowledgment support.
    """
    type: MessageType
    payload: Dict[str, Any]
    headers: MessageHeaders
    priority: MessagePriority = MessagePriority.NORMAL
    source_agent: str = "system"
    target_agent: Optional[str] = None
    target_group: Optional[str] = None
    status: MessageStatus = MessageStatus.PENDING

    def __post_init__(self):
        """Initialize message with defaults."""
        if not isinstance(self.type, MessageType):
            self.type = MessageType(self.type)
        if not isinstance(self.priority, MessagePriority):
            self.priority = MessagePriority(self.priority)
        if not isinstance(self.status, MessageStatus):
            self.status = MessageStatus(self.status)

    @classmethod
    def create(cls,
               message_type: Union[MessageType, str],
               payload: Dict[str, Any],
               source_agent: str = "system",
               target_agent: Optional[str] = None,
               target_group: Optional[str] = None,
               priority: Union[MessagePriority, int] = MessagePriority.NORMAL,
               correlation_id: Optional[str] = None,
               reply_to: Optional[str] = None,
               routing_key: str = "default",
               expiration_seconds: Optional[int] = None) -> "Message":
        """
        Create a new message with automatic header generation.

        Args:
            message_type: Type of message
            payload: Message payload data
            source_agent: Source agent name
            target_agent: Target agent name (for direct messaging)
            target_group: Target group name (for broadcast)
            priority: Message priority
            correlation_id: Correlation ID for request/response
            reply_to: Reply-to queue name
            routing_key: Message routing key
            expiration_seconds: Message expiration in seconds

        Returns:
            New message instance
        """
        message_id = str(uuid.uuid4())

        expiration = None
        if expiration_seconds:
            expiration = datetime.now() + timedelta(seconds=expiration_seconds)

        headers = MessageHeaders(
            message_id=message_id,
            correlation_id=correlation_id,
            reply_to=reply_to,
            routing_key=routing_key,
            expiration=expiration
        )

        if isinstance(message_type, str):
            message_type = MessageType(message_type)
        if isinstance(priority, int):
            priority = MessagePriority(priority)

        return cls(
            type=message_type,
            payload=payload,
            headers=headers,
            priority=priority,
            source_agent=source_agent,
            target_agent=target_agent,
            target_group=target_group
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize message to dictionary."""
        return {
            "type": self.type.value,
            "payload": self.payload,
            "headers": {
                "message_id": self.headers.message_id,
                "correlation_id": self.headers.correlation_id,
                "reply_to": self.headers.reply_to,
                "routing_key": self.headers.routing_key,
                "content_type": self.headers.content_type,
                "encoding": self.headers.encoding,
                "timestamp": self.headers.timestamp.isoformat(),
                "expiration": self.headers.expiration.isoformat() if self.headers.expiration else None,
                "retries": self.headers.retries,
                "max_retries": self.headers.max_retries
            },
            "priority": self.priority.value,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "target_group": self.target_group,
            "status": self.status.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Deserialize message from dictionary."""
        headers_data = data["headers"]
        headers = MessageHeaders(
            message_id=headers_data["message_id"],
            correlation_id=headers_data.get("correlation_id"),
            reply_to=headers_data.get("reply_to"),
            routing_key=headers_data.get("routing_key", "default"),
            content_type=headers_data.get("content_type", "application/json"),
            encoding=headers_data.get("encoding", "utf-8"),
            timestamp=datetime.fromisoformat(headers_data["timestamp"]),
            expiration=datetime.fromisoformat(headers_data["expiration"]) if headers_data.get("expiration") else None,
            retries=headers_data.get("retries", 0),
            max_retries=headers_data.get("max_retries", 3)
        )

        return cls(
            type=MessageType(data["type"]),
            payload=data["payload"],
            headers=headers,
            priority=MessagePriority(data["priority"]),
            source_agent=data["source_agent"],
            target_agent=data.get("target_agent"),
            target_group=data.get("target_group"),
            status=MessageStatus(data.get("status", "pending"))
        )

    def to_json(self) -> str:
        """Serialize message to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        """Deserialize message from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def is_expired(self) -> bool:
        """Check if message has expired."""
        if not self.headers.expiration:
            return False
        return datetime.now() > self.headers.expiration

    def should_retry(self) -> bool:
        """Check if message should be retried."""
        return (self.status == MessageStatus.FAILED and
                self.headers.retries < self.headers.max_retries and
                not self.is_expired())

    def increment_retry(self) -> None:
        """Increment retry count."""
        self.headers.retries += 1
        if self.headers.retries >= self.headers.max_retries:
            self.status = MessageStatus.DEAD_LETTER
        else:
            self.status = MessageStatus.RETRY

    def create_reply(self, payload: Dict[str, Any],
                    message_type: MessageType = MessageType.RPC_RESPONSE) -> "Message":
        """
        Create a reply message.

        Args:
            payload: Reply payload
            message_type: Reply message type

        Returns:
            Reply message
        """
        return Message.create(
            message_type=message_type,
            payload=payload,
            source_agent=self.target_agent or "system",
            target_agent=self.source_agent,
            correlation_id=self.headers.message_id,
            routing_key=self.headers.reply_to or "replies"
        )

    def __str__(self) -> str:
        """String representation of message."""
        target = self.target_agent or self.target_group or "broadcast"
        return f"Message({self.type.value}: {self.source_agent} -> {target})"


# Predefined message factory functions for common use cases

def create_task_assignment(task_id: str, description: str, agent: str,
                          skills: List[str], confidence_threshold: float = 0.75) -> Message:
    """Create a task assignment message."""
    return Message.create(
        message_type=MessageType.TASK_ASSIGNMENT,
        payload={
            "task_id": task_id,
            "description": description,
            "skills": skills,
            "confidence_threshold": confidence_threshold,
            "created_at": datetime.now().isoformat()
        },
        target_agent=agent,
        priority=MessagePriority.HIGH,
        routing_key=f"tasks.{agent}",
        expiration_seconds=3600  # 1 hour
    )


def create_agent_heartbeat(agent_name: str, status: str, current_task: Optional[str] = None) -> Message:
    """Create an agent heartbeat message."""
    return Message.create(
        message_type=MessageType.AGENT_HEARTBEAT,
        payload={
            "agent_name": agent_name,
            "status": status,
            "current_task": current_task,
            "timestamp": datetime.now().isoformat()
        },
        source_agent=agent_name,
        routing_key="heartbeats",
        expiration_seconds=60  # 1 minute
    )


def create_webhook_notification(event_type: str, data: Dict[str, Any],
                               priority: MessagePriority = MessagePriority.NORMAL) -> Message:
    """Create a webhook notification message."""
    return Message.create(
        message_type=MessageType.WEBHOOK_NOTIFICATION,
        payload={
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        },
        priority=priority,
        routing_key=f"webhooks.{event_type}",
        expiration_seconds=300  # 5 minutes
    )


def create_system_command(command: str, args: Dict[str, Any],
                         target_agent: Optional[str] = None) -> Message:
    """Create a system command message."""
    return Message.create(
        message_type=MessageType.SYSTEM_COMMAND,
        payload={
            "command": command,
            "args": args,
            "timestamp": datetime.now().isoformat()
        },
        target_agent=target_agent,
        target_group="all" if target_agent is None else None,
        priority=MessagePriority.HIGH,
        routing_key="system.commands",
        expiration_seconds=600  # 10 minutes
    )
