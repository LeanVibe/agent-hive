# Development Guide

This guide provides a comprehensive overview of the LeanVibe Agent Hive project architecture, development workflow, and contribution guidelines for developers working on the AI orchestration system.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Component Architecture](#component-architecture)
- [Development Workflow](#development-workflow)
- [Testing Strategy](#testing-strategy)
- [Configuration Management](#configuration-management)
- [Code Quality & XP Principles](#code-quality--xp-principles)
- [Contribution Guidelines](#contribution-guidelines)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

LeanVibe Agent Hive is designed as a distributed multi-agent system with a central orchestrator managing specialized AI agents. The architecture follows modern software engineering principles with emphasis on testability, configurability, and maintainability.

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator                            │
│  - Task Distribution                                        │
│  - Agent Lifecycle Management                               │
│  - State Management                                         │
│  - Performance Monitoring                                   │
└─────────────────┬───────────────────────┬───────────────────┘
                  │                       │
    ┌─────────────▼─────────────┐ ┌──────▼──────────────────┐
    │      Task Queue           │ │   Configuration         │
    │  - Priority Management    │ │   - Centralized YAML    │
    │  - Dependency Handling    │ │   - Environment Override│
    │  - Async Operations       │ │   - Runtime Validation  │
    └─────────────┬─────────────┘ └─────────────────────────┘
                  │
    ┌─────────────▼─────────────────────────────────────────┐
    │                Agent Network                          │
    │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │
    │  │Claude Agent │ │Gemini Agent │ │Future Agents│     │
    │  │- Code Gen   │ │- Reviews    │ │- Specialized│     │
    │  │- Debugging  │ │- Analysis   │ │- Tasks      │     │
    │  └─────────────┘ └─────────────┘ └─────────────┘     │
    └───────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Modularity**: Each component has clear boundaries and responsibilities
2. **Testability**: Comprehensive test coverage with mock infrastructure
3. **Configurability**: Centralized configuration with environment overrides
4. **Resilience**: Circuit breaker patterns and retry logic
5. **Observability**: Structured logging and performance monitoring

## Component Architecture

### Core Components

#### 1. Orchestrator (`orchestrator.py`)
**Role**: Central coordination engine for the entire system

**Responsibilities**:
- Task lifecycle management
- Agent assignment and load balancing
- State persistence and recovery
- Performance monitoring and optimization
- Human intervention decision making

**Key Methods**:
- `get_next_priority()`: Intelligent task prioritization
- `execute_autonomously()`: Autonomous task execution
- `request_human_guidance()`: Escalation management

#### 2. Task Queue (`queue/task_queue.py`) ✅
**Status**: 16/16 tests passing - Production ready

**Features**:
- Priority-based task ordering
- Dependency management between tasks
- Timeout handling for long-running tasks
- Queue size limits and persistence
- Async operation support

**Usage Example**:
```python
queue = TaskQueue(max_size=1000)
await queue.add_task(task)
next_task = await queue.get_next_task(agent_capabilities)
await queue.mark_task_completed(task_id)
```

#### 3. Configuration System (`config/`) ✅
**Status**: 15/16 tests passing - Production ready

**Features**:
- Centralized YAML configuration
- Environment variable overrides
- Runtime validation
- Agent-specific settings
- Development/production modes

**Configuration Structure**:
```yaml
system:
  log_level: INFO
  debug_mode: true

agents:
  claude:
    cli_path: "claude"
    timeout: 300
    capabilities: ["code_generation"]

task_queue:
  max_queue_size: 1000
  default_priority: 5
```

#### 4. Agent Framework (`agents/`)

**BaseAgent** (Abstract Interface):
```python
class BaseAgent(ABC):
    @abstractmethod
    async def execute_task(self, task: Task) -> Result:
        pass
    
    @abstractmethod
    async def get_status(self) -> AgentInfo:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass
```

**ClaudeAgent** ✅ (Implemented):
- CLI subprocess management
- Circuit breaker integration
- Task serialization/deserialization
- Output parsing and error handling

#### 5. Circuit Breaker (`agents/claude_agent.py`) ✅
**Status**: 3/3 tests passing - Production ready

**Purpose**: Provides resilience for external CLI calls

**States**: CLOSED → OPEN → HALF_OPEN → CLOSED
**Features**: Configurable failure thresholds and recovery timeouts

### Supporting Infrastructure

#### Testing Framework ✅
**Mock CLI Infrastructure**:
- `testing/mock_cli/mock_claude.py`: Simulates Claude CLI responses
- `testing/mock_cli/mock_gemini.py`: Simulates Gemini CLI responses
- Configurable delays and failure rates for testing

**Test Categories**:
- **Unit Tests**: Component isolation testing
- **Integration Tests**: Cross-component workflow testing
- **Performance Tests**: Load and timing validation
- **Mock Tests**: CLI interaction simulation

#### Logging System ✅
**Structured Logging**:
- Correlation ID tracking across requests
- Performance timing integration
- Configurable log levels and formats
- File and console output support

## Development Workflow

### XP Principles Implementation

#### 1. Test-Driven Development (TDD)
**Process**:
1. Write failing test
2. Implement minimal code to pass
3. Refactor for quality
4. Repeat

**Example**:
```bash
# Write test first
pytest tests/unit/test_new_feature.py::test_feature_behavior -v

# Implement feature
# Run test again to verify
pytest tests/unit/test_new_feature.py -v
```

#### 2. Continuous Integration
**Quality Gates**:
- All tests must pass
- Configuration validation required
- Code coverage targets maintained
- No lint violations

#### 3. Pair Programming (Recommended)
**When to Use**:
- Complex algorithmic implementations
- Architecture decisions
- Critical bug fixes
- Knowledge transfer sessions

### Git Workflow

#### Branch Strategy
```bash
# Feature development
git checkout -b feature/task-priority-algorithm
git checkout -b fix/circuit-breaker-timeout
git checkout -b refactor/config-validation

# Integration branches  
git checkout -b integration/week3-completion
```

#### Commit Convention
```bash
# Format: type(scope): description
git commit -m "feat(task-queue): add dependency management"
git commit -m "fix(config): resolve environment override issue"
git commit -m "test(integration): add orchestrator workflow test"
```

### Development Environment Setup

#### 1. Initial Setup
```bash
# Clone repository
git clone https://github.com/leanvibe/agent-hive.git
cd agent-hive

# Setup Python environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Development Configuration
```bash
# Copy and modify configuration
cp .claude/config/config.yaml .claude/config/config.dev.yaml

# Enable development mode
export LEANVIBE_DEVELOPMENT_DEBUG_MODE=true
export LEANVIBE_DEVELOPMENT_USE_MOCK_CLI=true
```

#### 3. Verification
```bash
# Run test suite to verify setup
pytest -v

# Check configuration loading
python -c "from .claude.config.config_loader import ConfigLoader; print('Config OK')"
```

## Testing Strategy

### Test Architecture

#### Test Structure
```
tests/
├── unit/                    # Component isolation tests
│   ├── test_task_queue.py   # 16 async tests ✅
│   ├── test_config_loader.py # 15 configuration tests ✅
│   └── test_circuit_breaker.py # 3 resilience tests ✅
├── integration/             # Cross-component tests
│   ├── test_orchestrator_workflow.py
│   └── test_agent_coordination.py
├── performance/             # Load and timing tests
└── conftest.py             # Shared fixtures ✅
```

#### Test Categories

**Unit Tests** (Primary Focus):
```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific component
pytest tests/unit/test_task_queue.py -v

# Run with coverage
pytest tests/unit/ --cov=.claude --cov-report=html
```

**Integration Tests**:
```bash
# Test agent coordination
pytest tests/integration/test_orchestrator_workflow.py -v

# Test end-to-end scenarios
pytest tests/integration/ -v
```

**Performance Tests**:
```bash
# Run performance benchmarks
pytest tests/performance/ -v

# Run with performance markers
pytest -m performance -v
```

### Mock Infrastructure

#### Mock CLI Usage
**Configuration**:
```yaml
development:
  use_mock_cli: true
  mock_settings:
    claude_delay: 1.0      # Simulate response time
    failure_rate: 0.05     # 5% failure rate
```

**Custom Mock Responses**:
```python
# In test files
@pytest.fixture
def mock_claude_success():
    return {
        "status": "success",
        "output": "Generated code here",
        "execution_time": 2.5
    }
```

### Test Best Practices

#### 1. Async Testing
```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result.status == "success"
```

#### 2. Configuration Testing
```python
def test_config_override(tmp_path):
    config_file = tmp_path / "config.yaml"
    # Write test config
    # Test configuration loading
```

#### 3. Mock Usage
```python
def test_cli_integration(mock_claude_agent):
    # Use mock agent for reliable testing
    result = mock_claude_agent.execute_task(task)
    assert result.success
```

## Configuration Management

### Configuration Architecture

#### Centralized Configuration ✅
**Location**: `.claude/config/config.yaml`

**Structure**:
```yaml
# System-wide settings
system:
  log_level: INFO
  debug_mode: false
  max_concurrent_tasks: 10

# Agent configurations
agents:
  claude:
    cli_path: "claude"
    test_cli_path: "testing/mock_cli/mock_claude.py"
    timeout: 300
    capabilities: ["code_generation", "debugging"]

# Environment-specific overrides
environments:
  production:
    system:
      debug_mode: false
  testing:
    development:
      use_mock_cli: true
```

#### Environment Variable Overrides
**Convention**: `LEANVIBE_<SECTION>_<KEY>=<VALUE>`

**Examples**:
```bash
# Override system settings
export LEANVIBE_SYSTEM_LOG_LEVEL=DEBUG
export LEANVIBE_SYSTEM_DEBUG_MODE=true

# Override agent settings
export LEANVIBE_AGENTS_CLAUDE_TIMEOUT=600

# Override development settings
export LEANVIBE_DEVELOPMENT_USE_MOCK_CLI=false
```

#### Configuration Validation
```python
# Validate configuration at startup
config = ConfigLoader()
if not config.validate():
    raise ConfigurationError("Invalid configuration")

# Check specific requirements
assert config.get('agents.claude.cli_path') is not None
```

### Configuration Usage Patterns

#### 1. Component Configuration
```python
class MyComponent:
    def __init__(self):
        self.config = get_config()
        self.timeout = self.config.get('component.timeout', 30)
        self.debug = self.config.is_development_mode()
```

#### 2. Agent Configuration
```python
agent_config = config.get_agent_config('claude')
cli_path = config.get_cli_path('claude')  # Handles mock/production
timeout = agent_config.get('timeout', 300)
```

#### 3. Environment-Specific Settings
```python
# Configuration automatically selects environment
if config.get('development.use_mock_cli', False):
    cli_manager = MockCLIManager()
else:
    cli_manager = ProductionCLIManager()
```

## Code Quality & XP Principles

### Code Standards

#### 1. Python Code Style
- Follow PEP 8 guidelines
- Use type hints for all functions
- Document complex algorithms
- Keep functions focused and small

#### 2. Async Programming
```python
# Correct async patterns
async def async_operation():
    async with self._lock:
        # Thread-safe operations
        result = await external_service()
    return result

# Proper error handling
try:
    result = await operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    raise
```

#### 3. Testing Standards
```python
# Descriptive test names
def test_task_queue_priority_ordering_with_dependencies():
    """Test that tasks are returned in priority order while respecting dependencies."""
    pass

# Comprehensive assertions
assert result.status == "success"
assert result.execution_time < 5.0
assert result.confidence > 0.8
```

### Quality Gates

#### Pre-Commit Checks
```bash
# Run before every commit
pytest                          # All tests pass
python -m flake8 .claude/       # Lint checks
python -m mypy .claude/         # Type checking
pytest --cov=.claude --cov-fail-under=80  # Coverage threshold
```

#### Integration Quality Gates
```bash
# Before merging
pytest tests/integration/ -v    # Integration tests pass
pytest -m performance -v       # Performance benchmarks pass
python .claude/config/config_loader.py  # Configuration validates
```

### Performance Guidelines

#### 1. Async Best Practices
- Use proper async context managers
- Avoid blocking operations in async functions
- Implement timeouts for external operations

#### 2. Memory Management
- Use weak references where appropriate
- Implement proper cleanup in async generators
- Monitor memory usage in long-running operations

#### 3. Logging Performance
```python
# Efficient logging
logger.debug("Processing task %s", task_id)  # Use formatting

# Avoid expensive operations in log messages
logger.debug("Task details: %s", lambda: expensive_operation())
```

## Contribution Guidelines

### Getting Started

#### 1. Fork and Clone
```bash
# Fork repository on GitHub
git clone https://github.com/your-username/agent-hive.git
cd agent-hive
```

#### 2. Setup Development Environment
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests to verify setup
pytest -v
```

#### 3. Choose an Issue
- Look for "good first issue" labels
- Check current priorities in docs/TODO.md
- Discuss complex changes in issues first

### Development Process

#### 1. Create Feature Branch
```bash
git checkout -b feature/your-feature-name
```

#### 2. Follow TDD Workflow
```bash
# Write failing test
pytest tests/unit/test_your_feature.py::test_new_behavior -v

# Implement feature
# Verify test passes
pytest tests/unit/test_your_feature.py -v

# Run full test suite
pytest -v
```

#### 3. Code Quality Checks
```bash
# Lint code
python -m flake8 .claude/

# Type checking
python -m mypy .claude/

# Coverage check
pytest --cov=.claude --cov-report=html
```

#### 4. Submit Pull Request
**PR Requirements**:
- [ ] All tests pass
- [ ] Code coverage maintained/improved
- [ ] Configuration changes documented
- [ ] Integration tests updated if needed
- [ ] README/docs updated if applicable

**PR Template**:
```markdown
## Summary
Brief description of changes

## Changes Made
- [ ] Feature implementation
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Configuration changes

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project standards
- [ ] All tests pass
- [ ] Configuration validated
- [ ] Documentation updated
```

### Review Process

#### 1. Automated Checks
- Test suite execution
- Code quality validation
- Configuration verification
- Coverage reporting

#### 2. Code Review Guidelines
**For Reviewers**:
- Focus on architecture and design
- Verify test coverage
- Check error handling
- Validate configuration changes

**For Contributors**:
- Respond to feedback promptly
- Update tests based on review
- Maintain code quality standards

## Troubleshooting

### Common Development Issues

#### 1. Import Path Issues
**Problem**: `ModuleNotFoundError: No module named 'config'`

**Solution**:
```python
# Add project root to Python path
import sys
sys.path.insert(0, '.claude')
from config.config_loader import ConfigLoader
```

#### 2. Async Test Configuration
**Problem**: `pytest-asyncio` configuration issues

**Solution**:
```ini
# pytest.ini
[tool:pytest]
asyncio_mode = auto
testpaths = tests
addopts = -v --tb=short
```

#### 3. Configuration Loading Errors
**Problem**: Configuration validation failures

**Solution**:
```python
# Debug configuration loading
config = ConfigLoader()
print("Config loaded:", config._config)
print("Validation:", config.validate())
```

#### 4. Mock CLI Issues
**Problem**: Mock CLIs not responding correctly

**Solution**:
```bash
# Verify mock CLI executable
chmod +x .claude/testing/mock_cli/mock_claude.py

# Test mock CLI directly
python .claude/testing/mock_cli/mock_claude.py --help
```

### Performance Troubleshooting

#### 1. Slow Test Execution
**Investigation**:
```bash
# Profile test execution
pytest --durations=10 -v

# Run specific slow tests
pytest tests/unit/test_slow_component.py -v -s
```

#### 2. Memory Usage Issues
**Monitoring**:
```python
# Add memory monitoring to tests
import psutil
process = psutil.Process()
print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

#### 3. Configuration Performance
**Optimization**:
```python
# Cache configuration for repeated access
config = get_config()  # Uses global singleton
value = config.get('key')  # Cached access
```

### Getting Help

#### 1. Documentation Resources
- Project README.md
- API documentation in docstrings
- Test examples in test files
- Configuration examples in config.yaml

#### 2. Debugging Tools
```bash
# Verbose test output
pytest -v -s

# Debug configuration
python -c "from .claude.config.config_loader import ConfigLoader; c = ConfigLoader(); print(c._config)"

# Check system status
python .claude/orchestrator.py --health-check
```

#### 3. Community Support
- GitHub Issues for bug reports
- GitHub Discussions for questions
- Pull Request reviews for code feedback

---

**Note**: This development guide is a living document that evolves with the project. Keep it updated as new components are added and processes are refined.