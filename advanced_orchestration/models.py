"""
Data models and types for advanced orchestration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class AgentStatus(Enum):
    """Agent status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    STARTING = "starting"
    STOPPING = "stopping"


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LoadBalancingStrategy(Enum):
    """Load balancing strategy enumeration."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RESOURCE_BASED = "resource_based"
    CAPABILITY_BASED = "capability_based"
    WEIGHTED = "weighted"


@dataclass
class ResourceRequirements:
    """Resource requirements for an agent or task."""
    cpu_cores: int = 1
    memory_mb: int = 512
    disk_mb: int = 1024
    network_mbps: int = 10


@dataclass
class ResourceAllocation:
    """Resource allocation for an agent."""
    agent_id: str
    allocated_cpu: int
    allocated_memory: int
    allocated_disk: int
    allocated_network: int
    allocation_time: datetime = field(default_factory=datetime.now)


@dataclass
class ResourceUsage:
    """Current resource usage."""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_percent: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ResourceLimits:
    """System resource limits."""
    max_cpu_cores: int = 8
    max_memory_mb: int = 8192
    max_disk_mb: int = 10240
    max_network_mbps: int = 1000
    max_agents: int = 10


@dataclass
class AgentMetadata:
    """Agent metadata."""
    agent_type: str
    version: str
    startup_time: datetime
    last_heartbeat: datetime
    capabilities: List[str]
    resource_requirements: ResourceRequirements
    custom_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRegistration:
    """Agent registration data."""
    agent_id: str
    capabilities: List[str]
    resource_requirements: ResourceRequirements
    metadata: AgentMetadata


@dataclass
class AgentInfo:
    """Complete agent information."""
    agent_id: str
    status: AgentStatus
    registration: AgentRegistration
    resource_allocation: Optional[ResourceAllocation] = None
    current_usage: Optional[ResourceUsage] = None
    active_tasks: int = 0
    error_count: int = 0
    last_heartbeat: datetime = field(default_factory=datetime.now)
    performance_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class TaskAssignment:
    """Task assignment to an agent."""
    task_id: str
    agent_id: str
    task_data: Dict[str, Any]
    priority: int
    deadline: Optional[datetime] = None
    resource_allocation: Optional[ResourceAllocation] = None
    assignment_time: datetime = field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.ASSIGNED


@dataclass
class ScalingReason:
    """Reason for scaling decision."""
    reason: str
    metric_name: str
    current_value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ScalingMetrics:
    """Scaling-related metrics."""
    current_agents: int
    target_agents: int
    queue_depth: int
    avg_response_time: float
    resource_utilization: float
    throughput: float
    error_rate: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CoordinatorConfig:
    """Configuration for MultiAgentCoordinator."""
    max_agents: int = 10
    min_agents: int = 2
    health_check_interval: float = 30.0
    load_balance_interval: float = 60.0
    task_timeout: float = 300.0
    agent_startup_timeout: float = 60.0
    failure_threshold: int = 3
    scaling_check_interval: float = 120.0
    load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.RESOURCE_BASED
    enable_auto_scaling: bool = True
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)


@dataclass
class ScalingConfig:
    """Configuration for auto-scaling."""
    scale_up_threshold: float = 0.8
    scale_down_threshold: float = 0.3
    min_agents: int = 2
    max_agents: int = 10
    cooldown_period: float = 300.0
    scale_up_step: int = 1
    scale_down_step: int = 1
    queue_depth_threshold: int = 100
    response_time_threshold: float = 5.0
    resource_threshold: float = 0.9


@dataclass
class LoadBalancingMetrics:
    """Metrics for load balancing effectiveness."""
    distribution_variance: float
    agent_utilization: Dict[str, float]
    task_completion_rate: float
    average_wait_time: float
    balancing_effectiveness: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CoordinatorState:
    """Current state of the coordinator."""
    active_agents: Dict[str, AgentInfo]
    pending_tasks: List[TaskAssignment]
    assigned_tasks: Dict[str, TaskAssignment]
    resource_usage: ResourceUsage
    scaling_metrics: ScalingMetrics
    load_balancing_metrics: LoadBalancingMetrics
    last_update: datetime = field(default_factory=datetime.now)


@dataclass
class ResourceOptimization:
    """Resource optimization recommendation."""
    agent_id: str
    current_allocation: ResourceAllocation
    recommended_allocation: ResourceAllocation
    expected_improvement: float
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)


class CoordinatorException(Exception):
    """Base exception for coordinator operations."""
    pass


class AgentRegistrationException(CoordinatorException):
    """Exception for agent registration failures."""
    pass


class ResourceAllocationException(CoordinatorException):
    """Exception for resource allocation failures."""
    pass


class TaskDistributionException(CoordinatorException):
    """Exception for task distribution failures."""
    pass


class ScalingException(CoordinatorException):
    """Exception for scaling operations."""
    pass