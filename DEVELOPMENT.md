# LeanVibe Agent Hive - Development Guide

**Production-Ready AI Orchestration System Development**

## 🎯 Overview

This guide provides comprehensive development standards, security practices, and contribution guidelines for the LeanVibe Agent Hive project. Whether you're extending the system, integrating it with your tools, or contributing to the codebase, this document ensures consistent, secure, and maintainable development.

## 🚀 Quick Start for Developers

### Prerequisites
- Python 3.8+
- Git
- Docker (optional, for containerized development)
- UV or pip for dependency management

### Development Setup
```bash
# Clone and set up development environment
git clone https://github.com/LeanVibe/agent-hive.git
cd agent-hive

# Install development dependencies
pip install -r requirements.txt -r requirements-dev.txt
# OR using UV (recommended)
uv sync --dev

# Set up pre-commit hooks
pre-commit install

# Verify installation
pytest tests/ -v
```

## 🔒 Security Standards

### Critical Security Requirements

#### Cryptographic Operations
```python
# ✅ CORRECT - Specify usedforsecurity for non-security hashing
import hashlib
feature_hash = hashlib.md5(data.encode(), usedforsecurity=False).hexdigest()

# ❌ INCORRECT - Security warning triggered
feature_hash = hashlib.md5(data.encode()).hexdigest()
```

#### Database Operations
```python
# ✅ CORRECT - Parameterized queries
cursor.execute(
    "DELETE FROM table WHERE date < datetime('now', ?)",
    (f'-{days} days',)
)

# ❌ INCORRECT - SQL injection vulnerability
cursor.execute(f"DELETE FROM table WHERE date < datetime('now', '-{days} days')")
```

#### Input Validation
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
- **Dependency Scanning**: `safety check` before each commit
- **Secret Detection**: Use git-secrets or similar tools

## 🏗️ Code Quality Standards

### Python Standards
- **PEP 8 Compliance**: Use `black` and `flake8` for formatting
- **Type Hints**: All public functions must have type annotations
- **Docstrings**: Google-style docstrings for all public APIs
- **Test Coverage**: Minimum 80% coverage for new code

### Example Code Structure
```python
"""
Module for agent coordination functionality.

This module provides the core coordination logic for multi-agent
systems including task assignment and resource management.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class AgentTask:
    """Represents a task assigned to an agent.
    
    Attributes:
        task_id: Unique identifier for the task
        description: Human-readable task description
        priority: Task priority (1-10, 10 being highest)
        estimated_duration: Estimated completion time in minutes
    """
    task_id: str
    description: str
    priority: int = 5
    estimated_duration: Optional[int] = None


def assign_task(agent_id: str, task: AgentTask) -> bool:
    """Assign a task to a specific agent.
    
    Args:
        agent_id: Unique identifier of the target agent
        task: Task object containing task details
        
    Returns:
        True if task assignment successful, False otherwise
        
    Raises:
        ValueError: If agent_id is invalid or task is malformed
        AgentUnavailableError: If target agent is not available
    """
    if not agent_id or not isinstance(agent_id, str):
        raise ValueError("agent_id must be a non-empty string")
    
    # Implementation details...
    return True
```

## 🧪 Testing Standards

### Test Structure
```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for component interaction
├── performance/    # Performance benchmarks and stress tests
├── security/       # Security-specific test suites
└── fixtures/       # Shared test fixtures and data
```

### Testing Requirements
- **Unit Tests**: Every public function/method
- **Integration Tests**: All component interactions
- **Performance Tests**: Critical path performance validation
- **Security Tests**: Authentication, authorization, input validation

### Example Test
```python
import pytest
from unittest.mock import Mock, patch

from agent_hive.coordination import assign_task, AgentTask


class TestTaskAssignment:
    """Test suite for task assignment functionality."""
    
    def test_assign_task_success(self):
        """Test successful task assignment."""
        task = AgentTask(
            task_id="test-123",
            description="Test task",
            priority=5
        )
        
        result = assign_task("agent-001", task)
        
        assert result is True
    
    def test_assign_task_invalid_agent(self):
        """Test task assignment with invalid agent ID."""
        task = AgentTask(task_id="test-123", description="Test task")
        
        with pytest.raises(ValueError, match="agent_id must be"):
            assign_task("", task)
    
    @patch('agent_hive.coordination.agent_registry')
    def test_assign_task_agent_unavailable(self, mock_registry):
        """Test task assignment when agent is unavailable."""
        mock_registry.is_available.return_value = False
        task = AgentTask(task_id="test-123", description="Test task")
        
        with pytest.raises(AgentUnavailableError):
            assign_task("agent-001", task)
```

## 🔧 Contributing Guidelines

### Pull Request Process
1. **Create Feature Branch**: `git checkout -b feature/your-feature-name`
2. **Write Tests First**: Follow TDD approach
3. **Implement Feature**: Write minimal code to pass tests
4. **Run Full Test Suite**: `pytest tests/ --cov=.`
5. **Security Scan**: `bandit -r . --severity-level medium`
6. **Update Documentation**: Update relevant docs and docstrings
7. **Submit PR**: Include description, test results, and performance impact

### Commit Message Format
```
type(scope): short description

Longer description if needed explaining the why, not the what.

Fixes #123
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

### Code Review Checklist
- [ ] Tests pass and provide adequate coverage
- [ ] Security scan passes without HIGH severity issues
- [ ] Documentation updated and accurate
- [ ] Performance impact assessed
- [ ] Breaking changes documented
- [ ] API changes backward compatible or properly versioned

## 🛠️ Development Tools

### Recommended IDE Configuration
```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.banditEnabled": true,
    "python.formatting.provider": "black"
}
```

### Pre-commit Configuration
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-r', '.', '--severity-level', 'medium']
```

## 🚀 Advanced Development

### Adding New Agent Types
1. **Create Agent Class**: Inherit from `BaseAgent`
2. **Define Capabilities**: Implement required methods
3. **Add Configuration**: Update agent registry
4. **Write Tests**: Unit and integration tests
5. **Update Documentation**: Add to agent documentation

### Extending API Gateway
1. **Define Endpoints**: Add new route handlers
2. **Add Authentication**: Apply appropriate middleware
3. **Validate Input**: Implement request validation
4. **Add Monitoring**: Include metrics and logging
5. **Test Thoroughly**: Security and performance testing

### Performance Optimization
- **Profile First**: Use `cProfile` to identify bottlenecks
- **Benchmark**: Establish baseline performance metrics
- **Optimize**: Focus on critical path improvements
- **Measure**: Validate improvements with benchmarks
- **Document**: Update BENCHMARKS.md with new metrics

## 📚 Additional Resources

- **Architecture Guide**: See `docs/ARCHITECTURE.md` for system design
- **API Reference**: Complete API documentation in `docs/API_REFERENCE.md`
- **Deployment Guide**: Production deployment instructions
- **Troubleshooting**: Common issues and solutions

## 🤝 Community and Support

- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Community support and collaboration
- **Security Issues**: Private disclosure to maintainers
- **Documentation**: Contributions welcome for user guides

---

**Remember**: This is a production system used by real teams. Prioritize security, reliability, and user experience in all development decisions.