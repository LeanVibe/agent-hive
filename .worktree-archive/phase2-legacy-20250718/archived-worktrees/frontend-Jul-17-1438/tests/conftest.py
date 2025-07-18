"""
Pytest configuration and fixtures for LeanVibe Orchestrator tests.

This module provides common fixtures and configurations used across all tests.
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# Add project root and .claude to path for imports
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / ".claude"))

# Import components for testing
try:
    from task_queue_module.task_queue import Task, TaskQueue
    from agents.base_agent import BaseAgent, AgentStatus, AgentInfo  # Fixed: AgentStatus is the enum
    from config.config_loader import ConfigLoader
    from utils.logging_config import get_logger
except ImportError as e:
    print(f"Import error in conftest: {e}")
    # Create minimal mock classes for testing
    class Task:
        pass
    class TaskQueue:
        pass
    class BaseAgent:
        pass
    class AgentStatus:
        pass
    class AgentInfo:
        pass
    class ConfigLoader:
        pass


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_directory():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    from datetime import datetime
    return Task(
        id="test-task-001",
        type="code_generation",
        description="Generate a simple Python function",
        priority=5,
        data={"prompt": "Create a hello world function"},
        created_at=datetime.now()
    )


@pytest.fixture
def sample_tasks():
    """Create multiple sample tasks for testing."""
    from datetime import datetime
    tasks = []
    for i in range(5):
        task = Task(
            id=f"test-task-{i:03d}",
            type="code_generation",
            description=f"Generate function #{i}",
            priority=i + 1,
            data={"prompt": f"Create function {i}"},
            created_at=datetime.now()
        )
        tasks.append(task)
    return tasks


@pytest_asyncio.fixture
async def task_queue():
    """Create a TaskQueue instance for testing."""
    queue = TaskQueue()
    yield queue
    # Cleanup - no explicit cleanup needed for TaskQueue


@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    agent = AsyncMock(spec=BaseAgent)
    agent.agent_id = "mock-agent-001"
    agent.get_capabilities.return_value = ["code_generation", "text_processing"]
    agent.can_handle_task.return_value = True
    agent.get_status.return_value = AgentInfo(
        id="mock-agent-001",
        status=AgentStatus.IDLE,
        capabilities=["code_generation", "text_processing"],
        current_task=None,
        last_activity=datetime.now()
    )
    agent.health_check.return_value = True
    return agent


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config_data = {
        "system": {
            "log_level": "INFO",
            "debug_mode": True
        },
        "agents": {
            "claude": {
                "cli_path": "/mock/claude",
                "test_cli_path": "/mock/claude_test",
                "timeout": 300,
                "max_retries": 3
            },
            "gemini": {
                "cli_path": "/mock/gemini",
                "test_cli_path": "/mock/gemini_test",
                "timeout": 180
            }
        },
        "task_queue": {
            "max_queue_size": 1000,
            "default_priority": 5
        },
        "development": {
            "debug_mode": True,
            "use_mock_cli": True
        }
    }

    config = MagicMock(spec=ConfigLoader)
    config.get.side_effect = lambda key, default=None: _get_nested_value(config_data, key, default)
    config.get_agent_config.side_effect = lambda agent: config_data.get("agents", {}).get(agent, {})
    config.should_use_mock_cli.return_value = True
    config.is_development_mode.return_value = True
    config.get_cli_path.side_effect = lambda agent: f"/mock/{agent}_test"

    return config


def _get_nested_value(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Helper function to get nested dictionary values using dot notation."""
    keys = key.split('.')
    current = data

    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return default

    return current


@pytest.fixture
def mock_cli_process():
    """Create a mock CLI process for testing subprocess interactions."""
    process = AsyncMock()
    process.returncode = 0
    process.stdout.read.return_value = b'{"status": "success", "response": "Mock response"}'
    process.stderr.read.return_value = b''
    process.wait.return_value = 0
    return process


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
async def circuit_breaker_config():
    """Configuration for circuit breaker testing."""
    return {
        "failure_threshold": 3,
        "recovery_timeout": 1.0,  # Short timeout for testing
        "expected_exception": Exception
    }


@pytest.fixture
def performance_thresholds():
    """Performance thresholds for benchmarking tests."""
    return {
        "task_execution_max_time": 5.0,  # seconds
        "queue_operation_max_time": 0.1,  # seconds
        "config_load_max_time": 0.05,  # seconds
        "max_memory_mb": 100  # MB
    }


# Test utilities
class TestUtils:
    """Utility functions for tests."""

    @staticmethod
    async def wait_for_condition(condition_func, timeout=5.0, interval=0.1):
        """Wait for a condition to become true within timeout."""
        import asyncio
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            if condition_func():
                return True
            await asyncio.sleep(interval)

        return False

    @staticmethod
    def assert_task_equal(task1: Task, task2: Task):
        """Assert that two tasks are equal (excluding timestamps)."""
        assert task1.id == task2.id
        assert task1.type == task2.type
        assert task1.description == task2.description
        assert task1.priority == task2.priority
        assert task1.data == task2.data


# Make TestUtils available as a fixture
@pytest.fixture
def test_utils():
    """Provide test utility functions."""
    return TestUtils
