"""
Data models for External API Integration components.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum


class WebhookEventType(Enum):
    """Types of webhook events."""
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    AGENT_STATUS = "agent_status"
    SYSTEM_ALERT = "system_alert"
    RESOURCE_UPDATE = "resource_update"


class EventPriority(Enum):
    """Event priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class WebhookConfig:
    """Configuration for webhook server."""
    host: str = "localhost"
    port: int = 8080
    endpoint_prefix: str = "/webhooks"
    secret_key: Optional[str] = None
    timeout_seconds: int = 30
    max_payload_size: int = 1048576  # 1MB
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    def __post_init__(self):
        """Validate configuration parameters."""
        if not 1 <= self.port <= 65535:
            raise ValueError(f"Port must be between 1-65535, got {self.port}")
        if self.timeout_seconds <= 0:
            raise ValueError(f"Timeout must be positive, got {self.timeout_seconds}")
        if self.max_payload_size <= 0:
            raise ValueError(f"Max payload size must be positive, got {self.max_payload_size}")


@dataclass
class ApiGatewayConfig:
    """Configuration for API gateway."""
    host: str = "localhost"
    port: int = 8081
    api_prefix: str = "/api/v1"
    enable_cors: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    rate_limit_requests: int = 1000
    rate_limit_window: int = 3600  # 1 hour
    auth_required: bool = False
    api_key_header: str = "X-API-Key"
    request_timeout: int = 30

    def __post_init__(self):
        """Validate configuration parameters."""
        if not 1 <= self.port <= 65535:
            raise ValueError(f"Port must be between 1-65535, got {self.port}")
        if self.request_timeout <= 0:
            raise ValueError(f"Request timeout must be positive, got {self.request_timeout}")


@dataclass
class EventStreamConfig:
    """Configuration for event streaming."""
    stream_name: str = "leanvibe-events"
    buffer_size: int = 1000
    flush_interval: int = 5  # seconds
    max_retries: int = 3
    retry_delay: int = 1  # seconds
    compression_enabled: bool = True
    batch_size: int = 100
    event_ttl: int = 86400  # 24 hours

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.buffer_size <= 0:
            raise ValueError(f"Buffer size must be positive, got {self.buffer_size}")
        if self.flush_interval <= 0:
            raise ValueError(f"Flush interval must be positive, got {self.flush_interval}")
        if self.max_retries < 0:
            raise ValueError(f"Max retries must be non-negative, got {self.max_retries}")


@dataclass
class WebhookEvent:
    """Webhook event data structure."""
    event_type: WebhookEventType
    event_id: str
    timestamp: datetime
    source: str
    payload: Dict[str, Any]
    priority: EventPriority = EventPriority.MEDIUM
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        """Validate event data."""
        if not self.event_id:
            raise ValueError("Event ID cannot be empty")
        if not self.source:
            raise ValueError("Event source cannot be empty")


@dataclass
class ApiRequest:
    """API request data structure."""
    method: str
    path: str
    headers: Dict[str, str]
    query_params: Dict[str, Any]
    body: Optional[Dict[str, Any]]
    timestamp: datetime
    request_id: str
    client_ip: str

    def __post_init__(self):
        """Validate request data."""
        if self.method not in ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]:
            raise ValueError(f"Invalid HTTP method: {self.method}")
        if not self.request_id:
            raise ValueError("Request ID cannot be empty")


@dataclass
class StreamEvent:
    """Event streaming data structure."""
    event_id: str
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    partition_key: str
    priority: EventPriority = EventPriority.MEDIUM
    tags: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate stream event data."""
        if not self.event_id:
            raise ValueError("Event ID cannot be empty")
        if not self.event_type:
            raise ValueError("Event type cannot be empty")
        if not self.partition_key:
            raise ValueError("Partition key cannot be empty")


@dataclass
class WebhookDelivery:
    """Webhook delivery status tracking."""
    webhook_id: str
    event_id: str
    endpoint_url: str
    attempt_count: int
    last_attempt: datetime
    status: str  # pending, success, failed, retrying
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        """Validate delivery data."""
        if not self.webhook_id:
            raise ValueError("Webhook ID cannot be empty")
        if not self.event_id:
            raise ValueError("Event ID cannot be empty")
        if self.status not in ["pending", "success", "failed", "retrying"]:
            raise ValueError(f"Invalid status: {self.status}")


@dataclass
class ApiResponse:
    """API response data structure."""
    status_code: int
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]]
    timestamp: datetime
    processing_time: float  # milliseconds
    request_id: str

    def __post_init__(self):
        """Validate response data."""
        if not 100 <= self.status_code <= 599:
            raise ValueError(f"Invalid status code: {self.status_code}")
        if self.processing_time < 0:
            raise ValueError(f"Processing time must be non-negative, got {self.processing_time}")
