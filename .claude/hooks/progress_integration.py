#!/usr/bin/env python3
"""
Progress Reporter Integration Module

Integrates the progress checkpoint system with the existing trigger system
for automated workflow management and enhanced coordination.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import sys

# Add .claude directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from state.trigger_manager import TriggerManager, Trigger, TriggerType, TriggerCondition, TriggerAction
    from hooks.progress_reporter import ProgressReporter, ProgressStatus, CheckpointType
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class ProgressWorkflowIntegration:
    """
    Integration layer between progress reporting and trigger system.
    
    Provides automated workflow triggers based on progress events
    and enhanced coordination between progress tracking and task automation.
    """
    
    def __init__(self, progress_reporter: ProgressReporter, trigger_manager: TriggerManager):
        """
        Initialize progress workflow integration.
        
        Args:
            progress_reporter: Progress reporter instance
            trigger_manager: Trigger manager instance
        """
        self.progress_reporter = progress_reporter
        self.trigger_manager = trigger_manager
        self.integration_active = False
        
        # Register action executors
        self._register_action_executors()
        
        # Set up default triggers
        self._setup_default_triggers()
        
        logger.info("Progress Workflow Integration initialized")
    
    def _register_action_executors(self) -> None:
        """Register action executors with trigger manager."""
        
        # Progress-related actions
        self.trigger_manager.register_action_executor("create_checkpoint", self._create_checkpoint_action)
        self.trigger_manager.register_action_executor("update_task_status", self._update_task_status_action)
        self.trigger_manager.register_action_executor("escalate_blocker", self._escalate_blocker_action)
        self.trigger_manager.register_action_executor("generate_report", self._generate_report_action)
        self.trigger_manager.register_action_executor("auto_commit", self._auto_commit_action)
        self.trigger_manager.register_action_executor("notify_milestone", self._notify_milestone_action)
        
        logger.info("Registered progress action executors")
    
    def _setup_default_triggers(self) -> None:
        """Set up default workflow triggers."""
        
        # Trigger 1: Create checkpoint on task completion
        self.trigger_manager.register_trigger(Trigger(
            trigger_id="task_completion_checkpoint",
            name="Task Completion Checkpoint",
            trigger_type=TriggerType.EVENT,
            conditions=[
                TriggerCondition(field="event_type", operator="==", value="task_completed")
            ],
            actions=[
                TriggerAction(
                    action_type="create_checkpoint",
                    target="system",
                    parameters={"type": "milestone", "description": "Task completed"}
                )
            ]
        ))
        
        # Trigger 2: Escalate long-running blockers
        self.trigger_manager.register_trigger(Trigger(
            trigger_id="blocker_escalation",
            name="Blocker Escalation",
            trigger_type=TriggerType.THRESHOLD,
            conditions=[
                TriggerCondition(field="blocked_duration_minutes", operator=">", value=15)
            ],
            actions=[
                TriggerAction(
                    action_type="escalate_blocker",
                    target="human",
                    parameters={"urgency": "high"}
                )
            ],
            cooldown_seconds=600  # 10 minute cooldown
        ))
        
        # Trigger 3: Auto-commit after significant progress
        self.trigger_manager.register_trigger(Trigger(
            trigger_id="progress_auto_commit",
            name="Progress Auto-Commit",
            trigger_type=TriggerType.THRESHOLD,
            conditions=[
                TriggerCondition(field="completion_percentage", operator=">=", value=25),
                TriggerCondition(field="git_uncommitted_changes", operator=">", value=5)
            ],
            actions=[
                TriggerAction(
                    action_type="auto_commit",
                    target="git",
                    parameters={"message_prefix": "progress: Checkpoint at"}
                )
            ],
            cooldown_seconds=900  # 15 minute cooldown
        ))
        
        # Trigger 4: Generate milestone report
        self.trigger_manager.register_trigger(Trigger(
            trigger_id="milestone_report",
            name="Milestone Report Generation",
            trigger_type=TriggerType.THRESHOLD,
            conditions=[
                TriggerCondition(field="completion_percentage", operator=">=", value=50)
            ],
            actions=[
                TriggerAction(
                    action_type="generate_report",
                    target="system",
                    parameters={"type": "milestone", "include_details": True}
                ),
                TriggerAction(
                    action_type="notify_milestone",
                    target="human",
                    parameters={"milestone": "50% completion"}
                )
            ],
            max_executions=1  # Only trigger once per session
        ))
        
        # Trigger 5: Quality gate validation
        self.trigger_manager.register_trigger(Trigger(
            trigger_id="quality_gate_check",
            name="Quality Gate Validation",
            trigger_type=TriggerType.THRESHOLD,
            conditions=[
                TriggerCondition(field="quality_metrics.git_hygiene_score", operator="<", value=70)
            ],
            actions=[
                TriggerAction(
                    action_type="create_checkpoint",
                    target="system",
                    parameters={"type": "error", "description": "Quality gate failure"}
                )
            ],
            cooldown_seconds=300  # 5 minute cooldown
        ))
        
        logger.info("Set up default workflow triggers")
    
    async def start_integration(self) -> None:
        """Start the integration monitoring."""
        if self.integration_active:
            logger.warning("Integration already active")
            return
        
        self.integration_active = True
        logger.info("Starting progress workflow integration")
        
        # Start monitoring loop
        asyncio.create_task(self._integration_loop())
    
    async def stop_integration(self) -> None:
        """Stop the integration monitoring."""
        self.integration_active = False
        logger.info("Stopped progress workflow integration")
    
    async def _integration_loop(self) -> None:
        """Main integration monitoring loop."""
        while self.integration_active:
            try:
                # Get current progress status
                progress_summary = self.progress_reporter.get_progress_summary()
                
                # Get latest checkpoint
                if self.progress_reporter.last_checkpoint:
                    checkpoint_data = {
                        "completion_percentage": progress_summary["completion_percentage"],
                        "overall_status": progress_summary["overall_status"],
                        "git_uncommitted_changes": self.progress_reporter.last_git_status.uncommitted_changes if self.progress_reporter.last_git_status else 0,
                        "session_duration_minutes": progress_summary["session_duration_minutes"],
                        "quality_metrics": self.progress_reporter.last_checkpoint.quality_metrics,
                        "blockers_count": len(self.progress_reporter.last_checkpoint.blockers)
                    }
                    
                    # Add blocked task duration
                    blocked_tasks = [task for task in self.progress_reporter.current_tasks.values() 
                                   if task.status == ProgressStatus.BLOCKED]
                    if blocked_tasks:
                        oldest_blocked = min(blocked_tasks, key=lambda t: t.last_update)
                        blocked_duration = (datetime.now() - oldest_blocked.last_update).total_seconds() / 60
                        checkpoint_data["blocked_duration_minutes"] = blocked_duration
                    
                    # Evaluate triggers
                    await self.trigger_manager.evaluate_triggers(checkpoint_data)
                
                # Wait before next evaluation
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in integration loop: {e}")
                await asyncio.sleep(30)
    
    async def _create_checkpoint_action(self, **params) -> None:
        """Action executor: Create checkpoint."""
        try:
            checkpoint_type = CheckpointType.MILESTONE
            if params.get("type") == "error":
                checkpoint_type = CheckpointType.ERROR
            elif params.get("type") == "manual":
                checkpoint_type = CheckpointType.MANUAL
            
            description = params.get("description", "Triggered checkpoint")
            
            checkpoint_id = await self.progress_reporter.create_checkpoint(checkpoint_type, description)
            logger.info(f"Trigger action created checkpoint: {checkpoint_id}")
            
        except Exception as e:
            logger.error(f"Error in create_checkpoint_action: {e}")
    
    async def _update_task_status_action(self, **params) -> None:
        """Action executor: Update task status."""
        try:
            task_id = params.get("target")
            status = params.get("status")
            
            if task_id and status:
                success = self.progress_reporter.update_task(task_id, status=ProgressStatus(status))
                logger.info(f"Trigger action updated task {task_id} status: {success}")
                
        except Exception as e:
            logger.error(f"Error in update_task_status_action: {e}")
    
    async def _escalate_blocker_action(self, **params) -> None:
        """Action executor: Escalate blocker to human attention."""
        try:
            urgency = params.get("urgency", "medium")
            
            # Create error checkpoint for human attention
            await self.progress_reporter.create_checkpoint(
                CheckpointType.ERROR,
                f"ESCALATION: Blocker requires human intervention (urgency: {urgency})"
            )
            
            logger.warning(f"ESCALATED: Blocker escalated to human with urgency {urgency}")
            
        except Exception as e:
            logger.error(f"Error in escalate_blocker_action: {e}")
    
    async def _generate_report_action(self, **params) -> None:
        """Action executor: Generate detailed report."""
        try:
            report_type = params.get("type", "standard")
            include_details = params.get("include_details", False)
            
            # This would trigger detailed report generation
            await self.progress_reporter._generate_progress_report()
            
            logger.info(f"Trigger action generated {report_type} report")
            
        except Exception as e:
            logger.error(f"Error in generate_report_action: {e}")
    
    async def _auto_commit_action(self, **params) -> None:
        """Action executor: Auto-commit git changes."""
        try:
            message_prefix = params.get("message_prefix", "auto:")
            
            if self.progress_reporter.last_git_status and not self.progress_reporter.last_git_status.repository_clean:
                # Create checkpoint before auto-commit
                await self.progress_reporter.create_checkpoint(
                    CheckpointType.GIT_CHANGE,
                    f"{message_prefix} {self.progress_reporter.get_progress_summary()['completion_percentage']}%"
                )
                
                logger.info(f"Trigger action: Auto-commit suggested (not executed for safety)")
                
        except Exception as e:
            logger.error(f"Error in auto_commit_action: {e}")
    
    async def _notify_milestone_action(self, **params) -> None:
        """Action executor: Notify milestone achievement."""
        try:
            milestone = params.get("milestone", "Unknown milestone")
            
            # Create milestone checkpoint
            await self.progress_reporter.create_checkpoint(
                CheckpointType.MILESTONE,
                f"MILESTONE ACHIEVED: {milestone}"
            )
            
            logger.info(f"MILESTONE: {milestone} achieved!")
            
        except Exception as e:
            logger.error(f"Error in notify_milestone_action: {e}")
    
    def trigger_task_completion(self, task_id: str) -> None:
        """Manually trigger task completion event."""
        try:
            context = {
                "event_type": "task_completed",
                "task_id": task_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # This would be called when a task is completed
            asyncio.create_task(self.trigger_manager.evaluate_triggers(context))
            
        except Exception as e:
            logger.error(f"Error triggering task completion: {e}")
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get integration status information."""
        return {
            "integration_active": self.integration_active,
            "triggers_registered": len(self.trigger_manager.triggers),
            "action_executors": len(self.trigger_manager.action_executors),
            "trigger_statistics": self.trigger_manager.get_statistics()
        }


# Factory function for easy initialization
def create_progress_integration() -> Optional[ProgressWorkflowIntegration]:
    """
    Factory function to create progress integration if dependencies are available.
    
    Returns:
        ProgressWorkflowIntegration instance or None if dependencies unavailable
    """
    if not IMPORTS_AVAILABLE:
        logger.warning("Progress integration dependencies not available")
        return None
    
    try:
        # Initialize components
        progress_reporter = ProgressReporter()
        trigger_manager = TriggerManager()
        
        # Create integration
        integration = ProgressWorkflowIntegration(progress_reporter, trigger_manager)
        
        logger.info("Progress integration created successfully")
        return integration
        
    except Exception as e:
        logger.error(f"Failed to create progress integration: {e}")
        return None


# Standalone test function
async def test_integration():
    """Test the progress integration system."""
    integration = create_progress_integration()
    if not integration:
        print("Integration dependencies not available")
        return
    
    print("Testing progress integration...")
    
    # Start integration
    await integration.start_integration()
    
    # Add some test tasks
    integration.progress_reporter.add_task("test_task_1", "Test task 1")
    integration.progress_reporter.add_task("test_task_2", "Test task 2")
    
    # Update progress
    integration.progress_reporter.update_task("test_task_1", progress_percentage=50)
    
    # Simulate task completion
    integration.progress_reporter.complete_task("test_task_2", quality_score=95)
    integration.trigger_task_completion("test_task_2")
    
    # Let it run for a bit
    await asyncio.sleep(5)
    
    # Show status
    status = integration.get_integration_status()
    print(f"Integration status: {status}")
    
    # Stop integration
    await integration.stop_integration()
    
    print("Integration test completed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_integration())