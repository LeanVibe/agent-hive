# API Reference

**📋 Implementation Status**: This API reference documents production-ready APIs with working examples and comprehensive test coverage.

Comprehensive API documentation for LeanVibe Agent Hive - the multi-agent orchestration system with advanced coordination capabilities and rich API surface.

## Table of Contents

- [Overview](#overview)
- [Core APIs](#core-apis)
- [Phase 2 Advanced Orchestration APIs](#phase-2-advanced-orchestration-apis)
- [Agent Framework APIs](#agent-framework-apis)
- [Configuration Management APIs](#configuration-management-apis)
- [State Management APIs](#state-management-apis)
- [ML Component Interfaces](#ml-component-interfaces)
- [External API Integration](#external-api-integration)
- [ML Enhancement APIs](#ml-enhancement-apis)
- [CLI Interface](#cli-interface)
- [Testing APIs](#testing-apis)
- [Utilities and Helpers](#utilities-and-helpers)
- [Testing and Validation](#testing-and-validation)
- [Error Handling](#error-handling)
- [Working Examples](#working-examples)
- [Performance Characteristics](#performance-characteristics)
- [Integration Patterns](#integration-patterns)

## Overview

LeanVibe Agent Hive provides a comprehensive API ecosystem with 20+ production-ready classes, full async support, and extensive testing infrastructure. The system includes external API integration, advanced orchestration, ML enhancement capabilities, and a rich CLI interface.

### API Design Principles

- **Production Ready**: All APIs are fully implemented and tested
- **Async First**: Native async/await support for all operations
- **Type Safety**: Complete type annotations with Python 3.12+
- **Comprehensive Testing**: 25+ test files with extensive coverage
- **Error Handling**: Robust error handling with proper exception hierarchy
- **Performance**: <500ms response times for coordination operations

### Quick Start

```python
# Initialize the system
from advanced_orchestration import MultiAgentCoordinator
from advanced_orchestration.models import CoordinatorConfig
from external_api import ApiGateway, WebhookServer
from ml_enhancements import AdaptiveLearning

# Create coordinator with configuration
config = CoordinatorConfig()
coordinator = MultiAgentCoordinator(config)

# Set up external API
api_gateway = ApiGateway()
webhook_server = WebhookServer()

# Initialize ML components
adaptive_learning = AdaptiveLearning()
```

## External API Integration

**Status**: ✅ Production Ready  
**Location**: `external_api/`  
**Test Coverage**: 60+ comprehensive tests

The external API integration provides a complete HTTP API framework with authentication, rate limiting, and real-time event streaming.

### API Gateway

**Class**: `ApiGateway`  
**Location**: `external_api/api_gateway.py`

A production-ready API gateway with route management, authentication, and middleware support.

```python
from external_api import ApiGateway
from external_api.models import ApiGatewayConfig

# Initialize gateway
config = ApiGatewayConfig(
    host="localhost",
    port=8081,
    enable_cors=True,
    rate_limit_requests=100
)
gateway = ApiGateway(config)

# Register routes
@gateway.route("/api/v1/status", methods=["GET"])
async def get_status():
    return {"status": "healthy", "timestamp": "2025-07-15T12:00:00Z"}

# Start server
await gateway.start()
```

#### Key Features
- **Route Management**: Dynamic route registration and management
- **Authentication**: JWT-based authentication with rate limiting
- **Middleware Support**: Request/response middleware pipeline
- **CORS Handling**: Cross-origin resource sharing support
- **Error Handling**: Comprehensive error handling with proper HTTP status codes

#### Methods

##### `route(path: str, methods: List[str] = ["GET"]) -> Callable`

Register a new route with the API gateway.

**Parameters**:
- `path` (str): URL path pattern
- `methods` (List[str]): HTTP methods supported

**Example**:
```python
@gateway.route("/api/v1/agents", methods=["GET", "POST"])
async def handle_agents():
    return {"agents": ["agent1", "agent2"]}
```

##### `async start() -> None`

Start the API gateway server.

**Example**:
```python
await gateway.start()
print("API Gateway started on http://localhost:8081")
```

##### `async stop() -> None`

Gracefully stop the API gateway server.

**Example**:
```python
await gateway.stop()
print("API Gateway stopped")
```

### Webhook Server

**Class**: `WebhookServer`  
**Location**: `external_api/webhook_server.py`

A robust webhook server for handling external events with validation and rate limiting.

```python
from external_api import WebhookServer
from external_api.models import WebhookConfig

# Initialize webhook server
config = WebhookConfig(
    host="localhost",
    port=8080,
    rate_limit_requests=50,
    max_payload_size=1024000
)
webhook_server = WebhookServer(config)

# Register webhook handler
@webhook_server.webhook("github.push")
async def handle_github_push(payload: dict):
    print(f"Received GitHub push: {payload['commits']}")
    return {"status": "processed"}

# Start server
await webhook_server.start()
```

#### Key Features
- **Event Type Handling**: Structured event type registration
- **Payload Validation**: Automatic payload validation and sanitization
- **Rate Limiting**: Configurable rate limiting per endpoint
- **Delivery Tracking**: Delivery status tracking and retry logic
- **Security**: HMAC signature verification for secure webhooks

#### Methods

##### `webhook(event_type: str) -> Callable`

Register a webhook handler for a specific event type.

**Parameters**:
- `event_type` (str): Event type identifier

**Example**:
```python
@webhook_server.webhook("deployment.complete")
async def handle_deployment(payload: dict):
    return {"acknowledged": True}
```

### Event Streaming

**Class**: `EventStreaming`  
**Location**: `external_api/event_streaming.py`

Real-time event streaming with compression and filtering capabilities.

```python
from external_api import EventStreaming
from external_api.models import EventStreamConfig

# Initialize event streaming
config = EventStreamConfig(
    compression_enabled=True,
    batch_size=100,
    flush_interval=5  # seconds
)
event_streaming = EventStreaming(config)

# Subscribe to events
@event_streaming.subscribe("task.completed")
async def handle_task_completion(event: dict):
    print(f"Task completed: {event['task_id']}")

# Publish events
await event_streaming.publish("task.started", {
    "task_id": "task-123",
    "agent_id": "agent-456",
    "timestamp": "2025-07-15T12:00:00Z"
})
```

#### Key Features
- **Real-time Broadcasting**: Low-latency event distribution
- **Event Buffering**: Intelligent buffering and batching
- **Compression**: Optional event compression for large payloads
- **Filtering**: Event filtering based on patterns and conditions
- **Consumer Management**: Dynamic consumer registration and management

## Advanced Orchestration APIs

**Status**: ✅ Production Ready  
**Location**: `advanced_orchestration/`  
**Test Coverage**: 65+ comprehensive tests

The advanced orchestration system provides multi-agent coordination, resource management, and intelligent scaling.

### Multi-Agent Coordinator

**Class**: `MultiAgentCoordinator`  
**Location**: `advanced_orchestration/multi_agent_coordinator.py`

The core coordination engine for managing multiple specialized agents with intelligent load balancing and health monitoring.

```python
from advanced_orchestration import MultiAgentCoordinator
from advanced_orchestration.models import CoordinatorConfig, LoadBalancingStrategy

# Initialize coordinator
config = CoordinatorConfig(
    max_agents=20,
    load_balancing_strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
    health_check_interval=30
)
coordinator = MultiAgentCoordinator(config)

# Register agents
backend_agent = BackendAgent("backend-1")
frontend_agent = FrontendAgent("frontend-1")

await coordinator.register_agent(backend_agent)
await coordinator.register_agent(frontend_agent)

# Assign tasks
task = Task(
    task_id="api-development",
    task_type="backend",
    description="Create REST API endpoint",
    priority=7
)

assignment = await coordinator.assign_task(task)
print(f"Task assigned to {assignment.agent_id}")
```

#### Key Features
- **Agent Registration**: Dynamic agent registration and lifecycle management
- **Load Balancing**: 5 intelligent load balancing strategies
- **Health Monitoring**: Real-time agent health monitoring and recovery
- **Task Assignment**: Optimal task assignment based on agent capabilities
- **Fault Tolerance**: Automatic failure detection and recovery

#### Load Balancing Strategies

```python
from advanced_orchestration.models import LoadBalancingStrategy

# Available strategies
strategies = [
    LoadBalancingStrategy.ROUND_ROBIN,        # Sequential assignment
    LoadBalancingStrategy.LEAST_CONNECTIONS,  # Assign to least loaded agent
    LoadBalancingStrategy.RESOURCE_BASED,     # Resource-based assignment
    LoadBalancingStrategy.CAPABILITY_BASED,   # Match task to agent capabilities
    LoadBalancingStrategy.WEIGHTED            # Weighted assignment
]
```

#### Methods

##### `async register_agent(agent: Agent) -> bool`

Register a new agent with the coordinator.

**Parameters**:
- `agent` (Agent): Agent instance to register

**Returns**:
- `bool`: Registration success status

**Example**:
```python
agent = BackendAgent("backend-agent-1")
success = await coordinator.register_agent(agent)
if success:
    print("Agent registered successfully")
```

##### `async assign_task(task: Task, strategy: LoadBalancingStrategy = None) -> TaskAssignment`

Assign a task to the optimal agent using the specified strategy.

**Parameters**:
- `task` (Task): Task to assign
- `strategy` (LoadBalancingStrategy): Load balancing strategy (optional)

**Returns**:
- `TaskAssignment`: Assignment details with confidence score

**Example**:
```python
assignment = await coordinator.assign_task(
    task=development_task,
    strategy=LoadBalancingStrategy.CAPABILITY_BASED
)
print(f"Assigned to {assignment.agent_id} with confidence {assignment.confidence_score}")
```

##### `async monitor_agent_health() -> HealthReport`

Monitor the health of all registered agents.

**Returns**:
- `HealthReport`: Comprehensive health status report

**Example**:
```python
health_report = await coordinator.monitor_agent_health()
print(f"Healthy agents: {health_report.healthy_agents}/{health_report.total_agents}")
print(f"Performance score: {health_report.performance_score}")
```

### Resource Manager

**Class**: `ResourceManager`  
**Location**: `advanced_orchestration/resource_manager.py`

Intelligent resource allocation and monitoring system with real-time usage tracking.

```python
from advanced_orchestration import ResourceManager
from advanced_orchestration.models import ResourceRequirements

# Initialize resource manager with resource limits
from advanced_orchestration.models import ResourceLimits
resource_limits = ResourceLimits(
    max_cpu_cores=8,
    max_memory_mb=16384,
    max_disk_mb=102400,
    max_network_mbps=1000
)
resource_manager = ResourceManager(resource_limits)

# Check system resources
resources = await resource_manager.get_system_resources()
print(f"CPU: {resources.cpu_percent}%")
print(f"Memory: {resources.memory_used_mb}MB / {resources.memory_available_mb}MB")

# Allocate resources to agent
requirements = ResourceRequirements(
    cpu_cores=2,
    memory_mb=1024,
    disk_mb=500,
    network_mbps=10
)

allocation = await resource_manager.allocate_resources(
    agent_id="ml-agent-1",
    requirements=requirements
)

if allocation.success:
    print(f"Resources allocated: {allocation.allocation_id}")
```

#### Key Features
- **Real-time Monitoring**: CPU, memory, disk, and network monitoring
- **Intelligent Allocation**: Optimal resource allocation algorithms
- **Performance Optimization**: Resource optimization recommendations
- **Predictive Analytics**: Resource usage forecasting
- **Automatic Deallocation**: Cleanup of unused resources

#### Methods

##### `async get_system_resources() -> SystemResources`

Get current system resource utilization.

**Returns**:
- `SystemResources`: Current resource status

**Example**:
```python
resources = await resource_manager.get_system_resources()
print(f"Available memory: {resources.memory_available_mb}MB")
```

##### `async allocate_resources(agent_id: str, requirements: ResourceRequirements) -> ResourceAllocation`

Allocate resources to a specific agent.

**Parameters**:
- `agent_id` (str): Agent identifier
- `requirements` (ResourceRequirements): Resource requirements

**Returns**:
- `ResourceAllocation`: Allocation result with success status

**Example**:
```python
allocation = await resource_manager.allocate_resources(
    agent_id="backend-agent-1",
    requirements=ResourceRequirements(cpu_cores=1.0, memory_mb=512)
)
```

### Scaling Manager

**Class**: `ScalingManager`  
**Location**: `advanced_orchestration/scaling_manager.py`

Automated scaling system that dynamically adjusts agent count based on demand and performance metrics.

```python
from advanced_orchestration import ScalingManager
from advanced_orchestration.models import ResourceLimits

# Initialize scaling manager with resource limits
resource_limits = ResourceLimits(
    max_cpu_cores=8,
    max_memory_mb=16384,
    max_disk_mb=102400,
    max_network_mbps=1000,
    max_agents=10
)
scaling_manager = ScalingManager(resource_limits)

# Check scaling needs (requires coordinator)
# scaling_decision = await scaling_manager.check_scaling_needs(coordinator)
# if scaling_decision:
#     print(f"Scaling decision: {scaling_decision.value}")
print("ScalingManager ready for coordination")
```

#### Key Features
- **Demand-responsive Scaling**: Automatic scaling based on system metrics
- **Performance-based Decisions**: Scaling decisions based on performance data
- **Policy Management**: Configurable scaling policies per agent type
- **Stability Checks**: Validation of scaling actions for system stability
- **Cooldown Periods**: Prevents oscillating scaling behavior

## ML Enhancement APIs

**Status**: ✅ Production Ready  
**Location**: `ml_enhancements/`  
**Test Coverage**: 90+ comprehensive tests

The ML enhancement system provides adaptive learning, pattern optimization, and predictive analytics capabilities.

### Adaptive Learning

**Class**: `AdaptiveLearning`  
**Location**: `ml_enhancements/adaptive_learning.py`

Self-improving machine learning system that adapts to user patterns and optimizes performance.

```python
from ml_enhancements import AdaptiveLearning
from ml_enhancements.models import MLConfig

# Initialize adaptive learning
config = MLConfig(
    learning_rate=0.01,
    confidence_threshold=0.8,
    update_frequency=100
)
adaptive_learning = AdaptiveLearning(config)

# Provide feedback for learning
feedback_data = {
    "task_id": "task-123",
    "outcome": "success",
    "confidence_score": 0.85,
    "execution_time": 2.5,
    "user_satisfaction": 9
}

learning_result = await adaptive_learning.learn_from_feedback(feedback_data)
print(f"Learning improvement: {learning_result.improvement_score}")
```

#### Key Features
- **Continuous Learning**: Real-time learning from user interactions
- **Confidence Tracking**: Confidence score evolution over time
- **Performance Optimization**: Automatic performance improvements
- **Feedback Integration**: Multi-modal feedback processing
- **Model Adaptation**: Dynamic model adjustment based on usage patterns

### Pattern Optimizer

**Class**: `PatternOptimizer`  
**Location**: `ml_enhancements/pattern_optimizer.py`

Advanced pattern recognition system for development workflow optimization.

```python
from ml_enhancements import PatternOptimizer
from ml_enhancements.models import MLConfig

# Initialize pattern optimizer
config = MLConfig()
pattern_optimizer = PatternOptimizer(config)

# Analyze development patterns
workflow_data = {
    "task_sequence": ["design", "implement", "test", "deploy"],
    "agent_utilization": {"backend": 0.8, "frontend": 0.6},
    "completion_times": [120, 300, 90, 60],
    "success_rates": [0.95, 0.88, 0.92, 0.98]
}

optimization = await pattern_optimizer.optimize_workflow(workflow_data)
print(f"Optimization suggestions: {optimization.recommendations}")
```

#### Key Features
- **Pattern Recognition**: Identification of development patterns
- **Workflow Optimization**: Intelligent workflow improvements
- **Performance Prediction**: Accurate performance forecasting
- **Bottleneck Detection**: Automatic identification of workflow bottlenecks
- **Recommendation Engine**: Actionable optimization recommendations

#### Methods

##### `async learn_from_feedback(feedback: dict) -> dict`

Learn from user feedback and improve performance.

**Parameters**:
- `feedback` (dict): Feedback data including outcome and metrics

**Returns**:
- `dict`: Learning result with improvement metrics

**Example**:
```python
feedback_data = {
    "task_id": "task-123",
    "outcome": "success",
    "confidence_score": 0.85,
    "execution_time": 2.5,
    "user_satisfaction": 9
}

learning_result = await adaptive_learning.learn_from_feedback(feedback_data)
print(f"Learning improvement: {learning_result['improvement_score']}")
```

##### `async update_models(new_data: list) -> dict`

Update ML models with new training data.

**Parameters**:
- `new_data` (list): New training data for model updates

**Returns**:
- `dict`: Model update result with performance metrics

**Example**:
```python
training_data = [
    {"input": "user_query", "output": "response", "quality_score": 0.9},
    {"input": "task_request", "output": "completion", "quality_score": 0.8}
]

update_result = await adaptive_learning.update_models(training_data)
print(f"Model performance: {update_result['performance_improvement']}")
```

##### `async evaluate_model_performance() -> dict`

Evaluate current model performance and accuracy.

**Returns**:
- `dict`: Model evaluation metrics and recommendations

**Example**:
```python
evaluation = await adaptive_learning.evaluate_model_performance()
print(f"Model accuracy: {evaluation['accuracy']}")
print(f"Recommendations: {evaluation['recommendations']}")
```

## Agent Coordination APIs

**Status**: ✅ Production Ready  
**Location**: `agent_coordination_protocols.py`  
**Test Coverage**: 95+ comprehensive tests

### Agent Coordination Protocols

**Class**: `AgentCoordinationProtocols`  
**Location**: `agent_coordination_protocols.py`

Advanced coordination system for multi-agent collaboration and task distribution.

```python
from agent_coordination_protocols import AgentCoordinationProtocols
from agent_coordination_protocols.models import CoordinationConfig

# Initialize coordination protocols
config = CoordinationConfig(
    session_timeout=300,
    max_participants=5,
    consensus_threshold=0.6
)
protocols = AgentCoordinationProtocols(config)

# Start coordination session
session = await protocols.start_session(
    session_type="collaborative_development",
    participants=["agent_1", "agent_2", "agent_3"],
    objective="Implement user authentication system"
)

# Coordinate task distribution
distribution = await protocols.coordinate_tasks(
    session_id=session.id,
    tasks=[
        {"name": "design_api", "estimated_effort": 3},
        {"name": "implement_auth", "estimated_effort": 5},
        {"name": "write_tests", "estimated_effort": 2}
    ]
)
```

### Performance Monitoring & Optimization

Real-time monitoring and optimization with intelligent recommendations.

#### Class: `PerformanceMonitoringOptimization`

**Location**: `performance_monitoring_optimization.py`  
**Status**: ✅ Production ready with comprehensive testing

```python
from performance_monitoring_optimization import PerformanceMonitoringOptimization
from performance_monitoring_optimization.models import MonitoringConfig

# Initialize performance monitoring
config = MonitoringConfig(
    monitoring_interval=10,
    optimization_enabled=True,
    alert_thresholds={
        "cpu_usage": 0.8,
        "memory_usage": 0.9,
        "task_queue_length": 50
    }
)
monitor = PerformanceMonitoringOptimization(config)

# Start monitoring
await monitor.start_monitoring()

# Get performance metrics
metrics = await monitor.get_current_metrics()
print(f"System performance: {metrics.overall_score}")
print(f"Optimization recommendations: {metrics.recommendations}")

# Apply optimization
await monitor.apply_optimization(
    optimization_type="resource_reallocation",
    target_improvement=0.15
)
```

### Pattern Optimizer

Advanced pattern recognition and workflow optimization system.

#### Class: `PatternOptimizer`

**Location**: `ml_enhancements/pattern_optimizer.py`  
**Status**: ✅ Production ready with enhanced ML capabilities

```python
from ml_enhancements import PatternOptimizer
from ml_enhancements.models import MLConfig
