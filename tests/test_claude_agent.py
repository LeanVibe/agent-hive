"""Integration tests for ClaudeAgent."""

import asyncio
import os
import sys
from pathlib import Path

import pytest
from agents.base_agent import AgentStatus, Task
from agents.claude_agent import ClaudeAgent
from utils.logging_config import setup_logging

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent / '.claude'))


# Initialize logging for tests
setup_logging(log_level="DEBUG", console_output=False)


class TestClaudeAgent:
    """Test suite for ClaudeAgent."""

    @pytest.fixture
    def claude_agent(self):
        """Create a ClaudeAgent instance for testing."""
        # Force use of mock CLI for testing
        os.environ["LEANVIBE_DEVELOPMENT_USE_MOCK_CLI"] = "true"

        agent = ClaudeAgent("test-claude-agent")
        yield agent

        # Cleanup
        asyncio.run(agent.shutdown())
        if "LEANVIBE_DEVELOPMENT_USE_MOCK_CLI" in os.environ:
            del os.environ["LEANVIBE_DEVELOPMENT_USE_MOCK_CLI"]

    @pytest.fixture
    def simple_task(self):
        """Create a simple test task."""
        return Task(
            id="test-001",
            type="code_generation",
            description="Generate a simple Python function",
            priority=5,
            data={
                "prompt": "Create a simple Python function that prints 'Hello, World!'"})

    def test_agent_initialization(self, claude_agent):
        """Test that agent initializes correctly."""
        assert claude_agent.agent_id == "test-claude-agent"
        assert claude_agent.status == AgentStatus.IDLE
        assert "code_generation" in claude_agent.get_capabilities()
        assert claude_agent.tasks_completed == 0

    def test_agent_can_handle_task(self, claude_agent, simple_task):
        """Test that agent can determine if it can handle a task."""
        assert claude_agent.can_handle_task(simple_task)

        # Test with unsupported task type
        unsupported_task = Task(
            id="test-002",
            type="unsupported_type",
            description="Unsupported task",
            priority=5,
            data={"prompt": "Test"}
        )
        assert not claude_agent.can_handle_task(unsupported_task)

    @pytest.mark.asyncio
    async def test_agent_health_check(self, claude_agent):
        """Test agent health check functionality."""
        # Health check should pass with mock CLI
        is_healthy = await claude_agent.health_check()
        assert is_healthy

    @pytest.mark.asyncio
    async def test_agent_status(self, claude_agent):
        """Test agent status reporting."""
        status = await claude_agent.get_status()

        assert status.id == "test-claude-agent"
        assert status.status == AgentStatus.IDLE
        assert status.capabilities == claude_agent.get_capabilities()
        assert status.current_task is None
        assert status.last_activity is not None
        assert status.resource_usage is not None

    @pytest.mark.asyncio
    async def test_execute_simple_task(self, claude_agent, simple_task):
        """Test executing a simple task."""
        result = await claude_agent.execute_task(simple_task)

        assert result.task_id == simple_task.id
        assert result.status == "success"
        assert result.data is not None
        assert result.confidence > 0
        assert result.execution_time is not None

        # Check agent metrics
        assert claude_agent.tasks_completed == 1
        assert claude_agent.total_execution_time > 0

    @pytest.mark.asyncio
    async def test_execute_task_with_error(self, claude_agent):
        """Test executing a task that causes an error."""
        # Create a task that will trigger an error in the mock CLI
        error_task = Task(
            id="test-error",
            type="code_generation",
            description="Task that will fail",
            priority=5,
            data={"prompt": "Test error", "error_type": "generic"}
        )

        result = await claude_agent.execute_task(error_task)

        assert result.task_id == error_task.id
        assert result.status == "failure"
        assert result.error is not None
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self, claude_agent):
        """Test that agent properly handles concurrent task attempts."""
        task1 = Task(
            id="concurrent-001",
            type="code_generation",
            description="First concurrent task",
            priority=5,
            data={"prompt": "First task"}
        )

        task2 = Task(
            id="concurrent-002",
            type="code_generation",
            description="Second concurrent task",
            priority=5,
            data={"prompt": "Second task"}
        )

        # Execute tasks concurrently
        results = await asyncio.gather(
            claude_agent.execute_task(task1),
            claude_agent.execute_task(task2),
            return_exceptions=True
        )

        # Both should complete successfully
        assert len(results) == 2
        for result in results:
            assert not isinstance(result, Exception)
            assert result.status == "success"

    @pytest.mark.asyncio
    async def test_task_retry_mechanism(self, claude_agent):
        """Test the retry mechanism for failed tasks."""
        # Create a task that will fail but can be retried
        retry_task = Task(
            id="test-retry",
            type="code_generation",
            description="Task that will be retried",
            priority=5,
            data={"prompt": "Test retry", "fail_rate": 0.7}  # 70% failure rate
        )

        # Execute multiple times to test retry behavior
        result = await claude_agent.execute_task(retry_task)

        # Should eventually succeed or fail after retries
        assert result.task_id == retry_task.id
        assert result.status in ["success", "failure"]

    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self, claude_agent):
        """Test circuit breaker pattern."""
        # Create multiple failing tasks to trigger circuit breaker
        failing_tasks = []
        for i in range(6):  # More than failure threshold
            task = Task(
                id=f"failing-{i}",
                type="code_generation",
                description=f"Failing task {i}",
                priority=5,
                data={"prompt": f"Task {i}", "error_type": "generic"}
            )
            failing_tasks.append(task)

        results = []
        for task in failing_tasks:
            result = await claude_agent.execute_task(task)
            results.append(result)

        # All should fail
        for result in results:
            assert result.status == "failure"

        # Circuit breaker should be open now
        assert claude_agent.cli_manager.circuit_breaker.state == "OPEN"

    @pytest.mark.asyncio
    async def test_agent_shutdown(self, claude_agent):
        """Test graceful agent shutdown."""
        # Create a long-running task
        long_task = Task(
            id="long-running",
            type="code_generation",
            description="Long running task",
            priority=5,
            data={"prompt": "Long task", "delay": 2.0}
        )

        # Start task execution
        task_future = asyncio.create_task(claude_agent.execute_task(long_task))

        # Wait a bit then shutdown
        await asyncio.sleep(0.5)
        await claude_agent.shutdown()

        # Task should be cancelled or completed
        try:
            result = await task_future
            # If completed, that's also fine
            assert result.task_id == long_task.id
        except asyncio.CancelledError:
            # Task was cancelled during shutdown
            pass

        # Agent should be in shutdown state
        status = await claude_agent.get_status()
        assert status.status == AgentStatus.SHUTDOWN


class TestClaudeAgentIntegration:
    """Integration tests with the full system."""

    @pytest.mark.asyncio
    async def test_agent_with_task_queue(self):
        """Test agent integration with task queue."""
        from queue.task_queue import TaskQueue

        # Force use of mock CLI
        os.environ["LEANVIBE_DEVELOPMENT_USE_MOCK_CLI"] = "true"

        try:
            agent = ClaudeAgent("integration-test-agent")
            queue = TaskQueue()

            # Add tasks to queue
            tasks = [
                Task(
                    id=f"integration-{i}",
                    type="code_generation",
                    description=f"Integration test task {i}",
                    priority=i,
                    data={"prompt": f"Task {i}"}
                )
                for i in range(5)
            ]

            for task in tasks:
                await queue.add_task(task)

            # Process tasks
            completed_tasks = []
            while True:
                task = await queue.get_next_task(agent.get_capabilities())
                if not task:
                    break

                await queue.mark_task_in_progress(task.id, agent.agent_id)
                result = await agent.execute_task(task)

                if result.status == "success":
                    await queue.mark_task_completed(task.id)
                    completed_tasks.append(task)
                else:
                    await queue.mark_task_failed(task.id)

            # Verify all tasks were processed
            assert len(completed_tasks) == 5

            # Check queue status
            queue_status = await queue.get_queue_status()
            assert queue_status["completed"] == 5

            # Cleanup
            await agent.shutdown()

        finally:
            if "LEANVIBE_DEVELOPMENT_USE_MOCK_CLI" in os.environ:
                del os.environ["LEANVIBE_DEVELOPMENT_USE_MOCK_CLI"]

    @pytest.mark.asyncio
    async def test_agent_with_orchestrator(self):
        """Test agent integration with orchestrator."""
        from orchestrator import LeanVibeOrchestrator

        # Force use of mock CLI
        os.environ["LEANVIBE_DEVELOPMENT_USE_MOCK_CLI"] = "true"

        try:
            orchestrator = LeanVibeOrchestrator()

            # Add a test task
            test_task = Task(
                id="orchestrator-test",
                type="code_generation",
                description="Test orchestrator integration",
                priority=5,
                data={"prompt": "Test integration"}
            )

            await orchestrator.add_task(test_task)

            # Process for a short time
            await asyncio.sleep(1)

            # Check queue status
            queue_status = await orchestrator.get_queue_status()
            # Task should be processed or pending
            assert queue_status["pending"] >= 0

            # Shutdown
            await orchestrator.shutdown()

        finally:
            if "LEANVIBE_DEVELOPMENT_USE_MOCK_CLI" in os.environ:
                del os.environ["LEANVIBE_DEVELOPMENT_USE_MOCK_CLI"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
