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

from state.intelligent_state import IntelligentStateManager
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
        
        # Legacy components (Phase 0)
        self.state = IntelligentStateManager()
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
        
        # Initialize agents
        self._initialize_agents()
        
        logger.info("LeanVibe Orchestrator initialized successfully")
    
    def _initialize_agents(self):
        """Initialize available agents."""
        try:
            # Initialize Claude agent
            claude_agent = ClaudeAgent("claude-primary")
            self.agents["claude-primary"] = claude_agent
            logger.info("Claude agent initialized")
            
            # Future: Initialize other agents here
            
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            raise

    async def run(self):
        """Main loop optimized for autonomy"""
        logger.info("Starting orchestrator main loop")
        self.running = True
        
        # Start background monitors
        asyncio.create_task(self.monitor.monitor_and_prevent())
        asyncio.create_task(self.health_monitor())
        
        # Start agent health monitoring
        asyncio.create_task(self._monitor_agent_health())

        while self.running:
            try:
                # Get next work item intelligently
                work_item = await self.get_next_priority()

                if not work_item:
                    await asyncio.sleep(5)  # Reduced sleep time for better responsiveness
                    continue

                # Check if we can handle autonomously
                if self.confidence.can_handle_autonomously(work_item):
                    await self.execute_autonomously(work_item)
                else:
                    await self.request_human_guidance(work_item)

                # Learn from execution
                outcome = await self.get_execution_outcome(work_item)
                self.confidence.learn_from_outcome(work_item, outcome)

            except Exception as e:
                await self.smart_error_handling(e)
                await asyncio.sleep(1)  # Brief pause after error
        
        logger.info("Orchestrator main loop stopped")

    async def execute_autonomously(self, work_item):
        """Execute with minimal interruption"""

        # Plan with Gemini
        plan = await self.plan_with_gemini(work_item)

        # Distribute smartly
        distribution = self.smart_distribute(plan)

        # Execute in parallel
        tasks = [
            self.execute_on_agent(agent, tasks) for agent, tasks in distribution.items()
        ]

        # Monitor without blocking
        asyncio.create_task(self.monitor_execution(tasks))

    async def smart_error_handling(self, error):
        """Handle errors without always escalating"""

        # Check if we've seen this before
        if solution := self.find_previous_solution(error):
            await self.apply_solution(solution)
            return

        # Try automatic recovery
        if await self.attempt_auto_recovery(error):
            return

        # Only escalate if truly necessary
        await self.escalate_with_context(error)

    # Add placeholder methods for Phase 0
    async def health_monitor(self):
        """Health monitoring - Phase 0 placeholder"""
        print("Health monitoring started...")
        
    async def execute_autonomously(self, work_item):
        """Execute with minimal interruption - Phase 0 placeholder"""
        print(f"Executing autonomously: {work_item}")
        
    async def request_human_guidance(self, work_item):
        """Request human guidance - Phase 0 placeholder"""
        print(f"Requesting human guidance for: {work_item}")
        
    async def plan_with_gemini(self, work_item):
        """Plan with Gemini - Phase 0 placeholder"""
        print(f"Planning with Gemini: {work_item}")
        return {"plan": "placeholder"}
        
    def smart_distribute(self, plan):
        """Smart distribution - Phase 0 placeholder"""
        print(f"Smart distributing: {plan}")
        return {"agent1": ["task1"]}
        
    async def execute_on_agent(self, agent, tasks):
        """Execute on agent - Phase 0 placeholder"""
        print(f"Executing on {agent}: {tasks}")
        
    async def monitor_execution(self, tasks):
        """Monitor execution - Phase 0 placeholder"""
        print(f"Monitoring execution: {tasks}")
        
    def find_previous_solution(self, error):
        """Find previous solution - Phase 0 placeholder"""
        print(f"Finding previous solution for: {error}")
        return None
        
    async def apply_solution(self, solution):
        """Apply solution - Phase 0 placeholder"""
        print(f"Applying solution: {solution}")
        
    async def attempt_auto_recovery(self, error):
        """Attempt auto recovery - Phase 0 placeholder"""
        print(f"Attempting auto recovery for: {error}")
        return False
        
    async def escalate_with_context(self, error):
        """Escalate with context - Phase 0 placeholder"""
        print(f"Escalating with context: {error}")
    
    # Phase 1 implementations
    async def get_next_priority(self):
        """Get next priority work item from task queue"""
        # Check if any agent is available
        available_agents = []
        for agent_id, agent in self.agents.items():
            status = await agent.get_status()
            if status.status.value == "idle":
                available_agents.append((agent_id, agent))
        
        if not available_agents:
            return None
        
        # Get next task for available agents
        for agent_id, agent in available_agents:
            task = await self.task_queue.get_next_task(agent.get_capabilities())
            if task:
                logger.debug(f"Task {task.id} assigned to agent {agent_id}")
                return task
        
        return None
    
    async def execute_autonomously(self, work_item):
        """Execute with minimal interruption - Phase 1 implementation"""
        if not isinstance(work_item, Task):
            logger.error(f"Invalid work item type: {type(work_item)}")
            return
        
        with CorrelationContext():
            logger.info(f"Executing task autonomously: {work_item.id}")
            
            # Find suitable agent
            suitable_agent = None
            for agent_id, agent in self.agents.items():
                if agent.can_handle_task(work_item):
                    status = await agent.get_status()
                    if status.status.value == "idle":
                        suitable_agent = agent
                        break
            
            if not suitable_agent:
                logger.error(f"No suitable agent found for task {work_item.id}")
                await self.task_queue.mark_task_failed(work_item.id, can_retry=True)
                return
            
            # Mark task as in progress
            await self.task_queue.mark_task_in_progress(work_item.id, suitable_agent.agent_id)
            
            try:
                # Execute task
                result = await suitable_agent.execute_task(work_item)
                
                if result.status == "success":
                    await self.task_queue.mark_task_completed(work_item.id)
                    logger.info(f"Task {work_item.id} completed successfully")
                else:
                    await self.task_queue.mark_task_failed(work_item.id, can_retry=True)
                    logger.warning(f"Task {work_item.id} failed: {result.error}")
                
            except Exception as e:
                logger.error(f"Error executing task {work_item.id}: {e}")
                await self.task_queue.mark_task_failed(work_item.id, can_retry=True)
    
    async def _monitor_agent_health(self):
        """Monitor agent health periodically"""
        while self.running:
            try:
                for agent_id, agent in self.agents.items():
                    is_healthy = await agent.health_check()
                    if not is_healthy:
                        logger.warning(f"Agent {agent_id} health check failed")
                        
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in agent health monitoring: {e}")
                await asyncio.sleep(10)
    
    async def add_task(self, task: Task) -> bool:
        """Add a task to the queue.
        
        Args:
            task: Task to add
            
        Returns:
            True if task was added successfully
        """
        return await self.task_queue.add_task(task)
    
    async def get_queue_status(self):
        """Get current queue status"""
        return await self.task_queue.get_queue_status()
    
    async def shutdown(self):
        """Gracefully shutdown the orchestrator"""
        logger.info("Shutting down orchestrator...")
        self.running = False
        
        # Shutdown all agents
        for agent_id, agent in self.agents.items():
            try:
                await agent.shutdown()
                logger.info(f"Agent {agent_id} shutdown complete")
            except Exception as e:
                logger.error(f"Error shutting down agent {agent_id}: {e}")
        
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
