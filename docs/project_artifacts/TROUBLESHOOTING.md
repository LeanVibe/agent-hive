# Troubleshooting Guide

**📋 Implementation Status**: This guide covers troubleshooting for both implemented and planned features.

**✅ Currently Troubleshootable**:
- Python API imports and advanced_orchestration module
- Intelligence Framework with ML-based decision making
- External API Integration (WebhookServer, ApiGateway, EventStreaming)
- Enhanced ML Systems (PatternOptimizer, PredictiveAnalytics, AdaptiveLearning)
- Task allocation and agent coordination protocols
- Performance monitoring and optimization
- Testing infrastructure and test execution (26 tests with 96% coverage)
- UV/Python environment and dependency issues

**❌ Not Yet Available**:
- CLI commands and orchestrator troubleshooting
- Configuration system issues
- Agent framework and ML component problems

Comprehensive troubleshooting guide for LeanVibe Agent Hive - covering installation issues, current API problems, and development environment debugging.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Installation Issues](#installation-issues)
- [Configuration Problems](#configuration-problems)
- [Phase 2 Multi-Agent Issues](#phase-2-multi-agent-issues)
- [Intelligence Framework Issues](#intelligence-framework-issues)
- [External API Integration Issues](#external-api-integration-issues)
- [Enhanced ML Systems Issues](#enhanced-ml-systems-issues)
- [Performance Problems](#performance-problems)
- [Testing Issues](#testing-issues)
- [Development Environment](#development-environment)
- [Common Error Messages](#common-error-messages)
- [Advanced Debugging](#advanced-debugging)
- [Getting Help](#getting-help)

## Quick Diagnostics

### System Health Check

Run these commands to quickly diagnose system health:

```bash
# Check UV installation and version
uv --version

# Verify Python version
uv run python --version

# Quick environment validation
uv run python -c "
import sys
print(f'Python: {sys.version}')
print(f'Path: {sys.path[:3]}')
"

# Validate current implementation
uv run python -c "
from advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
from advanced_orchestration.models import CoordinatorConfig
config = CoordinatorConfig()
coordinator = MultiAgentCoordinator(config)
print('✅ Python API working successfully')
print('✅ Core orchestration components available')
"

# NOTE: Configuration system not yet implemented
# Future: from claude.config.config_loader import ConfigLoader

# Run health check test
uv run pytest tests/integration/test_orchestrator_workflow.py::test_health_check -v
```

### Environment Information

```bash
# System information
echo "System: $(uname -a)"
echo "Python: $(python --version)"
echo "UV: $(uv --version)"
echo "Git: $(git --version)"

# Project information
echo "Working directory: $(pwd)"
echo "Git branch: $(git branch --show-current)"
echo "Git status: $(git status --porcelain | wc -l) changes"

# Dependencies
uv run pip list | grep -E "(pytest|asyncio|yaml)"
```

## Installation Issues

### UV Installation Problems

#### Issue: UV command not found
```bash
# Error message
-bash: uv: command not found
```

**Solution**:
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reload shell configuration
source ~/.bashrc
# OR restart terminal

# Verify installation
uv --version
```

#### Issue: UV installation fails on macOS
```bash
# Error message
curl: (35) error:1407742E:SSL routines:SSL23_GET_SERVER_HELLO:tlsv1 alert protocol version
```

**Solutions**:
```bash
# Update curl and certificates
brew update && brew upgrade curl

# Alternative installation method
pip install uv

# Or use Homebrew
brew install uv
```

### Python Version Issues

#### Issue: Python 3.12+ required
```bash
# Error message
Python 3.11 or earlier detected. LeanVibe Agent Hive requires Python 3.12+
```

**Solutions**:
```bash
# Install Python 3.12 with UV
uv python install 3.12

# Or use Homebrew on macOS
brew install python@3.12

# Update PATH to use Python 3.12
export PATH="/opt/homebrew/bin:$PATH"

# Verify version
python --version
```

### Dependency Installation Issues

#### Issue: UV sync fails with dependency conflicts
```bash
# Error message
error: Failed to solve the requirements from `pyproject.toml`.
```

**Solutions**:
```bash
# Clear UV cache
uv cache clean

# Force reinstall dependencies
uv sync --reinstall

# Update lock file
uv lock --upgrade

# Check for conflicting system packages
uv run pip check
```

#### Issue: Missing system dependencies on Linux
```bash
# Error message
error: Microsoft Visual C++ 14.0 is required
# OR
error: Failed building wheel for some-package
```

**Solutions**:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install build-essential python3-dev

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel

# Alpine
apk add build-base python3-dev
```

## Configuration Problems

### Configuration Loading Errors

#### Issue: Configuration file not found
```bash
# Error message
FileNotFoundError: [Errno 2] No such file or directory: '.claude/config/config.yaml'
```

**Solution**:
```bash
# Check if file exists
ls -la .claude/config/

# If missing, copy from template
cp .claude/config/config.yaml.example .claude/config/config.yaml

# Or create minimal configuration
cat > .claude/config/config.yaml << 'EOF'
system:
  log_level: INFO
  debug_mode: true

agents:
  claude:
    cli_path: "claude"
    timeout: 300
    capabilities: ["code_generation", "debugging"]

development:
  use_mock_cli: true
EOF
```

#### Issue: Invalid YAML syntax
```bash
# Error message
yaml.scanner.ScannerError: while scanning for the next token
```

**Diagnostics**:
```bash
# Validate YAML syntax
uv run python -c "
import yaml
with open('.claude/config/config.yaml', 'r') as f:
    try:
        yaml.safe_load(f)
        print('✅ YAML syntax is valid')
    except yaml.YAMLError as e:
        print(f'❌ YAML syntax error: {e}')
"

# Check for common issues
grep -n ":" .claude/config/config.yaml | head -10
```

**Common YAML Issues**:
```yaml
# ❌ Incorrect indentation
system:
log_level: INFO  # Should be indented

# ✅ Correct indentation
system:
  log_level: INFO

# ❌ Missing quotes for special characters
description: "Agent: Advanced AI"  # Colon needs quotes

# ✅ Proper quoting
description: "Agent: Advanced AI"
```

### Environment Variable Issues

#### Issue: Environment overrides not working
```bash
# Variables set but not taking effect
export LEANVIBE_SYSTEM_LOG_LEVEL=DEBUG
```

**Diagnostics**:
```bash
# Check environment variables
env | grep LEANVIBE_

# Verify configuration loading
uv run python -c "
from claude.config.config_loader import ConfigLoader
config = ConfigLoader()
print(f'Log level: {config.get(\"system.log_level\")}')
print(f'Debug mode: {config.get(\"system.debug_mode\")}')
"
```

**Solution**:
```bash
# Ensure correct variable format
export LEANVIBE_SYSTEM_LOG_LEVEL=DEBUG
export LEANVIBE_SYSTEM_DEBUG_MODE=true

# Check if variables are being read
uv run python -c "
import os
print('Environment variables:')
for key, value in os.environ.items():
    if key.startswith('LEANVIBE_'):
        print(f'  {key}={value}')
"
```

## Phase 2 Multi-Agent Issues

### Multi-Agent Coordinator Problems

#### Issue: Agents not registering properly
```bash
# Error message
CoordinationError: Failed to register agent 'backend-agent-1'
```

**Diagnostics**:
```bash
# Check coordinator status
uv run python -c "
from claude.advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
coordinator = MultiAgentCoordinator()
status = coordinator.get_status()
print(f'Registered agents: {status.total_agents}')
print(f'Health status: {status.health_score}')
"

# Test agent registration
uv run pytest tests/test_multi_agent_coordinator.py::test_agent_registration -v
```

**Solutions**:
```bash
# Reset coordinator state
uv run python -c "
from claude.advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
coordinator = MultiAgentCoordinator()
coordinator.reset_all_agents()
print('✅ Coordinator state reset')
"

# Check agent configuration
uv run python -c "
from claude.config.config_loader import ConfigLoader
config = ConfigLoader()
agents_config = config.get('agents', {})
for agent_type, agent_config in agents_config.items():
    print(f'{agent_type}: {agent_config.get(\"capabilities\", [])}')
"
```

#### Issue: Load balancing not working correctly
```bash
# Error message
LoadBalancingError: No suitable agent found for task
```

**Diagnostics**:
```bash
# Check load balancing status
uv run pytest tests/test_multi_agent_coordinator.py::test_load_balancing -v

# Examine agent loads
uv run python -c "
from claude.advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
coordinator = MultiAgentCoordinator()
for agent_id in coordinator.get_registered_agents():
    status = coordinator.get_agent_status(agent_id)
    print(f'{agent_id}: {status.load_percentage:.1f}% load')
"
```

### Resource Management Issues

#### Issue: Resource allocation failures
```bash
# Error message
ResourceError: Insufficient resources for allocation
```

**Diagnostics**:
```bash
# Check current resource usage
uv run python -c "
from claude.advanced_orchestration.resource_manager import ResourceManager
rm = ResourceManager()
resources = rm.get_system_resources()
print(f'CPU: {resources.cpu_percent:.1f}%')
print(f'Memory: {resources.memory_used_mb}MB / {resources.memory_available_mb}MB')
print(f'Disk: {resources.disk_used_gb}GB / {resources.disk_free_gb}GB')
"

# Test resource allocation
uv run pytest tests/test_resource_manager.py::test_allocation_efficiency -v
```

**Solutions**:
```bash
# Free up resources
uv run python -c "
from claude.advanced_orchestration.resource_manager import ResourceManager
rm = ResourceManager()
# Deallocate unused resources
for agent_id in rm.get_allocated_agents():
    if not rm.is_agent_active(agent_id):
        rm.deallocate_resources(agent_id)
        print(f'✅ Freed resources for {agent_id}')
"

# Adjust resource limits
export LEANVIBE_RESOURCES_CPU_LIMIT_PERCENT=90
export LEANVIBE_RESOURCES_MEMORY_LIMIT_PERCENT=85
```

### Auto-Scaling Issues

#### Issue: Scaling not responding to load changes
```bash
# Error message
ScalingError: Scaling operation failed or timed out
```

**Diagnostics**:
```bash
# Check scaling configuration
uv run python -c "
from claude.config.config_loader import ConfigLoader
config = ConfigLoader()
scaling_config = config.get('scaling', {})
print(f'Auto-scale enabled: {scaling_config.get(\"auto_scale\", False)}')
print(f'Scale up threshold: {scaling_config.get(\"scale_up_threshold\", 0.8)}')
print(f'Scale down threshold: {scaling_config.get(\"scale_down_threshold\", 0.3)}')
"

# Test scaling logic
uv run pytest tests/test_scaling_manager.py::test_scaling_triggers -v
```

**Solutions**:
```bash
# Enable auto-scaling
export LEANVIBE_SCALING_AUTO_SCALE=true

# Adjust thresholds
export LEANVIBE_SCALING_SCALE_UP_THRESHOLD=0.75
export LEANVIBE_SCALING_SCALE_DOWN_THRESHOLD=0.25

# Manual scaling test
uv run python -c "
from claude.advanced_orchestration.scaling_manager import ScalingManager
sm = ScalingManager()
result = sm.scale_up('backend', count=1)
print(f'Scaling result: {result.success}')
"
```

## Intelligence Framework Issues

### ML-based Decision Making Problems

#### Issue: Confidence scoring inconsistencies
```bash
# Error message
IntelligenceError: Confidence score calculation failed or returned invalid value
```

**Diagnostics**:
```bash
# Check intelligence framework status
uv run python -c "
from intelligence_framework import IntelligenceFramework
from intelligence_framework.models import IntelligenceConfig
config = IntelligenceConfig()
framework = IntelligenceFramework(config)
health = framework.health_check()
print(f'Framework health: {health.status}')
print(f'Confidence system: {health.confidence_system_active}')
"

# Test confidence scoring
uv run pytest tests/test_intelligence_framework.py::test_confidence_scoring -v
```

**Solutions**:
```bash
# Reset confidence system
uv run python -c "
from intelligence_framework import IntelligenceFramework
framework = IntelligenceFramework()
framework.reset_confidence_system()
print('✅ Confidence system reset')
"

# Recalibrate confidence scoring
export LEANVIBE_INTELLIGENCE_CONFIDENCE_THRESHOLD=0.75
export LEANVIBE_INTELLIGENCE_LEARNING_RATE=0.01
```

#### Issue: Intelligent task allocation failures
```bash
# Error message
TaskAllocationError: No suitable agent found for task based on intelligence analysis
```

**Diagnostics**:
```bash
# Check task allocation system
uv run python -c "
from intelligent_task_allocation import IntelligentTaskAllocator
from intelligent_task_allocation.models import TaskAllocationConfig
config = TaskAllocationConfig()
allocator = IntelligentTaskAllocator(config)
status = allocator.get_system_status()
print(f'Available agents: {status.available_agents}')
print(f'Performance scores: {status.agent_performance_scores}')
"

# Test task allocation
uv run pytest tests/test_intelligent_task_allocation.py::test_allocation_logic -v
```

**Solutions**:
```bash
# Refresh agent performance profiles
uv run python -c "
from intelligent_task_allocation import IntelligentTaskAllocator
allocator = IntelligentTaskAllocator()
allocator.refresh_agent_profiles()
print('✅ Agent profiles refreshed')
"

# Adjust allocation parameters
export LEANVIBE_TASK_ALLOCATION_MIN_CONFIDENCE=0.6
export LEANVIBE_TASK_ALLOCATION_LEARNING_ENABLED=true
```

### Agent Coordination Protocol Issues

#### Issue: Coordination session failures
```bash
# Error message
CoordinationProtocolError: Failed to establish coordination session between agents
```

**Diagnostics**:
```bash
# Check coordination protocols
uv run python -c "
from agent_coordination_protocols import AgentCoordinationProtocols
from agent_coordination_protocols.models import CoordinationConfig
config = CoordinationConfig()
protocols = AgentCoordinationProtocols(config)
sessions = protocols.get_active_sessions()
print(f'Active sessions: {len(sessions)}')
for session in sessions:
    print(f'  Session {session.id}: {session.participants} participants')
"

# Test coordination protocols
uv run pytest tests/test_agent_coordination_protocols.py::test_session_management -v
```

**Solutions**:
```bash
# Reset coordination state
uv run python -c "
from agent_coordination_protocols import AgentCoordinationProtocols
protocols = AgentCoordinationProtocols()
protocols.reset_coordination_state()
print('✅ Coordination state reset')
"

# Optimize coordination settings
export LEANVIBE_COORDINATION_SESSION_TIMEOUT=300
export LEANVIBE_COORDINATION_MAX_PARTICIPANTS=5
```

## External API Integration Issues

### WebhookServer Problems

#### Issue: Webhook event processing failures
```bash
# Error message
WebhookError: Failed to process incoming webhook event
```

**Diagnostics**:
```bash
# Check webhook server status
uv run python -c "
from external_api import WebhookServer
from external_api.models import WebhookConfig
config = WebhookConfig()
server = WebhookServer(config)
status = server.get_status()
print(f'Server status: {status.is_running}')
print(f'Processed events: {status.processed_events}')
print(f'Failed events: {status.failed_events}')
"

# Test webhook processing
uv run pytest tests/test_webhook_server.py::test_event_processing -v
```

**Solutions**:
```bash
# Restart webhook server
uv run python -c "
from external_api import WebhookServer
server = WebhookServer()
server.stop()
server.start()
print('✅ Webhook server restarted')
"

# Adjust webhook settings
export LEANVIBE_WEBHOOK_RATE_LIMIT=1000
export LEANVIBE_WEBHOOK_TIMEOUT=30
export LEANVIBE_WEBHOOK_MAX_PAYLOAD_SIZE=10485760
```

#### Issue: API Gateway authentication failures
```bash
# Error message
ApiGatewayError: Authentication failed for API request
```

**Diagnostics**:
```bash
# Check API gateway status
uv run python -c "
from external_api import ApiGateway
from external_api.models import ApiGatewayConfig
config = ApiGatewayConfig()
gateway = ApiGateway(config)
status = gateway.get_status()
print(f'Gateway status: {status.is_running}')
print(f'Auth system: {status.auth_system_active}')
print(f'Request count: {status.total_requests}')
"

# Test API gateway authentication
uv run pytest tests/test_api_gateway.py::test_authentication -v
```

**Solutions**:
```bash
# Reset API gateway authentication
uv run python -c "
from external_api import ApiGateway
gateway = ApiGateway()
gateway.reset_auth_system()
print('✅ API gateway auth system reset')
"

# Configure authentication settings
export LEANVIBE_API_GATEWAY_AUTH_TYPE=jwt
export LEANVIBE_API_GATEWAY_JWT_SECRET=your-secret-key
export LEANVIBE_API_GATEWAY_TOKEN_EXPIRY=3600
```

### Event Streaming Issues

#### Issue: Event streaming connection failures
```bash
# Error message
EventStreamError: Failed to establish streaming connection
```

**Diagnostics**:
```bash
# Check event streaming status
uv run python -c "
from external_api import EventStreaming
from external_api.models import EventStreamConfig
config = EventStreamConfig()
streaming = EventStreaming(config)
status = streaming.get_status()
print(f'Streaming status: {status.is_active}')
print(f'Active connections: {status.active_connections}')
print(f'Events processed: {status.events_processed}')
"

# Test event streaming
uv run pytest tests/test_event_streaming.py::test_connection_management -v
```

**Solutions**:
```bash
# Restart event streaming
uv run python -c "
from external_api import EventStreaming
streaming = EventStreaming()
streaming.stop()
streaming.start()
print('✅ Event streaming restarted')
"

# Optimize streaming settings
export LEANVIBE_EVENT_STREAMING_MAX_CONNECTIONS=100
export LEANVIBE_EVENT_STREAMING_BUFFER_SIZE=1024
export LEANVIBE_EVENT_STREAMING_COMPRESSION=true
```

## Enhanced ML Systems Issues

### PatternOptimizer Problems

#### Issue: Pattern recognition failures
```bash
# Error message
PatternOptimizerError: Failed to identify optimization patterns
```

**Diagnostics**:
```bash
# Check pattern optimizer status
uv run python -c "
from ml_enhancements import PatternOptimizer
from ml_enhancements.models import MLConfig
config = MLConfig()
optimizer = PatternOptimizer(config)
status = optimizer.get_status()
print(f'Optimizer status: {status.is_active}')
print(f'Patterns learned: {status.patterns_learned}')
print(f'Optimization score: {status.optimization_score}')
"

# Test pattern recognition
uv run pytest tests/test_pattern_optimizer.py::test_pattern_recognition -v
```

**Solutions**:
```bash
# Reset pattern optimizer
uv run python -c "
from ml_enhancements import PatternOptimizer
optimizer = PatternOptimizer()
optimizer.reset_patterns()
print('✅ Pattern optimizer reset')
"

# Adjust optimization parameters
export LEANVIBE_ML_PATTERN_RECOGNITION_THRESHOLD=0.8
export LEANVIBE_ML_LEARNING_RATE=0.005
```

### PredictiveAnalytics Issues

#### Issue: Performance prediction inaccuracies
```bash
# Error message
PredictiveAnalyticsError: Prediction accuracy below acceptable threshold
```

**Diagnostics**:
```bash
# Check predictive analytics status
uv run python -c "
from ml_enhancements import PredictiveAnalytics
from ml_enhancements.models import MLConfig
config = MLConfig()
analytics = PredictiveAnalytics(config)
status = analytics.get_status()
print(f'Analytics status: {status.is_active}')
print(f'Prediction accuracy: {status.prediction_accuracy}')
print(f'Models trained: {status.models_trained}')
"

# Test predictive analytics
uv run pytest tests/test_predictive_analytics.py::test_prediction_accuracy -v
```

**Solutions**:
```bash
# Retrain predictive models
uv run python -c "
from ml_enhancements import PredictiveAnalytics
analytics = PredictiveAnalytics()
analytics.retrain_models()
print('✅ Predictive models retrained')
"

# Optimize prediction settings
export LEANVIBE_ML_PREDICTION_WINDOW=3600
export LEANVIBE_ML_MODEL_UPDATE_INTERVAL=86400
```

### AdaptiveLearning Problems

#### Issue: Learning system adaptation failures
```bash
# Error message
AdaptiveLearningError: Failed to adapt learning parameters
```

**Diagnostics**:
```bash
# Check adaptive learning status
uv run python -c "
from ml_enhancements import AdaptiveLearning
from ml_enhancements.models import MLConfig
config = MLConfig()
learning = AdaptiveLearning(config)
status = learning.get_status()
print(f'Learning status: {status.is_active}')
print(f'Adaptation rate: {status.adaptation_rate}')
print(f'Learning efficiency: {status.learning_efficiency}')
"

# Test adaptive learning
uv run pytest tests/test_adaptive_learning.py::test_adaptation_logic -v
```

**Solutions**:
```bash
# Reset adaptive learning system
uv run python -c "
from ml_enhancements import AdaptiveLearning
learning = AdaptiveLearning()
learning.reset_learning_state()
print('✅ Adaptive learning system reset')
"

# Adjust learning parameters
export LEANVIBE_ML_ADAPTIVE_LEARNING_RATE=0.01
export LEANVIBE_ML_ADAPTATION_THRESHOLD=0.7
export LEANVIBE_ML_LEARNING_MEMORY_SIZE=10000
```

## Performance Problems

### Coordination Latency Issues

#### Issue: High task assignment latency (>500ms)
```bash
# Error message
PerformanceWarning: Task assignment latency 1250ms exceeds target 500ms
```

**Diagnostics**:
```bash
# Profile coordination performance
uv run pytest tests/performance/test_coordination_latency.py -v --profile

# Check coordination metrics
uv run python -c "
from claude.utils.performance_monitor import PerformanceMonitor
monitor = PerformanceMonitor()
metrics = monitor.collect_metrics()
print(f'Coordination latency: {metrics.coordination_latency_ms}ms')
print(f'Task throughput: {metrics.tasks_per_minute} tasks/min')
"
```

**Solutions**:
```bash
# Optimize coordinator configuration
export LEANVIBE_MULTI_AGENT_HEALTH_CHECK_INTERVAL=60  # Reduce check frequency
export LEANVIBE_MULTI_AGENT_COORDINATION_TIMEOUT=30   # Reduce timeout

# Profile and optimize
uv run python -m cProfile -o coordination_profile.out -c "
from claude.orchestrator import Orchestrator
orchestrator = Orchestrator()
# Run coordination tasks
"

# Analyze profile
uv run python -c "
import pstats
stats = pstats.Stats('coordination_profile.out')
stats.sort_stats('cumulative').print_stats(10)
"
```

### Memory Usage Issues

#### Issue: High memory consumption
```bash
# Error message
MemoryWarning: Agent memory usage 2.5GB exceeds limit 1GB
```

**Diagnostics**:
```bash
# Monitor memory usage
uv run python -c "
import psutil
import os
process = psutil.Process(os.getpid())
memory_info = process.memory_info()
print(f'RSS Memory: {memory_info.rss / 1024 / 1024:.1f} MB')
print(f'VMS Memory: {memory_info.vms / 1024 / 1024:.1f} MB')
"

# Memory profiling
uv run python -m memory_profiler -c "
from claude.orchestrator import Orchestrator
orchestrator = Orchestrator()
# Perform memory-intensive operations
"
```

**Solutions**:
```bash
# Reduce memory limits
export LEANVIBE_RESOURCES_MEMORY_LIMIT_PERCENT=75

# Enable garbage collection optimization
uv run python -c "
import gc
gc.set_threshold(700, 10, 10)  # Aggressive garbage collection
gc.collect()
print('✅ Garbage collection optimized')
"

# Check for memory leaks
uv run pytest tests/performance/test_memory_usage.py -v
```

### Database Performance Issues

#### Issue: Slow state persistence operations
```bash
# Error message
DatabaseWarning: State save operation took 2.5s, target <500ms
```

**Diagnostics**:
```bash
# Check database file size and location
ls -lh *.db .claude/**/*.db 2>/dev/null || echo "No database files found"

# Test database performance
uv run pytest tests/performance/test_database_performance.py -v

# SQLite optimization check
uv run python -c "
import sqlite3
conn = sqlite3.connect('.claude/state.db')
cursor = conn.cursor()
cursor.execute('PRAGMA optimize;')
cursor.execute('PRAGMA integrity_check;')
result = cursor.fetchone()
print(f'Database integrity: {result[0]}')
conn.close()
"
```

**Solutions**:
```bash
# Optimize SQLite settings
uv run python -c "
import sqlite3
conn = sqlite3.connect('.claude/state.db')
cursor = conn.cursor()
cursor.execute('PRAGMA journal_mode=WAL;')
cursor.execute('PRAGMA synchronous=NORMAL;')
cursor.execute('PRAGMA cache_size=10000;')
cursor.execute('PRAGMA temp_store=MEMORY;')
conn.commit()
conn.close()
print('✅ Database optimized')
"

# Clean up old data
uv run python -c "
# Add cleanup logic for old state data
print('✅ Database cleanup completed')
"
```

## Testing Issues

### Test Execution Problems

#### Issue: Async tests failing
```bash
# Error message
RuntimeError: There is no current event loop in thread 'MainThread'
```

**Solution**:
```bash
# Check pytest configuration
cat pytest.ini

# Should contain:
# [tool:pytest]
# asyncio_mode = auto

# If missing, add it:
echo "[tool:pytest]
asyncio_mode = auto
testpaths = tests
addopts = -v --tb=short" > pytest.ini

# Verify pytest-asyncio is installed
uv run pip list | grep pytest-asyncio
```

#### Issue: Mock CLI not working
```bash
# Error message
FileNotFoundError: mock_claude.py not found or not executable
```

**Solution**:
```bash
# Check mock CLI files
ls -la .claude/testing/mock_cli/

# Make mock CLIs executable
chmod +x .claude/testing/mock_cli/mock_*.py

# Test mock CLI directly
python .claude/testing/mock_cli/mock_claude.py --help

# Enable mock mode
export LEANVIBE_DEVELOPMENT_USE_MOCK_CLI=true
```

### Test Coverage Issues

#### Issue: Low test coverage warnings
```bash
# Error message
TOTAL coverage: 78% (target: 95%)
```

**Diagnostics**:
```bash
# Run coverage report
uv run pytest --cov=.claude --cov-report=html --cov-report=term

# Open detailed HTML report
open htmlcov/index.html  # macOS
# OR
xdg-open htmlcov/index.html  # Linux

# Find uncovered lines
uv run pytest --cov=.claude --cov-report=term-missing
```

## Development Environment

### IDE and Editor Issues

#### Issue: Import resolution problems in VS Code
```bash
# Error message
Import "claude.config.config_loader" could not be resolved
```

**Solution**:
```bash
# Create .vscode/settings.json
mkdir -p .vscode
cat > .vscode/settings.json << 'EOF'
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.analysis.extraPaths": [".claude"],
    "python.analysis.autoSearchPaths": true,
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true
}
EOF

# Reload VS Code or restart Python language server
```

### Git and Version Control Issues

#### Issue: Large files in repository
```bash
# Error message
remote: error: File too large (>100MB)
```

**Solution**:
```bash
# Find large files
find . -type f -size +50M -not -path "./.git/*"

# Remove large files from Git history
git filter-branch --force --index-filter \
'git rm --cached --ignore-unmatch large-file.bin' \
--prune-empty --tag-name-filter cat -- --all

# Add to .gitignore
echo "*.bin
*.log
htmlcov/
.coverage
__pycache__/
*.pyc" >> .gitignore
```

## Common Error Messages

### Configuration Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ConfigurationError: Invalid config schema` | YAML syntax error | Validate YAML syntax, check indentation |
| `KeyError: 'agents.claude.cli_path'` | Missing configuration | Add missing configuration keys |
| `FileNotFoundError: config.yaml` | Configuration file missing | Create configuration file from template |

### Runtime Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: No module named 'claude'` | Python path issue | Add `.claude` to Python path |
| `asyncio.TimeoutError` | Operation timeout | Increase timeout values in configuration |
| `ConnectionError: Agent not responding` | Agent communication failure | Check agent health and restart if needed |

### Multi-Agent Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `CoordinationError: No agents available` | All agents busy or failed | Check agent status, restart failed agents |
| `ResourceError: Allocation failed` | Insufficient resources | Free resources or adjust limits |
| `ScalingError: Scale operation timeout` | Scaling system overloaded | Reduce scaling frequency, check system load |

## Advanced Debugging

### Performance Profiling

#### CPU Profiling
```bash
# Profile the orchestrator
uv run python -m cProfile -o orchestrator_profile.out .claude/orchestrator.py

# Analyze profile
uv run python -c "
import pstats
stats = pstats.Stats('orchestrator_profile.out')
stats.sort_stats('cumulative').print_stats(20)
"

# Visual profiling with snakeviz (if installed)
pip install snakeviz
snakeviz orchestrator_profile.out
```

#### Memory Profiling
```bash
# Install memory profiler
pip install memory-profiler psutil

# Profile memory usage
uv run python -m memory_profiler .claude/orchestrator.py

# Line-by-line memory profiling
uv run python -c "
from memory_profiler import profile
# Add @profile decorator to functions you want to profile
"
```

### Network Debugging

#### Agent Communication Issues
```bash
# Test agent communication
uv run python -c "
from claude.agents.claude_agent import ClaudeAgent
agent = ClaudeAgent({'cli_path': 'claude', 'timeout': 30})
health = agent.health_check()
print(f'Agent health: {health}')
"

# Network connectivity test
ping -c 3 api.anthropic.com
nslookup api.anthropic.com
```

### Log Analysis

#### Structured Log Analysis
```bash
# View logs with filtering
tail -f .claude/logs/orchestrator.log | grep ERROR

# Parse JSON logs
cat .claude/logs/orchestrator.log | jq '.level == "ERROR"'

# Log level debugging
export LEANVIBE_SYSTEM_LOG_LEVEL=DEBUG
uv run python .claude/orchestrator.py 2>&1 | tee debug.log
```

## Getting Help

### Self-Diagnostics

#### Automated Health Check
```bash
# Run comprehensive health check
uv run python -c "
from claude.utils.health_check import comprehensive_health_check
report = comprehensive_health_check()
print(report)
"
```

#### System Information Collection
```bash
# Collect system information for bug reports
cat > debug_info.txt << EOF
# LeanVibe Agent Hive Debug Information
Date: $(date)
System: $(uname -a)
Python: $(python --version)
UV: $(uv --version)
Git: $(git --version)

# Environment Variables
$(env | grep LEANVIBE_ | sort)

# Configuration Status
$(uv run python -c "
from claude.config.config_loader import ConfigLoader
config = ConfigLoader()
print(f'Config valid: {config.validate()}')
")

# Test Status
$(uv run pytest --collect-only -q | tail -1)

# Performance Metrics
$(uv run python -c "
from claude.utils.performance_monitor import PerformanceMonitor
monitor = PerformanceMonitor()
metrics = monitor.collect_metrics()
print(f'Agent coordination latency: {metrics.coordination_latency_ms}ms')
print(f'Resource utilization: {metrics.resource_utilization_percent}%')
" 2>/dev/null || echo "Performance metrics unavailable")
EOF

cat debug_info.txt
```

### Community Support

#### GitHub Issues
1. **Search existing issues** before creating new ones
2. **Use issue templates** for bug reports and feature requests
3. **Include debug information** from the system information collection above
4. **Provide minimal reproduction steps**

#### Documentation Resources
- **[README.md](README.md)**: Quick start and overview
- **[DEVELOPMENT.md](DEVELOPMENT.md)**: Comprehensive development guide
- **[API_REFERENCE.md](API_REFERENCE.md)**: Complete API documentation
- **Phase 2 Progress**: `docs/PHASE2_PROGRESS_SUMMARY.md`

#### Expert Support
For complex issues requiring expert assistance:

1. **Prepare comprehensive information**:
   - Debug information output
   - Reproduction steps
   - Expected vs actual behavior
   - Configuration files (anonymized)

2. **Performance issues**:
   - Include profiling results
   - System resource usage
   - Load characteristics

3. **Multi-agent coordination issues**:
   - Agent status information
   - Coordination logs
   - Resource allocation details

---

**Troubleshooting Guide Version**: Phase 2.0  
**Last Updated**: July 14, 2025  
**Status**: Comprehensive coverage for Phase 1-2 issues | Ready for Phase 2.2 ML enhancement troubleshooting

This guide is regularly updated as new issues are discovered and resolved. For the latest troubleshooting information, please check the documentation and community discussions.