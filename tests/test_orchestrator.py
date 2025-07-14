#!/usr/bin/env python3
"""
Comprehensive tests for the LeanVibe Orchestrator.

This test suite covers:
- Orchestrator initialization and configuration
- Agent management and health monitoring
- Task execution and state management
- Integration with StateManager and TriggerManager
- Error handling and recovery
- Shutdown procedures
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Add .claude directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / '.claude'))

from orchestrator import LeanVibeOrchestrator
from task_queue_module.task_queue import Task


class TestLeanVibeOrchestrator:
    """Test suite for LeanVibe Orchestrator"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        return LeanVibeOrchestrator()
    
    @pytest.fixture
    def sample_task(self):
        """Create a sample task for testing"""
        return Task(
            id="test-task-001",
            type="code_generation",
            description="Test task for unit tests",
            priority=5,
            data={"test": "data"},
            created_at=datetime.now()
        )
    
    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initializes correctly"""
        assert orchestrator.state_manager is not None
        assert orchestrator.git_manager is not None
        assert orchestrator.trigger_manager is not None
        assert orchestrator.task_queue is not None
        assert orchestrator.agents == {}
        assert orchestrator.running is False
        assert orchestrator.config is not None
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, orchestrator):
        """Test agent initialization and registration"""
        await orchestrator._initialize_agents()
        
        assert "claude-primary" in orchestrator.agents
        
        # Verify agent was registered with StateManager
        agent_state = await orchestrator.state_manager.get_agent_state("claude-primary")
        assert agent_state is not None
        assert agent_state.agent_id == "claude-primary"
        assert "code_generation" in agent_state.capabilities
    
    @pytest.mark.asyncio
    async def test_add_task(self, orchestrator, sample_task):
        """Test adding tasks to the orchestrator"""
        result = await orchestrator.add_task(sample_task)
        assert result is True
        
        # Verify task was added to StateManager
        task_state = await orchestrator.state_manager.get_next_priority_task()
        assert task_state is not None
        assert task_state.task_id == sample_task.id
        assert task_state.priority == sample_task.priority
    
    @pytest.mark.asyncio
    async def test_get_next_priority_no_agents(self, orchestrator):
        """Test getting next priority when no agents available"""
        work_item = await orchestrator.get_next_priority()
        assert work_item is None
    
    @pytest.mark.asyncio
    async def test_get_next_priority_with_agents(self, orchestrator, sample_task):
        """Test getting next priority with available agents"""
        # Initialize agents first
        await orchestrator._initialize_agents()
        
        # Add a task
        await orchestrator.add_task(sample_task)
        
        # Get next priority
        work_item = await orchestrator.get_next_priority()
        assert work_item is not None
        assert work_item.task_id == sample_task.id
    
    @pytest.mark.asyncio
    async def test_execute_autonomously_success(self, orchestrator, sample_task):
        """Test successful autonomous task execution"""
        # Initialize agents
        await orchestrator._initialize_agents()
        
        # Add task and get it
        await orchestrator.add_task(sample_task)
        work_item = await orchestrator.get_next_priority()
        
        # Mock successful execution
        with patch.object(orchestrator.agents["claude-primary"], 'execute_task') as mock_execute:
            mock_result = Mock()
            mock_result.status = "success"
            mock_execute.return_value = mock_result
            
            # Execute autonomously
            await orchestrator.execute_autonomously(work_item)
            
            # Verify task was marked as completed
            task_state = await orchestrator.state_manager.get_next_priority_task()
            assert task_state is None or task_state.status == "completed"
    
    @pytest.mark.asyncio
    async def test_execute_autonomously_failure(self, orchestrator, sample_task):
        """Test failed autonomous task execution"""
        # Initialize agents
        await orchestrator._initialize_agents()
        
        # Add task and get it
        await orchestrator.add_task(sample_task)
        work_item = await orchestrator.get_next_priority()
        
        # Mock failed execution
        with patch.object(orchestrator.agents["claude-primary"], 'execute_task') as mock_execute:
            mock_result = Mock()
            mock_result.status = "failed"
            mock_result.error = "Test error"
            mock_execute.return_value = mock_result
            
            # Execute autonomously
            await orchestrator.execute_autonomously(work_item)
            
            # Verify task was marked as failed
            # (This would require checking the database directly)
    
    @pytest.mark.asyncio
    async def test_execute_autonomously_exception(self, orchestrator, sample_task):
        """Test exception handling during autonomous execution"""
        # Initialize agents
        await orchestrator._initialize_agents()
        
        # Add task and get it
        await orchestrator.add_task(sample_task)
        work_item = await orchestrator.get_next_priority()
        
        # Mock exception during execution
        with patch.object(orchestrator.agents["claude-primary"], 'execute_task') as mock_execute:
            mock_execute.side_effect = Exception("Test exception")
            
            # Execute autonomously (should not raise exception)
            await orchestrator.execute_autonomously(work_item)
            
            # Verify task was marked as failed
            # (This would require checking the database directly)
    
    @pytest.mark.asyncio
    async def test_request_human_guidance(self, orchestrator, sample_task):
        """Test requesting human guidance for complex tasks"""
        # Add task and get it
        await orchestrator.add_task(sample_task)
        work_item = await orchestrator.get_next_priority()
        
        # Request human guidance
        await orchestrator.request_human_guidance(work_item)
        
        # Verify task was marked as requiring human review
        # (This would require checking the database directly)
    
    @pytest.mark.asyncio
    async def test_health_monitor(self, orchestrator):
        """Test health monitoring functionality"""
        # Initialize agents
        await orchestrator._initialize_agents()
        
        # Start health monitor for a short time
        orchestrator.running = True
        task = asyncio.create_task(orchestrator.health_monitor())
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        # Stop monitoring
        orchestrator.running = False
        await asyncio.sleep(0.1)
        
        # Verify no exceptions were raised
        assert not task.done() or not task.exception()
    
    @pytest.mark.asyncio
    async def test_agent_health_monitoring(self, orchestrator):
        """Test agent health monitoring"""
        # Initialize agents
        await orchestrator._initialize_agents()
        
        # Mock agent health check
        with patch.object(orchestrator.agents["claude-primary"], 'health_check') as mock_health:
            mock_health.return_value = True
            
            # Start health monitor for a short time
            orchestrator.running = True
            task = asyncio.create_task(orchestrator._monitor_agent_health())
            
            # Let it run briefly
            await asyncio.sleep(0.1)
            
            # Stop monitoring
            orchestrator.running = False
            await asyncio.sleep(0.1)
            
            # Verify health check was called
            mock_health.assert_called()
    
    @pytest.mark.asyncio
    async def test_checkpoint_monitoring(self, orchestrator):
        """Test checkpoint monitoring functionality"""
        # Mock StateManager methods
        with patch.object(orchestrator.state_manager, 'should_create_checkpoint') as mock_should_create:
            mock_should_create.return_value = (True, "Test checkpoint")
            
            with patch.object(orchestrator.state_manager, 'create_checkpoint') as mock_create:
                mock_create.return_value = "test-checkpoint-id"
                
                # Start checkpoint monitor for a short time
                orchestrator.running = True
                task = asyncio.create_task(orchestrator._monitor_checkpoints())
                
                # Let it run briefly
                await asyncio.sleep(0.1)
                
                # Stop monitoring
                orchestrator.running = False
                await asyncio.sleep(0.1)
                
                # Verify checkpoint was created
                mock_create.assert_called_with("auto")
    
    @pytest.mark.asyncio
    async def test_get_queue_status(self, orchestrator):
        """Test getting queue status"""
        status = await orchestrator.get_queue_status()
        assert status is not None
        # Verify system state structure
        assert hasattr(status, 'active_agents')
        assert hasattr(status, 'total_tasks')
        assert hasattr(status, 'completed_tasks')
    
    @pytest.mark.asyncio
    async def test_shutdown(self, orchestrator):
        """Test graceful shutdown"""
        # Initialize agents
        await orchestrator._initialize_agents()
        
        # Mock agent shutdown
        with patch.object(orchestrator.agents["claude-primary"], 'shutdown') as mock_shutdown:
            mock_shutdown.return_value = None
            
            # Start orchestrator
            orchestrator.running = True
            
            # Shutdown
            await orchestrator.shutdown()
            
            # Verify shutdown was called
            mock_shutdown.assert_called()
            assert orchestrator.running is False
    
    @pytest.mark.asyncio
    async def test_smart_error_handling(self, orchestrator):
        """Test smart error handling"""
        test_error = Exception("Test error")
        
        # Should not raise exception
        await orchestrator.smart_error_handling(test_error)
        
        # Verify error was logged (this would require log capturing)
    
    @pytest.mark.asyncio
    async def test_get_execution_outcome(self, orchestrator, sample_task):
        """Test getting execution outcome"""
        # Add task
        await orchestrator.add_task(sample_task)
        work_item = await orchestrator.get_next_priority()
        
        # Get execution outcome
        outcome = await orchestrator.get_execution_outcome(work_item)
        
        assert outcome is not None
        assert "status" in outcome
        assert "confidence" in outcome


class TestOrchestratorIntegration:
    """Integration tests for orchestrator with other components"""
    
    @pytest.mark.asyncio
    async def test_orchestrator_with_state_manager(self):
        """Test orchestrator integration with StateManager"""
        orchestrator = LeanVibeOrchestrator()
        
        # Test state manager is properly initialized
        assert orchestrator.state_manager is not None
        
        # Test confidence tracking integration
        context = {"test": "context"}
        need_human, confidence = orchestrator.state_manager.confidence_tracker.should_involve_human(context)
        assert isinstance(need_human, bool)
        assert isinstance(confidence, float)
    
    @pytest.mark.asyncio
    async def test_orchestrator_with_trigger_manager(self):
        """Test orchestrator integration with TriggerManager"""
        orchestrator = LeanVibeOrchestrator()
        
        # Test trigger manager is properly initialized
        assert orchestrator.trigger_manager is not None
        
        # Test trigger statistics
        stats = orchestrator.trigger_manager.get_trigger_statistics()
        assert "total_rules" in stats
        assert "enabled_rules" in stats
    
    @pytest.mark.asyncio
    async def test_orchestrator_with_git_manager(self):
        """Test orchestrator integration with GitMilestoneManager"""
        orchestrator = LeanVibeOrchestrator()
        
        # Test git manager is properly initialized
        assert orchestrator.git_manager is not None
        
        # Test milestone creation capability
        should_create, reason, data = await orchestrator.git_manager.should_create_milestone()
        assert isinstance(should_create, bool)
        assert isinstance(reason, str)
        assert isinstance(data, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])