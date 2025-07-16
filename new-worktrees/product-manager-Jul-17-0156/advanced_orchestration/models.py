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
    BLOCKED = "blocked"
    WAITING_DEPENDENCY = "waiting_dependency"


class LoadBalancingStrategy(Enum):
    """Load balancing strategy enumeration."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RESOURCE_BASED = "resource_based"
    CAPABILITY_BASED = "capability_based"
    WEIGHTED = "weighted"
    INTELLIGENT = "intelligent"
    PRIORITY_BASED = "priority_based"


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


class WorkflowType(Enum):
    """Workflow type enumeration."""
    DOCUMENTATION = "documentation"
    TUTORIAL = "tutorial"
    INTEGRATION = "integration"
    QUALITY = "quality"
    ARCHIVE = "archive"
    DEVELOPMENT = "development"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


class AgentSpecialization(Enum):
    """Agent specialization enumeration."""
    DOCUMENTATION = "documentation"
    TUTORIAL = "tutorial"
    INTEGRATION = "integration"
    QUALITY = "quality"
    ARCHIVE = "archive"
    DEVELOPMENT = "development"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    ORCHESTRATION = "orchestration"
    GENERAL = "general"


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 10
    HIGH = 8
    MEDIUM = 5
    LOW = 3
    BACKGROUND = 1


class DependencyType(Enum):
    """Task dependency types."""
    BLOCKING = "blocking"
    SOFT = "soft"
    RESOURCE = "resource"
    ORDERING = "ordering"


@dataclass
class TaskDependency:
    """Task dependency definition."""
    task_id: str
    depends_on: str
    dependency_type: DependencyType
    required_status: TaskStatus = TaskStatus.COMPLETED
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class WorkflowDefinition:
    """Multi-agent workflow definition."""
    workflow_id: str
    workflow_type: WorkflowType
    name: str
    description: str
    tasks: List[str]
    dependencies: List[TaskDependency]
    agent_assignments: Dict[str, AgentSpecialization]
    parallel_execution: bool = True
    max_parallel_tasks: int = 5
    estimated_duration: int = 480  # minutes
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class EnhancedTaskAssignment:
    """Enhanced task assignment with workflow context."""
    task_id: str
    workflow_id: str
    agent_id: str
    agent_specialization: AgentSpecialization
    task_data: Dict[str, Any]
    priority: TaskPriority
    dependencies: List[TaskDependency]
    estimated_duration: int  # minutes
    deadline: Optional[datetime] = None
    resource_allocation: Optional[ResourceAllocation] = None
    assignment_time: datetime = field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.ASSIGNED
    progress_percentage: float = 0.0
    quality_score: float = 0.0
    integration_points: List[str] = field(default_factory=list)


@dataclass
class AgentCapabilities:
    """Enhanced agent capabilities."""
    specialization: AgentSpecialization
    skill_level: float  # 0.0 to 1.0
    supported_workflows: List[WorkflowType]
    max_concurrent_tasks: int = 3
    preferred_task_types: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    learning_rate: float = 0.1
    adaptation_score: float = 0.5


@dataclass
class CoordinationMetrics:
    """Multi-agent coordination metrics."""
    workflow_completion_rate: float
    parallel_efficiency: float
    task_distribution_balance: float
    quality_consistency: float
    dependency_resolution_time: float
    agent_utilization: Dict[str, float]
    coordination_overhead: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class IntelligentRouting:
    """Intelligent task routing configuration."""
    use_ml_prediction: bool = True
    consider_agent_history: bool = True
    adapt_to_performance: bool = True
    quality_weight: float = 0.3
    speed_weight: float = 0.4
    resource_weight: float = 0.3
    learning_enabled: bool = True
    confidence_threshold: float = 0.8


@dataclass
class QualityGate:
    """Quality gate definition."""
    gate_id: str
    workflow_id: str
    required_tasks: List[str]
    quality_threshold: float = 0.8
    validation_criteria: List[str] = field(default_factory=list)
    blocking: bool = True
    auto_validation: bool = False
    timeout_minutes: int = 30


@dataclass
class WorkflowState:
    """Current workflow execution state."""
    workflow_id: str
    status: str
    progress_percentage: float
    active_tasks: List[str]
    completed_tasks: List[str]
    failed_tasks: List[str]
    blocked_tasks: List[str]
    quality_gates: List[QualityGate]
    coordination_metrics: CoordinationMetrics
    estimated_completion: datetime
    started_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)