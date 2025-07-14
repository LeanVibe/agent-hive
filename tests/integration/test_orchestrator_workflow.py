"""
Integration tests for Orchestrator workflow.

Tests the main orchestrator workflow with mock agents (happy path scenarios).
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Import the components under test
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / ".claude"))

from orchestrator import LeanVibeOrchestrator
from task_queue_module.task_queue import Task
from agents.base_agent import AgentStatus, AgentStatusEnum


class TestOrchestratorWorkflow:
    """Integration test cases for orchestrator workflow."""

    @pytest.fixture
    async def orchestrator_with_mock_agents(self, mock_config):
        """Create orchestrator with mock agents for testing."""
        with patch('claude.orchestrator.get_config', return_value=mock_config):
            with patch('claude.orchestrator.ClaudeAgent') as mock_claude_agent_class:
                # Create mock agent instance
                mock_agent = AsyncMock()
                mock_agent.agent_id = "mock-claude-primary"
                mock_agent.get_capabilities.return_value = ["code_generation", "text_processing"]
                mock_agent.can_handle_task.return_value = True
                mock_agent.get_status.return_value = AgentStatus(
                    agent_id="mock-claude-primary",
                    status=AgentStatusEnum.IDLE,
                    current_task_id=None,
                    last_heartbeat=datetime.now(),
                    capabilities=["code_generation", "text_processing"]
                )
                mock_agent.health_check.return_value = True
                
                # Mock successful task execution
                mock_result = MagicMock()
                mock_result.status = "success"
                mock_result.data = {"response": "Mock task completed successfully"}
                mock_agent.execute_task.return_value = mock_result
                
                mock_claude_agent_class.return_value = mock_agent
                
                # Create orchestrator
                orchestrator = LeanVibeOrchestrator()
                yield orchestrator
                
                # Cleanup
                await orchestrator.shutdown()

    @pytest.mark.integration
    async def test_basic_task_execution_workflow(self, orchestrator_with_mock_agents, sample_task):
        """Test basic task execution workflow from start to finish."""
        orchestrator = orchestrator_with_mock_agents
        
        # Add a task to the queue
        result = await orchestrator.add_task(sample_task)
        assert result is True
        
        # Verify task is in queue
        queue_status = await orchestrator.get_queue_status()
        assert queue_status["pending_tasks"] == 1
        
        # Get next priority work item
        work_item = await orchestrator.get_next_priority()
        assert work_item is not None
        assert work_item.id == sample_task.id
        
        # Execute the task autonomously
        await orchestrator.execute_autonomously(work_item)
        
        # Verify task is completed
        final_status = await orchestrator.get_queue_status()
        assert final_status["completed_tasks"] == 1
        assert final_status["pending_tasks"] == 0

    @pytest.mark.integration
    async def test_multiple_tasks_priority_handling(self, orchestrator_with_mock_agents, sample_tasks):
        """Test handling multiple tasks with different priorities."""
        orchestrator = orchestrator_with_mock_agents
        
        # Add all tasks
        for task in sample_tasks:
            await orchestrator.add_task(task)
        
        # Process tasks one by one
        completed_tasks = []
        while True:
            work_item = await orchestrator.get_next_priority()
            if work_item is None:
                break
            
            await orchestrator.execute_autonomously(work_item)
            completed_tasks.append(work_item)
        
        # Verify all tasks completed
        assert len(completed_tasks) == len(sample_tasks)
        
        # Verify they were processed in priority order (highest first)
        priorities = [task.priority for task in completed_tasks]
        assert priorities == sorted(priorities, reverse=True)

    @pytest.mark.integration 
    async def test_agent_health_monitoring(self, orchestrator_with_mock_agents):
        """Test agent health monitoring integration."""
        orchestrator = orchestrator_with_mock_agents
        
        # Start health monitoring (simulate brief run)
        health_task = asyncio.create_task(orchestrator._monitor_agent_health())
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        # Stop monitoring
        orchestrator.running = False
        
        try:
            await asyncio.wait_for(health_task, timeout=1.0)
        except asyncio.TimeoutError:
            health_task.cancel()

    @pytest.mark.integration
    async def test_task_failure_handling(self, orchestrator_with_mock_agents, sample_task):
        """Test handling of task execution failures."""
        orchestrator = orchestrator_with_mock_agents
        
        # Make the agent fail the task
        agent = list(orchestrator.agents.values())[0]
        mock_result = MagicMock()
        mock_result.status = "error"
        mock_result.error = "Mock task failure"
        agent.execute_task.return_value = mock_result
        
        # Add and execute task
        await orchestrator.add_task(sample_task)
        work_item = await orchestrator.get_next_priority()
        await orchestrator.execute_autonomously(work_item)
        
        # Verify task is marked as failed but can retry
        queue_status = await orchestrator.get_queue_status()
        assert queue_status["pending_tasks"] == 1  # Back in pending for retry
        assert queue_status["completed_tasks"] == 0

    @pytest.mark.integration
    async def test_no_suitable_agent_handling(self, orchestrator_with_mock_agents):
        """Test handling when no suitable agent is available."""
        orchestrator = orchestrator_with_mock_agents
        
        # Create task that no agent can handle
        unsupported_task = Task(
            id="unsupported-task",
            type="unsupported_type",
            description="Task with unsupported type",
            priority=5,
            data={},
            created_at=datetime.now()
        )
        
        # Make agent unable to handle this task
        agent = list(orchestrator.agents.values())[0]
        agent.can_handle_task.return_value = False
        
        await orchestrator.add_task(unsupported_task)
        work_item = await orchestrator.get_next_priority()
        
        # Should handle gracefully without crashing
        await orchestrator.execute_autonomously(work_item)
        
        # Task should be marked as failed
        queue_status = await orchestrator.get_queue_status()
        assert queue_status["pending_tasks"] == 1  # Back in pending for retry

    @pytest.mark.integration
    async def test_agent_busy_handling(self, orchestrator_with_mock_agents, sample_task):
        """Test handling when agent is busy."""
        orchestrator = orchestrator_with_mock_agents
        
        # Make agent appear busy
        agent = list(orchestrator.agents.values())[0]
        agent.get_status.return_value = AgentStatus(
            agent_id="mock-claude-primary",
            status=AgentStatusEnum.BUSY,
            current_task_id="other-task",
            last_heartbeat=datetime.now(),
            capabilities=["code_generation", "text_processing"]
        )
        
        await orchestrator.add_task(sample_task)
        
        # Should not get any work item when agent is busy
        work_item = await orchestrator.get_next_priority()
        assert work_item is None

    @pytest.mark.integration
    async def test_task_capability_matching(self, orchestrator_with_mock_agents):
        """Test task-agent capability matching."""
        orchestrator = orchestrator_with_mock_agents
        
        # Create task requiring specific capability
        specialized_task = Task(
            id="specialized-task",
            type="image_processing",
            description="Process an image",
            priority=5,
            data={},
            created_at=datetime.now()
        )
        
        # Agent doesn't have image processing capability
        agent = list(orchestrator.agents.values())[0]
        agent.get_capabilities.return_value = ["code_generation", "text_processing"]
        agent.can_handle_task.return_value = False
        
        await orchestrator.add_task(specialized_task)
        
        # Should not get task due to capability mismatch
        work_item = await orchestrator.get_next_priority()
        assert work_item is None

    @pytest.mark.integration
    async def test_concurrent_task_processing_simulation(self, orchestrator_with_mock_agents, sample_tasks):
        """Test simulation of concurrent task processing."""
        orchestrator = orchestrator_with_mock_agents
        
        # Add multiple tasks
        for task in sample_tasks:
            await orchestrator.add_task(task)
        
        # Simulate concurrent processing (sequential for testing)
        processing_tasks = []
        
        for _ in range(len(sample_tasks)):
            work_item = await orchestrator.get_next_priority()
            if work_item:
                # Create task for processing
                task_coro = orchestrator.execute_autonomously(work_item)
                processing_tasks.append(task_coro)
        
        # Wait for all to complete
        if processing_tasks:
            await asyncio.gather(*processing_tasks)
        
        # Verify all completed
        queue_status = await orchestrator.get_queue_status()
        assert queue_status["completed_tasks"] == len(sample_tasks)

    @pytest.mark.integration
    @pytest.mark.performance
    async def test_orchestrator_performance_under_load(self, orchestrator_with_mock_agents, performance_thresholds):
        """Test orchestrator performance under simulated load."""
        orchestrator = orchestrator_with_mock_agents
        
        # Create many tasks
        num_tasks = 100
        tasks = []
        for i in range(num_tasks):
            task = Task(
                id=f"load-test-{i}",
                type="code_generation",
                description=f"Load test task {i}",
                priority=i % 10,
                data={},
                created_at=datetime.now()
            )
            tasks.append(task)
        
        # Measure task addition time
        start_time = asyncio.get_event_loop().time()
        for task in tasks:
            await orchestrator.add_task(task)
        add_time = asyncio.get_event_loop().time() - start_time
        
        # Measure task processing time
        start_time = asyncio.get_event_loop().time()
        processed_count = 0
        
        while True:
            work_item = await orchestrator.get_next_priority()
            if work_item is None:
                break
            
            await orchestrator.execute_autonomously(work_item)
            processed_count += 1
        
        process_time = asyncio.get_event_loop().time() - start_time
        
        # Performance assertions
        avg_add_time = add_time / num_tasks
        avg_process_time = process_time / num_tasks
        
        assert avg_add_time < 0.01, f"Task addition too slow: {avg_add_time}s per task"
        assert avg_process_time < performance_thresholds["task_execution_max_time"], f"Task processing too slow: {avg_process_time}s per task"
        assert processed_count == num_tasks

    @pytest.mark.integration
    async def test_orchestrator_graceful_shutdown(self, orchestrator_with_mock_agents, sample_task):
        """Test orchestrator graceful shutdown."""
        orchestrator = orchestrator_with_mock_agents
        
        # Add a task
        await orchestrator.add_task(sample_task)
        
        # Verify shutdown completes without hanging
        shutdown_task = asyncio.create_task(orchestrator.shutdown())
        
        try:
            await asyncio.wait_for(shutdown_task, timeout=5.0)
        except asyncio.TimeoutError:
            pytest.fail("Orchestrator shutdown took too long")
        
        # Verify shutdown state
        assert orchestrator.running is False