# LeanVibe Agent Hive - Coding Standards and Best Practices

**Date**: 2025-07-18  
**Version**: 1.0  
**Maintainer**: Technical Debt Cleanup Agent

## 🎯 Overview

This document establishes coding standards and best practices for the LeanVibe Agent Hive project, based on comprehensive technical debt analysis and security audit findings.

## 🔒 Security Standards

### Critical Security Requirements

#### 1. **Cryptographic Operations**
```python
# ✅ CORRECT - Specify usedforsecurity for non-security hashing
import hashlib
feature_hash = hashlib.md5(data.encode(), usedforsecurity=False).hexdigest()

# ❌ INCORRECT - Security warning triggered
feature_hash = hashlib.md5(data.encode()).hexdigest()
```

#### 2. **Database Operations**
```python
# ✅ CORRECT - Parameterized queries
cursor.execute(
    "DELETE FROM table WHERE date < datetime('now', ?)",
    (f'-{days} days',)
)

# ❌ INCORRECT - SQL injection vulnerability
cursor.execute(f"DELETE FROM table WHERE date < datetime('now', '-{days} days')")
```

#### 3. **Input Validation**
```python
# ✅ CORRECT - Validate all external inputs
def process_user_input(data: str) -> str:
    if not isinstance(data, str):
        raise ValueError("Input must be string")
    if len(data) > MAX_INPUT_LENGTH:
        raise ValueError("Input too long")
    return sanitize(data)
```

### Security Scanning Requirements
- **Pre-commit**: Run `bandit -r . --severity-level medium`
- **Zero Tolerance**: No HIGH severity security issues allowed
- **Documentation**: All security exceptions must be documented

## 📦 Package Structure Standards

### Proper Python Packaging

#### ✅ CORRECT Package Structure
```
leanvibe/
├── __init__.py              # Package initialization
├── cli.py                   # Command-line interface
├── orchestration/           # Core orchestration logic
│   ├── __init__.py
│   ├── coordinator.py
│   └── models.py
├── intelligence/            # AI and ML components
│   ├── __init__.py
│   ├── confidence_tracker.py
│   └── context_monitor.py
├── state/                   # State management
│   ├── __init__.py
│   ├── state_manager.py
│   └── git_milestone_manager.py
└── external_api/            # External integrations
    ├── __init__.py
    ├── webhook_server.py
    └── api_gateway.py
```

#### ❌ INCORRECT Import Patterns
```python
# NEVER use sys.path manipulation
import sys
sys.path.insert(0, '/some/path')  # ❌ Fragile and breaks packaging

# NEVER use relative path strings
from '../state/state_manager' import StateManager  # ❌ Not portable
```

#### ✅ CORRECT Import Patterns
```python
# Use proper relative imports
from .state.state_manager import StateManager

# Use absolute imports when appropriate
from leanvibe.intelligence.confidence_tracker import ConfidenceTracker

# Use package-level imports
from leanvibe.state import StateManager
```

## 🧪 Testing Standards

### Test Organization
```
tests/
├── unit/                    # Unit tests for individual modules
├── integration/             # Integration tests for workflows
├── external_api/            # API integration tests
├── performance/             # Performance benchmarks
└── conftest.py             # Shared test configuration
```

### Test Quality Requirements
- **Coverage Minimum**: 75% for all new code
- **Import Safety**: No `sys.path` manipulation in tests
- **Isolation**: Each test must be independent
- **Performance**: Tests should complete in <30 seconds

### Test Patterns
```python
# ✅ CORRECT - Proper test structure
import pytest
from leanvibe.state import StateManager

class TestStateManager:
    @pytest.fixture
    def state_manager(self, tmp_path):
        return StateManager(tmp_path)
    
    def test_checkpoint_creation(self, state_manager):
        # Test implementation
        pass

# ❌ INCORRECT - sys.path in tests
def test_imports():
    import sys
    sys.path.append('.claude')  # ❌ Makes tests fragile
```

## 📝 Code Quality Standards

### File Size Limits
- **Maximum Function**: 50 lines
- **Maximum Class**: 300 lines  
- **Maximum Module**: 500 lines
- **Exceptions**: Must be documented and justified

### Complexity Guidelines
- **Cyclomatic Complexity**: Max 10 per function
- **Nesting Depth**: Max 4 levels
- **Parameters**: Max 5 per function

### Documentation Requirements
```python
class ComponentManager:
    """Manages component lifecycle and dependencies.
    
    This class handles the creation, configuration, and cleanup
    of system components with proper dependency injection.
    
    Args:
        config: Configuration object with component settings
        logger: Optional logger instance for debugging
        
    Raises:
        ComponentError: When component initialization fails
        ConfigurationError: When config is invalid
        
    Example:
        >>> manager = ComponentManager(config)
        >>> component = manager.create('webhook_server')
        >>> manager.start(component)
    """
```

## ⚡ Performance Standards

### Async/Await Patterns
```python
# ✅ CORRECT - Proper async patterns
async def process_batch(items: List[Item]) -> List[Result]:
    tasks = [process_item(item) for item in items]
    return await asyncio.gather(*tasks)

# ❌ INCORRECT - Blocking in async function
async def bad_process(items):
    results = []
    for item in items:
        result = sync_process(item)  # ❌ Blocks event loop
        results.append(result)
    return results
```

### Memory Management
```python
# ✅ CORRECT - Resource cleanup
class DatabaseManager:
    async def __aenter__(self):
        self.connection = await create_connection()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            await self.connection.close()

# Usage
async with DatabaseManager() as db:
    await db.execute_query()
```

### Performance Targets
- **Response Time**: <200ms for API calls
- **Memory Usage**: <100MB for CLI operations
- **Startup Time**: <2 seconds for CLI initialization
- **Database Queries**: <50ms for simple operations

## 🔧 Configuration Management

### Single Source of Truth
```python
# ✅ CORRECT - Centralized configuration
from leanvibe.config import settings

# Access all config through single interface
database_url = settings.DATABASE_URL
api_timeout = settings.API_TIMEOUT
```

### Configuration Hierarchy
1. **Environment Variables** (highest priority)
2. **Configuration Files** (YAML/TOML)
3. **Default Values** (lowest priority)

### Environment-Specific Settings
```yaml
# config/development.yaml
database:
  url: "sqlite:///dev.db"
  echo: true

# config/production.yaml  
database:
  url: "${DATABASE_URL}"
  echo: false
```

## 🚨 Error Handling Standards

### Exception Hierarchy
```python
class LeanVibeError(Exception):
    """Base exception for all LeanVibe errors."""

class ConfigurationError(LeanVibeError):
    """Configuration-related errors."""

class ComponentError(LeanVibeError):
    """Component lifecycle errors."""
```

### Error Context
```python
# ✅ CORRECT - Provide context
try:
    result = risky_operation(data)
except ValueError as e:
    logger.error(f"Failed to process {data.id}: {e}")
    raise ComponentError(f"Data processing failed for {data.id}") from e
```

## 📊 Monitoring and Logging

### Structured Logging
```python
import structlog

logger = structlog.get_logger()

# ✅ CORRECT - Structured logs
logger.info(
    "Processing batch",
    batch_id=batch.id,
    item_count=len(batch.items),
    duration_ms=duration
)
```

### Metrics Collection
```python
# ✅ CORRECT - Track key metrics
@metrics.timer('component.operation.duration')
@metrics.counter('component.operation.calls')
async def critical_operation():
    # Operation implementation
    pass
```

## 🔄 Development Workflow

### Pre-commit Checklist
- [ ] Security scan passes (bandit)
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Tests pass with coverage ≥75%
- [ ] No `sys.path` manipulation
- [ ] Documentation updated
- [ ] Performance impact assessed

### Code Review Requirements
- **Security**: All security-related changes require review
- **Architecture**: Major structural changes require design review
- **Performance**: Changes affecting >10% performance require benchmarks
- **Documentation**: Public API changes require documentation updates

## 🎯 Migration Guidelines

### From Legacy Patterns
1. **Remove sys.path usage**: Convert to proper imports
2. **Package structure**: Move modules to appropriate packages
3. **Configuration**: Consolidate config systems
4. **Testing**: Fix import errors and improve coverage

### Gradual Improvement
- **Phase 1**: Critical security and import fixes
- **Phase 2**: Test coverage and quality improvements  
- **Phase 3**: Performance optimization and monitoring
- **Phase 4**: Advanced features and tooling

## ✅ Success Metrics

### Code Quality KPIs
- **Security**: Zero HIGH severity vulnerabilities
- **Coverage**: ≥75% test coverage maintained
- **Performance**: All targets met consistently
- **Maintainability**: No modules >500 lines
- **Documentation**: All public APIs documented

### Development Velocity KPIs
- **Build Time**: <30 seconds for full pipeline
- **Test Time**: <5 minutes for full suite
- **Deploy Time**: <10 minutes to production
- **Mean Time to Fix**: <2 hours for critical issues

---

**Enforcement**: These standards are enforced through automated tooling in pre-commit hooks and CI/CD pipelines.

**Updates**: This document is versioned and updated as the project evolves.

**Questions**: Contact the Technical Architecture team for clarifications or exceptions.