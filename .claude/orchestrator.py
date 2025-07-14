# .claude/orchestrator.py
#!/usr/bin/env python3
"""Streamlined orchestrator with maximum autonomy"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from state.state_manager import StateManager
from context.smart_context_manager import SmartContextManager
from learning.confidence_optimizer import ConfidenceOptimizer
from dashboard.unified_views import UnifiedDashboard
from xp.smart_xp import SmartXPEnforcer

# New imports for Phase 1
from queue.task_queue import TaskQueue, Task
from agents.base_agent import BaseAgent
from agents.claude_agent import ClaudeAgent
from config.config_loader import get_config
from utils.logging_config import get_logger, set_correlation_id, CorrelationContext

logger = get_logger('orchestrator')


class LeanVibeOrchestrator:
    def __init__(self):
        # Initialize logging
        set_correlation_id()
        logger.info("Initializing LeanVibe Orchestrator")
        
        # State management with ML integration
        self.state_manager = StateManager()
        
        # Legacy components (Phase 0) - TODO: Replace with StateManager equivalents
        self.monitor = SmartContextManager()
        self.confidence = ConfidenceOptimizer()
        self.dashboard = UnifiedDashboard()
        self.xp = SmartXPEnforcer()
        
        # New components (Phase 1)
        self.task_queue = TaskQueue()
        self.agents: Dict[str, BaseAgent] = {}
        self.running = False
        
        # Configuration
        self.config = get_config()
        
        # Note: Agent initialization is now async and done in run() method
        logger.info("LeanVibe Orchestrator initialized successfully")
    
    async def _initialize_agents(self):
        """Initialize available agents and register with StateManager."""
        try:
            # Initialize Claude agent
            claude_agent = ClaudeAgent("claude-primary")
            self.agents["claude-primary"] = claude_agent
            
            # Register agent with StateManager
            await self.state_manager.register_agent(
                "claude-primary", 
                capabilities=["code_generation", "analysis", "refactoring", "testing"]
            )
            
            logger.info("Claude agent initialized and registered with StateManager")
            
            # Future: Initialize other agents here
            
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            raise

    async def run(self):
        """Main loop optimized for autonomy"""
        logger.info("Starting orchestrator main loop")
        self.running = True
        
        # Initialize agents with StateManager
        await self._initialize_agents()
        
        # Start background monitors
        asyncio.create_task(self.monitor.monitor_and_prevent())
        asyncio.create_task(self.health_monitor())
        
        # Start agent health monitoring
        asyncio.create_task(self._monitor_agent_health())
        
        # Start StateManager checkpoint monitoring
        asyncio.create_task(self._monitor_checkpoints())

        while self.running:
            try:
                # Get next work item intelligently
                work_item = await self.get_next_priority()

                if not work_item:
                    await asyncio.sleep(5)  # Reduced sleep time for better responsiveness
                    continue

                # Check if we can handle autonomously using StateManager's ML components
                context = {
                    "task_type": work_item.metadata.get("type", "general"),
                    "priority": work_item.priority,
                    "agent_confidence": 0.8,  # Default confidence
                    "gemini_confidence": 0.8,  # Default confidence  
                    "complexity": work_item.metadata.get("complexity", "medium")
                }
                
                need_human, confidence = self.state_manager.confidence_tracker.should_involve_human(context)
                
                if not need_human:
                    await self.execute_autonomously(work_item)
                else:
                    await self.request_human_guidance(work_item)

                # Learn from execution
                outcome = await self.get_execution_outcome(work_item)
                decision_id = f"orchestrator_{work_item.task_id}"
                self.state_manager.confidence_tracker.record_outcome(
                    decision_id, context, need_human, outcome.get("status", "success")
                )

            except Exception as e:
                await self.smart_error_handling(e)
                await asyncio.sleep(1)  # Brief pause after error
        
        logger.info("Orchestrator main loop stopped")

    async def execute_autonomously_legacy(self, work_item):
        """Execute with minimal interruption - Legacy Phase 0 method"""

        # Legacy method - now handled by StateManager integration
        logger.info(f"Legacy execute_autonomously called for: {work_item}")
        
        # This method is deprecated - use StateManager-based implementation instead
        pass

    async def smart_error_handling(self, error):
        """Handle errors without always escalating using StateManager intelligence"""
        logger.warning(f"Handling error: {error}")
        
        # For now, just log and continue - TODO: Implement smart recovery
        await asyncio.sleep(1)
    
    async def request_human_guidance(self, work_item):
        """Request human guidance for complex tasks"""
        logger.info(f"Requesting human guidance for task: {work_item.task_id}")
        
        # Mark task as requiring human review
        await self.state_manager.update_task_state(
            work_item.task_id, 
            status="pending",
            metadata={**work_item.metadata, "requires_human_review": True}
        )
    
    async def get_execution_outcome(self, work_item):
        """Get execution outcome from StateManager"""
        # Get updated task state
        task_state = await self.state_manager.get_next_priority_task()
        
        if task_state and task_state.task_id == work_item.task_id:
            return {
                "status": task_state.status,
                "confidence": 0.8
            }
        
        return {"status": "success", "confidence": 0.8}
    
    async def health_monitor(self):
        """Monitor system health using StateManager"""
        while self.running:
            try:
                system_state = await self.state_manager.get_system_state()
                
                # Log system health metrics
                if system_state.active_agents == 0:
                    logger.warning("No active agents available")
                
                if system_state.average_context_usage > 0.8:
                    logger.warning(f"High average context usage: {system_state.average_context_usage:.1%}")
                
                await asyncio.sleep(120)  # Check every 2 minutes
                
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
                await asyncio.sleep(30)

    # Add placeholder methods for Phase 0
    # Phase 1 implementations - Core orchestrator methods
    async def get_next_priority(self):
        """Get next priority work item using StateManager"""
        # Check if any agent is available
        available_agents = []
        for agent_id, agent in self.agents.items():
            agent_state = await self.state_manager.get_agent_state(agent_id)
            if agent_state and agent_state.status == "idle":
                available_agents.append((agent_id, agent, agent_state))
        
        if not available_agents:
            return None
        
        # Get next task from StateManager
        for agent_id, agent, agent_state in available_agents:
            task_state = await self.state_manager.get_next_priority_task(agent_state.capabilities)
            if task_state:
                logger.debug(f"Task {task_state.task_id} assigned to agent {agent_id}")
                return task_state
        
        return None
    
    async def execute_autonomously(self, work_item):
        """Execute with minimal interruption using StateManager"""
        from state.state_manager import TaskState
        
        if not isinstance(work_item, TaskState):
            logger.error(f"Invalid work item type: {type(work_item)}")
            return
        
        with CorrelationContext():
            logger.info(f"Executing task autonomously: {work_item.task_id}")
            
            # Find suitable agent
            suitable_agent = None
            suitable_agent_id = None
            for agent_id, agent in self.agents.items():
                agent_state = await self.state_manager.get_agent_state(agent_id)
                if agent_state and agent_state.status == "idle":
                    # Check if agent can handle this task type
                    task_type = work_item.metadata.get("type", "general")
                    if task_type in agent_state.capabilities or "general" in agent_state.capabilities:
                        suitable_agent = agent
                        suitable_agent_id = agent_id
                        break
            
            if not suitable_agent:
                logger.error(f"No suitable agent found for task {work_item.task_id}")
                await self.state_manager.update_task_state(work_item.task_id, status="failed")
                return
            
            # Mark task as in progress and update agent state
            await self.state_manager.update_task_state(
                work_item.task_id, 
                status="in_progress", 
                agent_id=suitable_agent_id
            )
            await self.state_manager.update_agent_state(
                suitable_agent_id, 
                status="working",
                current_task_id=work_item.task_id
            )
            
            try:
                # Create Task object for backward compatibility
                task = Task(
                    id=work_item.task_id,
                    type=work_item.metadata.get("type", "general"),
                    description=work_item.metadata.get("description", ""),
                    priority=work_item.priority,
                    data=work_item.metadata.get("data", {}),
                    created_at=work_item.created_at
                )
                
                # Execute task
                result = await suitable_agent.execute_task(task)
                
                if result.status == "success":
                    await self.state_manager.update_task_state(work_item.task_id, status="completed")
                    await self.state_manager.update_agent_state(
                        suitable_agent_id, 
                        status="idle",
                        current_task_id=None
                    )
                    logger.info(f"Task {work_item.task_id} completed successfully")
                else:
                    await self.state_manager.update_task_state(work_item.task_id, status="failed")
                    await self.state_manager.update_agent_state(
                        suitable_agent_id, 
                        status="idle",
                        current_task_id=None
                    )
                    logger.warning(f"Task {work_item.task_id} failed: {result.error}")
                
            except Exception as e:
                logger.error(f"Error executing task {work_item.task_id}: {e}")
                await self.state_manager.update_task_state(work_item.task_id, status="failed")
                await self.state_manager.update_agent_state(
                    suitable_agent_id, 
                    status="idle",
                    current_task_id=None
                )
    
    async def _monitor_agent_health(self):
        """Monitor agent health periodically using StateManager"""
        while self.running:
            try:
                for agent_id, agent in self.agents.items():
                    is_healthy = await agent.health_check()
                    if not is_healthy:
                        logger.warning(f"Agent {agent_id} health check failed")
                        await self.state_manager.update_agent_state(agent_id, status="offline")
                    else:
                        # Update agent state with health information
                        agent_state = await self.state_manager.get_agent_state(agent_id)
                        if agent_state and agent_state.status == "offline":
                            await self.state_manager.update_agent_state(agent_id, status="idle")
                        
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in agent health monitoring: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_checkpoints(self):
        """Monitor and create checkpoints based on StateManager recommendations"""
        while self.running:
            try:
                # Check if we should create a checkpoint
                should_create, reason = await self.state_manager.should_create_checkpoint()
                
                if should_create:
                    checkpoint_id = await self.state_manager.create_checkpoint("auto")
                    if checkpoint_id:
                        logger.info(f"Automatic checkpoint created: {checkpoint_id} - {reason}")
                    else:
                        logger.warning(f"Failed to create checkpoint: {reason}")
                
                # Monitor individual agents for high context usage
                for agent_id in self.agents.keys():
                    agent_state = await self.state_manager.get_agent_state(agent_id)
                    if agent_state and agent_state.context_usage > 0.85:
                        should_create_agent, agent_reason = await self.state_manager.should_create_checkpoint(agent_id)
                        if should_create_agent:
                            checkpoint_id = await self.state_manager.create_checkpoint("context_overflow", agent_id)
                            if checkpoint_id:
                                logger.info(f"Agent checkpoint created: {checkpoint_id} - {agent_reason}")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in checkpoint monitoring: {e}")
                await asyncio.sleep(60)
    
    async def add_task(self, task: Task) -> bool:
        """Add a task to the StateManager.
        
        Args:
            task: Task to add
            
        Returns:
            True if task was added successfully
        """
        metadata = {
            "type": task.type,
            "description": task.description,
            "data": task.data,
            "created_at": task.created_at.isoformat()
        }
        
        return await self.state_manager.add_task(
            task_id=task.id,
            priority=task.priority,
            metadata=metadata
        )
    
    async def get_queue_status(self):
        """Get current system status from StateManager"""
        return await self.state_manager.get_system_state()
    
    async def shutdown(self):
        """Gracefully shutdown the orchestrator"""
        logger.info("Shutting down orchestrator...")
        self.running = False
        
        # Shutdown all agents
        for agent_id, agent in self.agents.items():
            try:
                await agent.shutdown()
                await self.state_manager.update_agent_state(agent_id, status="offline")
                logger.info(f"Agent {agent_id} shutdown complete")
            except Exception as e:
                logger.error(f"Error shutting down agent {agent_id}: {e}")
        
        # Shutdown StateManager
        await self.state_manager.shutdown()
        
        logger.info("Orchestrator shutdown complete")


def main():
    """Main entry point for the orchestrator"""
    # Initialize logging
    from utils.logging_config import setup_logging
    setup_logging()
    
    logger.info("Starting LeanVibe Orchestrator...")
    orchestrator = LeanVibeOrchestrator()
    
    # For Phase 1, show status and demonstrate functionality
    status = orchestrator.dashboard.render_status()
    logger.info(f"Orchestrator Status: {status}")
    
    # Example: Add a test task
    test_task = Task(
        id="test-001",
        type="code_generation",
        description="Generate a simple Python hello world function",
        priority=5,
        data={"prompt": "Create a simple Python function that prints 'Hello, World!'"},
        created_at=datetime.now()
    )
    
    async def run_example():
        await orchestrator.add_task(test_task)
        logger.info("Test task added to queue")
        
        # Run for a short time to demonstrate
        await asyncio.sleep(2)
        
        queue_status = await orchestrator.get_queue_status()
        logger.info(f"Queue status: {queue_status}")
        
        # Shutdown
        await orchestrator.shutdown()
    
    # Run the example
    asyncio.run(run_example())
    
    logger.info("Phase 1 demonstration complete!")
    return orchestrator


if __name__ == "__main__":
    main()
