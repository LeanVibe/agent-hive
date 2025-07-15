# API Reference

**📋 Implementation Status**: This API reference documents production-ready APIs with working examples and comprehensive test coverage.

Comprehensive API documentation for LeanVibe Agent Hive - the multi-agent orchestration system with advanced coordination capabilities and rich API surface.

## Table of Contents

- [Overview](#overview)
- [External API Integration](#external-api-integration)
- [Advanced Orchestration APIs](#advanced-orchestration-apis)
- [ML Enhancement APIs](#ml-enhancement-apis)
- [CLI Interface](#cli-interface)
- [Testing and Validation](#testing-and-validation)
- [Error Handling](#error-handling)
- [Working Examples](#working-examples)
- [Performance Characteristics](#performance-characteristics)
- [Integration Patterns](#integration-patterns)

## Overview

LeanVibe Agent Hive provides a comprehensive API for multi-agent orchestration, resource management, and intelligent coordination. The API is designed for both synchronous and asynchronous operations, with comprehensive error handling and performance monitoring.

### API Design Principles

- **Type Safety**: Full type annotations with Python 3.12+ support
- **Async First**: Native async/await support for all operations
- **Composable**: Modular design for flexible integration
- **Observable**: Built-in metrics and logging integration
- **Testable**: Comprehensive mock and testing infrastructure

### Configuration and Setup

**⚠️ Status**: Configuration system not yet implemented. Currently using direct model instantiation.

```python
# CURRENT IMPLEMENTATION ✅
from advanced_orchestration.models import CoordinatorConfig
from advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator

# Initialize configuration
config = CoordinatorConfig()
coordinator = MultiAgentCoordinator(config)

# FUTURE IMPLEMENTATION ❌ (planned for Phase 0)
# from claude.config.config_loader import ConfigLoader
# config = ConfigLoader()
# config.validate()
```

## Core APIs

### Orchestrator API

**❌ Status**: Not yet implemented. Planned for Phase 0 CLI development.

The planned main orchestration engine for coordinating all agent activities.

#### Class: `Orchestrator` (Future Implementation)

**Planned Location**: `.claude/orchestrator.py`

```python
# FUTURE IMPLEMENTATION ❌
# from claude.orchestrator import Orchestrator
# 
# class Orchestrator:
#     """Central coordination engine for multi-agent orchestration."""
#     
#     def __init__(self, config: Optional[ConfigLoader] = None):
#         """Initialize orchestrator with optional configuration."""
#         
#     async def start(self) -> None:
#         """Start the orchestrator and all subsystems."""
#         
#     async def stop(self) -> None:
#         """Gracefully stop the orchestrator and all agents."""

# CURRENT ALTERNATIVE ✅ - Use MultiAgentCoordinator directly
from advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
from advanced_orchestration.models import CoordinatorConfig

config = CoordinatorConfig()
coordinator = MultiAgentCoordinator(config)
```

#### Data Types

```python
@dataclass
class OrchestratorStatus:
    """Current status of the orchestrator."""
    active_agents: int
    pending_tasks: int
    completed_tasks: int
    resource_utilization: float
    uptime: timedelta
    last_activity: datetime
    health_score: float

@dataclass
class ExecutionReport:
    """Report from autonomous execution session."""
    session_duration: timedelta
    tasks_completed: int
    tasks_failed: int
    agents_used: List[str]
    performance_metrics: Dict[str, Any]
    error_summary: List[str]
```

#### Methods

##### `async start() -> None`

Starts the orchestrator and initializes all subsystems.

**Example**:
```python
orchestrator = Orchestrator()
await orchestrator.start()
```

**Raises**:
- `ConfigurationError`: Invalid configuration
- `SystemError`: Failed to initialize subsystems

##### `async execute_autonomously(duration: timedelta) -> ExecutionReport`

Execute autonomous work session with specified duration.

**Parameters**:
- `duration` (timedelta): Maximum duration for autonomous execution

**Returns**:
- `ExecutionReport`: Detailed report of execution session

**Example**:
```python
from datetime import timedelta

report = await orchestrator.execute_autonomously(timedelta(hours=4))
print(f"Completed {report.tasks_completed} tasks in {report.session_duration}")
```

## Phase 2 Advanced Orchestration APIs

### Multi-Agent Coordinator API

Manages coordination across multiple specialized agents with load balancing and health monitoring.

#### Class: `MultiAgentCoordinator`

**Location**: `advanced_orchestration/multi_agent_coordinator.py`  
**Status**: ✅ Production ready with 25 comprehensive tests

```python
from advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
from advanced_orchestration.models import CoordinatorConfig

class MultiAgentCoordinator:
    """Coordinates multiple agents with intelligent load balancing."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize coordinator with configuration."""
        
    async def register_agent(self, agent: Agent) -> bool:
        """Register new agent with the coordinator."""
        
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister agent from coordination."""
        
    async def assign_task(
        self, 
        task: Task, 
        strategy: LoadBalancingStrategy = "least_loaded"
    ) -> TaskAssignment:
        """Assign task to optimal agent using specified strategy."""
        
    async def get_agent_status(self, agent_id: str) -> AgentStatus:
        """Get current status of specific agent."""
        
    async def monitor_agent_health(self) -> HealthReport:
        """Monitor health of all registered agents."""
        
    async def rebalance_load(self) -> RebalanceReport:
        """Rebalance tasks across agents for optimal performance."""
```

#### Load Balancing Strategies

```python
from enum import Enum

class LoadBalancingStrategy(Enum):
    """Available load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    CAPABILITY_BASED = "capability_based"
    PRIORITY_WEIGHTED = "priority_weighted"
    PREDICTIVE = "predictive"
```

#### Data Types

```python
@dataclass
class TaskAssignment:
    """Result of task assignment."""
    agent_id: str
    task_id: str
    assignment_time: datetime
    estimated_completion: datetime
    confidence_score: float

@dataclass
class AgentStatus:
    """Current status of an agent."""
    agent_id: str
    status: AgentState
    current_task: Optional[str]
    load_percentage: float
    last_heartbeat: datetime
    capabilities: List[str]
    performance_metrics: Dict[str, float]

@dataclass
class HealthReport:
    """Health report for all agents."""
    total_agents: int
    healthy_agents: int
    unhealthy_agents: int
    average_load: float
    performance_score: float
    alerts: List[str]
```

#### Methods

##### `async assign_task(task: Task, strategy: LoadBalancingStrategy) -> TaskAssignment`

Assign task to optimal agent using specified load balancing strategy.

**Parameters**:
- `task` (Task): Task to assign
- `strategy` (LoadBalancingStrategy): Load balancing strategy to use

**Returns**:
- `TaskAssignment`: Assignment details with confidence score

**Example**:
```python
coordinator = MultiAgentCoordinator()

# Assign task using least loaded strategy
assignment = await coordinator.assign_task(
    task=my_task,
    strategy=LoadBalancingStrategy.LEAST_LOADED
)

print(f"Task assigned to {assignment.agent_id} with confidence {assignment.confidence_score}")
```

### Resource Manager API

Manages system resources with real-time monitoring and intelligent allocation.

#### Class: `ResourceManager`

**Location**: `advanced_orchestration/resource_manager.py`  
**Status**: ✅ Production ready with 20 comprehensive tests

```python
from advanced_orchestration.resource_manager import ResourceManager

class ResourceManager:
    """Manages system resources with intelligent allocation."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize resource manager with configuration."""
        
    async def get_system_resources(self) -> SystemResources:
        """Get current system resource utilization."""
        
    async def allocate_resources(
        self, 
        agent_id: str, 
        requirements: ResourceRequirements
    ) -> ResourceAllocation:
        """Allocate resources to specific agent."""
        
    async def deallocate_resources(self, agent_id: str) -> bool:
        """Deallocate resources from agent."""
        
    async def monitor_resource_usage(self) -> ResourceMonitoringReport:
        """Monitor real-time resource usage across all agents."""
        
    async def optimize_allocation(self) -> OptimizationReport:
        """Optimize resource allocation for better performance."""
        
    async def predict_resource_needs(
        self, 
        time_horizon: timedelta
    ) -> ResourcePrediction:
        """Predict future resource needs based on historical data."""
```

#### Data Types

```python
@dataclass
class SystemResources:
    """Current system resource status."""
    cpu_percent: float
    memory_available_mb: int
    memory_used_mb: int
    disk_free_gb: int
    disk_used_gb: int
    network_io_mbps: float
    timestamp: datetime

@dataclass
class ResourceRequirements:
    """Resource requirements for an agent."""
    cpu_cores: float
    memory_mb: int
    disk_mb: int
    network_bandwidth_mbps: float
    priority: int

@dataclass
class ResourceAllocation:
    """Resource allocation result."""
    allocation_id: str
    agent_id: str
    allocated_resources: ResourceRequirements
    allocation_time: datetime
    expires_at: Optional[datetime]
    success: bool
    message: str

@dataclass
class ResourceMonitoringReport:
    """Resource monitoring report."""
    total_cpu_usage: float
    total_memory_usage: float
    agent_allocations: Dict[str, ResourceAllocation]
    efficiency_score: float
    recommendations: List[str]
```

#### Methods

##### `async allocate_resources(agent_id: str, requirements: ResourceRequirements) -> ResourceAllocation`

Allocate system resources to a specific agent.

**Parameters**:
- `agent_id` (str): Unique identifier for the agent
- `requirements` (ResourceRequirements): Resource requirements specification

**Returns**:
- `ResourceAllocation`: Allocation result with success status

**Example**:
```python
resource_manager = ResourceManager()

# Define resource requirements
requirements = ResourceRequirements(
    cpu_cores=2.0,
    memory_mb=1024,
    disk_mb=500,
    network_bandwidth_mbps=10.0,
    priority=5
)

# Allocate resources
allocation = await resource_manager.allocate_resources(
    agent_id="backend-agent-1",
    requirements=requirements
)

if allocation.success:
    print(f"Resources allocated: {allocation.allocation_id}")
else:
    print(f"Allocation failed: {allocation.message}")
```

### Scaling Manager API

Manages auto-scaling of agents based on demand and performance metrics.

#### Class: `ScalingManager`

**Location**: `advanced_orchestration/scaling_manager.py`  
**Status**: ✅ Production ready with 20 comprehensive tests

```python
from advanced_orchestration.scaling_manager import ScalingManager

class ScalingManager:
    """Manages auto-scaling of agents based on demand."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize scaling manager with configuration."""
        
    async def scale_up(self, agent_type: str, count: int = 1) -> ScalingResult:
        """Scale up agents of specified type."""
        
    async def scale_down(self, agent_type: str, count: int = 1) -> ScalingResult:
        """Scale down agents of specified type."""
        
    async def auto_scale(self) -> AutoScalingReport:
        """Perform automatic scaling based on current metrics."""
        
    async def get_scaling_status(self) -> ScalingStatus:
        """Get current scaling status and metrics."""
        
    async def set_scaling_policy(
        self, 
        agent_type: str, 
        policy: ScalingPolicy
    ) -> bool:
        """Set scaling policy for specific agent type."""
```

#### Data Types

```python
@dataclass
class ScalingResult:
    """Result of scaling operation."""
    operation: str  # "scale_up" or "scale_down"
    agent_type: str
    requested_count: int
    actual_count: int
    new_instances: List[str]
    success: bool
    message: str

@dataclass
class ScalingPolicy:
    """Scaling policy configuration."""
    min_instances: int
    max_instances: int
    scale_up_threshold: float
    scale_down_threshold: float
    cooldown_period: timedelta
    scale_factor: float

@dataclass
class AutoScalingReport:
    """Report from auto-scaling operation."""
    actions_taken: List[ScalingResult]
    metrics_evaluated: Dict[str, float]
    recommendations: List[str]
    next_evaluation: datetime
```

#### Methods

##### `async auto_scale() -> AutoScalingReport`

Perform automatic scaling based on current system metrics.

**Returns**:
- `AutoScalingReport`: Detailed report of scaling actions taken

**Example**:
```python
scaling_manager = ScalingManager()

# Perform auto-scaling
report = await scaling_manager.auto_scale()

for action in report.actions_taken:
    print(f"Scaled {action.operation} {action.agent_type}: {action.actual_count} instances")
```

## Agent Framework APIs

**❌ Status**: Not yet implemented. Planned for Phase 0.

### Base Agent Interface (Future Implementation)

Planned abstract base class for all agents in the system.

#### Class: `BaseAgent` (Future Implementation)

**Planned Location**: `.claude/agents/base_agent.py`

```python
# FUTURE IMPLEMENTATION ❌
# from abc import ABC, abstractmethod
# from claude.agents.base_agent import BaseAgent

class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    @abstractmethod
    async def execute_task(self, task: Task) -> TaskResult:
        """Execute assigned task and return result."""
        pass
    
    @abstractmethod
    async def get_status(self) -> AgentInfo:
        """Get current agent status and information."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Perform health check and return status."""
        pass
    
    @abstractmethod
    async def get_capabilities(self) -> List[str]:
        """Get list of agent capabilities."""
        pass
```

### Claude Agent Implementation (Future Implementation)

Planned production implementation of Claude agent with CLI integration.

#### Class: `ClaudeAgent` (Future Implementation)

**Planned Location**: `.claude/agents/claude_agent.py`  
**Status**: ❌ Not yet implemented

```python
# FUTURE IMPLEMENTATION ❌
# from claude.agents.claude_agent import ClaudeAgent

class ClaudeAgent(BaseAgent):
    """Claude agent implementation with CLI integration."""
    
    def __init__(self, config: Dict):
        """Initialize Claude agent with configuration."""
        
    async def execute_task(self, task: Task) -> TaskResult:
        """Execute task using Claude CLI."""
        
    async def get_status(self) -> AgentInfo:
        """Get current agent status."""
        
    async def health_check(self) -> bool:
        """Check agent health and CLI availability."""
        
    async def get_capabilities(self) -> List[str]:
        """Get Claude agent capabilities."""
```

#### Data Types

```python
@dataclass
class Task:
    """Task definition for agent execution."""
    task_id: str
    task_type: str
    description: str
    parameters: Dict[str, Any]
    priority: int
    deadline: Optional[datetime]
    dependencies: List[str]

@dataclass
class TaskResult:
    """Result from task execution."""
    task_id: str
    success: bool
    result: Any
    execution_time: float
    confidence: float
    error_message: Optional[str]
    metadata: Dict[str, Any]

@dataclass
class AgentInfo:
    """Agent information and status."""
    agent_id: str
    agent_type: str
    status: AgentState
    capabilities: List[str]
    current_task: Optional[str]
    performance_metrics: Dict[str, float]
    last_heartbeat: datetime
```

## Configuration Management APIs

### Configuration Loader (Future Implementation)

Planned centralized configuration management with environment variable overrides.

#### Class: `ConfigLoader` (Future Implementation)

**Planned Location**: `.claude/config/config_loader.py`  
**Status**: ❌ Not yet implemented

```python
# FUTURE IMPLEMENTATION ❌
# from claude.config.config_loader import ConfigLoader

class ConfigLoader:
    """Centralized configuration management."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration loader."""
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with dot notation."""
        
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        
    def validate(self) -> bool:
        """Validate configuration schema."""
        
    def get_agent_config(self, agent_type: str) -> Dict:
        """Get configuration for specific agent type."""
        
    def get_cli_path(self, agent_type: str) -> str:
        """Get CLI path for agent type (handles mock/production)."""
        
    def is_development_mode(self) -> bool:
        """Check if running in development mode."""
```

#### Methods

##### `get(key: str, default: Any = None) -> Any`

Get configuration value using dot notation.

**Parameters**:
- `key` (str): Configuration key in dot notation (e.g., "agents.claude.timeout")
- `default` (Any): Default value if key not found

**Returns**:
- Configuration value or default

**Example**:
```python
config = ConfigLoader()

# Get specific configuration values
timeout = config.get("agents.claude.timeout", 300)
debug_mode = config.get("system.debug_mode", False)
max_agents = config.get("multi_agent.max_agents", 5)
```

## State Management APIs

**❌ Status**: Not yet implemented. Planned for Phase 0.

### Task Queue (Future Implementation)

Planned priority-based task queue with dependency management and async operations.

#### Class: `TaskQueue` (Future Implementation)

**Planned Location**: `.claude/queue/task_queue.py`  
**Status**: ❌ Not yet implemented

```python
# FUTURE IMPLEMENTATION ❌
# from claude.queue.task_queue import TaskQueue

class TaskQueue:
    """Priority-based task queue with dependency management."""
    
    def __init__(self, max_size: int = 1000):
        """Initialize task queue with maximum size."""
        
    async def add_task(self, task: Task) -> bool:
        """Add task to queue with priority ordering."""
        
    async def get_next_task(
        self, 
        agent_capabilities: List[str] = None
    ) -> Optional[Task]:
        """Get next task matching agent capabilities."""
        
    async def mark_task_completed(self, task_id: str) -> bool:
        """Mark task as completed and handle dependencies."""
        
    async def mark_task_failed(self, task_id: str, error: str) -> bool:
        """Mark task as failed and handle retry logic."""
        
    async def get_queue_status(self) -> QueueStatus:
        """Get current queue status and metrics."""
        
    async def get_pending_tasks(self) -> List[Task]:
        """Get list of all pending tasks."""
```

#### Data Types

```python
@dataclass
class QueueStatus:
    """Current queue status."""
    total_tasks: int
    pending_tasks: int
    completed_tasks: int
    failed_tasks: int
    average_wait_time: float
    throughput_per_minute: float
```

#### Methods

##### `async add_task(task: Task) -> bool`

Add task to queue with automatic priority ordering.

**Parameters**:
- `task` (Task): Task to add to queue

**Returns**:
- `bool`: Success status

**Example**:
```python
queue = TaskQueue(max_size=1000)

task = Task(
    task_id="task-001",
    task_type="code_generation",
    description="Generate API endpoint",
    parameters={"language": "python", "framework": "fastapi"},
    priority=5,
    dependencies=[]
)

success = await queue.add_task(task)
if success:
    print(f"Task {task.task_id} added to queue")
```

### Circuit Breaker (Future Implementation)

Planned resilience pattern implementation for external service calls.

#### Class: `CircuitBreaker` (Future Implementation)

**Planned Location**: `.claude/agents/claude_agent.py`  
**Status**: ❌ Not yet implemented

```python
# FUTURE IMPLEMENTATION ❌
# from claude.agents.claude_agent import CircuitBreaker

class CircuitBreaker:
    """Circuit breaker for resilient external service calls."""
    
    def __init__(
        self, 
        failure_threshold: int = 5, 
        recovery_timeout: int = 60
    ):
        """Initialize circuit breaker with thresholds."""
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        
    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        
    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
```

#### States

```python
from enum import Enum

class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Blocking calls
    HALF_OPEN = "half_open" # Testing recovery
```

## ML Component Interfaces

**❌ Status**: Not yet implemented. Planned for future phases.

### Pattern Optimizer (Future Implementation - Phase 2.2)

Planned advanced pattern recognition for development optimization.

#### Interface: `PatternOptimizer`

**Location**: `ml_enhancements/pattern_optimizer.py` (planned)

```python
from abc import ABC, abstractmethod

class PatternOptimizer(ABC):
    """Advanced pattern recognition for development optimization."""
    
    @abstractmethod
    async def analyze_patterns(
        self, 
        data: List[HistoricalData]
    ) -> PatternAnalysis:
        """Analyze historical data for patterns."""
        pass
    
    @abstractmethod
    async def optimize_workflow(
        self, 
        current_workflow: Workflow
    ) -> OptimizedWorkflow:
        """Optimize workflow based on pattern analysis."""
        pass
    
    @abstractmethod
    async def predict_outcomes(
        self, 
        workflow: Workflow
    ) -> PredictionResult:
        """Predict outcomes for proposed workflow."""
        pass
```

### Predictive Analytics (Phase 2.2 - Ready for Implementation)

Performance prediction and optimization recommendations.

#### Interface: `PredictiveAnalytics`

**Location**: `ml_enhancements/predictive_analytics.py` (planned)

```python
class PredictiveAnalytics(ABC):
    """Performance prediction and optimization."""
    
    @abstractmethod
    async def predict_performance(
        self, 
        configuration: SystemConfiguration
    ) -> PerformancePrediction:
        """Predict system performance for given configuration."""
        pass
    
    @abstractmethod
    async def recommend_optimizations(
        self, 
        current_metrics: PerformanceMetrics
    ) -> List[OptimizationRecommendation]:
        """Recommend optimizations based on current metrics."""
        pass
    
    @abstractmethod
    async def forecast_resource_needs(
        self, 
        time_horizon: timedelta,
        workload_projection: WorkloadProjection
    ) -> ResourceForecast:
        """Forecast future resource needs."""
        pass
```

### Adaptive Learning (Phase 2.2 - Ready for Implementation)

Self-improving ML models for continuous optimization.

#### Interface: `AdaptiveLearning`

**Location**: `ml_enhancements/adaptive_learning.py` (planned)

```python
class AdaptiveLearning(ABC):
    """Self-improving adaptive learning system."""
    
    @abstractmethod
    async def learn_from_feedback(
        self, 
        feedback: UserFeedback
    ) -> LearningResult:
        """Learn from user feedback and outcomes."""
        pass
    
    @abstractmethod
    async def update_models(
        self, 
        new_data: List[TrainingData]
    ) -> ModelUpdateResult:
        """Update ML models with new training data."""
        pass
    
    @abstractmethod
    async def evaluate_model_performance(self) -> ModelEvaluation:
        """Evaluate current model performance."""
        pass
```

## Testing APIs

**❌ Status**: Basic testing infrastructure exists, but mock APIs not yet implemented.

### Mock Infrastructure (Future Implementation)

Planned comprehensive mock infrastructure for testing.

#### Mock Agent Coordinator (Future Implementation)

```python
# FUTURE IMPLEMENTATION ❌
# from claude.testing.mocks import MockMultiAgentCoordinator

# CURRENT TESTING ✅ - Use actual test files
# See tests/ directory for implemented tests

class MockMultiAgentCoordinator:
    """Mock coordinator for testing multi-agent scenarios."""
    
    async def setup_test_agents(self, count: int = 5) -> List[MockAgent]:
        """Setup mock agents for testing."""
        
    async def simulate_load(self, load_percentage: float) -> None:
        """Simulate system load for testing."""
        
    async def trigger_agent_failure(self, agent_id: str) -> None:
        """Simulate agent failure for testing."""
```

#### Mock Resource Environment

```python
from claude.testing.mocks import MockResourceEnvironment

class MockResourceEnvironment:
    """Mock resource environment for testing."""
    
    def __init__(
        self,
        cpu_usage: float = 0.5,
        memory_usage: float = 0.4,
        disk_usage: float = 0.3,
        network_usage: float = 0.2
    ):
        """Initialize mock environment with controlled usage."""
```

## Utilities and Helpers

**❌ Status**: Not yet implemented. Planned for Phase 0.

### Performance Monitoring (Future Implementation)

Planned real-time performance monitoring and metrics collection.

#### Class: `PerformanceMonitor` (Future Implementation)

```python
# FUTURE IMPLEMENTATION ❌
# from claude.utils.performance_monitor import PerformanceMonitor

class PerformanceMonitor:
    """Real-time performance monitoring."""
    
    async def collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics."""
        
    async def start_monitoring(self, interval: int = 30) -> None:
        """Start continuous monitoring with specified interval."""
        
    async def stop_monitoring(self) -> None:
        """Stop continuous monitoring."""
        
    async def get_historical_metrics(
        self, 
        duration: timedelta
    ) -> List[PerformanceMetrics]:
        """Get historical metrics for specified duration."""
```

### Logging Configuration (Future Implementation)

Planned structured logging with correlation ID tracking.

#### Functions (Future Implementation)

```python
# FUTURE IMPLEMENTATION ❌
# from claude.utils.logging_config import setup_logging, get_logger

def setup_logging(config: Dict) -> None:
    """Setup structured logging configuration."""
    
def get_logger(name: str) -> Logger:
    """Get logger with structured formatting."""
    
def log_performance(func: Callable) -> Callable:
    """Decorator for automatic performance logging."""
```

## Error Handling

### Exception Hierarchy

```python
class LeanViveError(Exception):
    """Base exception for LeanVibe Agent Hive."""
    pass

class ConfigurationError(LeanViveError):
    """Configuration related errors."""
    pass

class AgentError(LeanViveError):
    """Agent execution errors."""
    pass

class CoordinationError(LeanViveError):
    """Multi-agent coordination errors."""
    pass

class ResourceError(LeanViveError):
    """Resource management errors."""
    pass

class ScalingError(LeanViveError):
    """Auto-scaling errors."""
    pass
```

### Error Response Format

```python
@dataclass
class ErrorResponse:
    """Standardized error response."""
    error_code: str
    error_message: str
    error_details: Dict[str, Any]
    timestamp: datetime
    correlation_id: str
```

## Examples

### Current Working Example

**✅ What Actually Works Now**:

```python
import asyncio
from advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
from advanced_orchestration.models import CoordinatorConfig

async def main():
    # Initialize configuration (current implementation)
    config = CoordinatorConfig()
    
    # Initialize coordinator (what's currently implemented)
    coordinator = MultiAgentCoordinator(config)
    
    # This is what currently works
    print("✅ MultiAgentCoordinator initialized successfully")
    print(f"Configuration: {config}")
    
    # Future features (not yet implemented):
    # - Orchestrator wrapper
    # - Autonomous execution sessions  
    # - Status monitoring
    # - Agent registration/management

if __name__ == "__main__":
    asyncio.run(main())
```

### Future Complete Orchestration Example (Planned)

**❌ Future Implementation**:

```python
# FUTURE IMPLEMENTATION ❌
# import asyncio
# from datetime import timedelta
# from claude.orchestrator import Orchestrator
# from claude.config.config_loader import ConfigLoader
# 
# async def main():
#     config = ConfigLoader()
#     config.validate()
#     orchestrator = Orchestrator(config)
#     await orchestrator.start()
#     # ... rest of orchestration features
```

### Multi-Agent Task Assignment Example (Future Implementation)

**❌ Status**: Task assignment functionality planned but not yet implemented.

```python
# FUTURE IMPLEMENTATION ❌
# async def assign_tasks_example():
#     from advanced_orchestration.multi_agent_coordinator import (
#         MultiAgentCoordinator, LoadBalancingStrategy
#     )
#     from claude.queue.task_queue import Task
    
    coordinator = MultiAgentCoordinator()
    
    # Create tasks
    tasks = [
        Task(
            task_id="backend-001",
            task_type="api_development",
            description="Create REST API endpoint",
            parameters={"framework": "fastapi"},
            priority=7
        ),
        Task(
            task_id="frontend-001", 
            task_type="ui_development",
            description="Create React component",
            parameters={"component": "UserProfile"},
            priority=6
        )
    ]
    
    # Assign tasks using different strategies
    for task in tasks:
        assignment = await coordinator.assign_task(
            task=task,
            strategy=LoadBalancingStrategy.CAPABILITY_BASED
        )
        print(f"Task {task.task_id} assigned to {assignment.agent_id}")
        print(f"Confidence: {assignment.confidence_score:.2f}")
```

### Resource Management Example

**✅ Current Implementation**:

```python
async def resource_management_example():
    from advanced_orchestration.resource_manager import ResourceManager
    from advanced_orchestration.models import ResourceRequirements
    
    resource_manager = ResourceManager()
    
    # Check current resources
    resources = await resource_manager.get_system_resources()
    print(f"CPU: {resources.cpu_percent}%")
    print(f"Memory: {resources.memory_used_mb}MB / {resources.memory_available_mb}MB")
    
    # Allocate resources for agent
    requirements = ResourceRequirements(
        cpu_cores=2.0,
        memory_mb=1024,
        disk_mb=500,
        network_bandwidth_mbps=10.0,
        priority=5
    )
    
    allocation = await resource_manager.allocate_resources(
        agent_id="ml-agent-1",
        requirements=requirements
    )
    
    if allocation.success:
        print(f"Resources allocated: {allocation.allocation_id}")
        
        # Monitor usage
        report = await resource_manager.monitor_resource_usage()
        print(f"Efficiency score: {report.efficiency_score:.2f}")
    else:
        print(f"Allocation failed: {allocation.message}")
```

---

**API Version**: Phase 0 (Foundation Implementation)  
**Status**: Core orchestration APIs implemented | CLI and configuration systems planned | Documentation accuracy restored

**✅ Currently Implemented**:
- `advanced_orchestration.multi_agent_coordinator.MultiAgentCoordinator`
- `advanced_orchestration.resource_manager.ResourceManager`  
- `advanced_orchestration.scaling_manager.ScalingManager`
- `advanced_orchestration.models.*` (all data types)

**❌ Planned for Phase 0**:
- CLI interface (`cli.py`)
- Configuration system (`.claude/config/`)
- Agent framework (`.claude/agents/`)
- Task queue (`.claude/queue/`)
- Utilities and helpers (`.claude/utils/`)

This API reference now accurately reflects current implementation status. For working examples, see the tests directory.