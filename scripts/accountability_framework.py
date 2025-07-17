#!/usr/bin/env python3
"""
Automated Accountability Framework for Agent Coordination
Ensures mandatory completion deadlines, evidence tracking, and automated escalation.

XP METHODOLOGY COMPLIANCE:
- Small Releases: Tasks broken into 4-hour maximum chunks
- Continuous Integration: Automated git/test validation
- Test-Driven Development: Evidence requirements include test passing
- Simple Design: Clean, modular accountability system
- Collective Code Ownership: Automated reassignment on failures
- Sustainable Pace: 4-hour maximum work cycles with checkpoints
"""

import asyncio
import json
import logging
import subprocess
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path


logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task completion status levels."""
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    OVERDUE = "overdue"
    COMPLETED = "completed"
    REASSIGNED = "reassigned"
    ESCALATED = "escalated"


class EscalationLevel(Enum):
    """Escalation severity levels."""
    WARNING = "warning"
    CRITICAL = "critical"
    URGENT = "urgent"
    EMERGENCY = "emergency"


@dataclass
class TaskAssignment:
    """Task assignment with accountability tracking."""
    task_id: str
    agent_id: str
    task_description: str
    assigned_at: datetime
    deadline: datetime
    priority: str
    status: TaskStatus
    evidence_required: List[str]
    progress_checkpoints: List[datetime]
    evidence_collected: List[str] = None
    last_update: datetime = None
    escalation_level: EscalationLevel = EscalationLevel.WARNING
    reassignment_count: int = 0
    
    def __post_init__(self):
        if self.evidence_collected is None:
            self.evidence_collected = []
        if self.last_update is None:
            self.last_update = self.assigned_at


@dataclass
class EvidenceRequirement:
    """Required evidence for task completion."""
    type: str  # "git_commit", "file_modified", "test_passing", "pr_created"
    description: str
    validation_command: str
    required: bool = True


class AccountabilityFramework:
    """
    Automated accountability system for agent task management.
    
    Provides mandatory deadlines, evidence tracking, automated escalation,
    and task reassignment capabilities.
    """
    
    def __init__(self, config_path: str = ".claude/accountability_config.json"):
        """Initialize accountability framework."""
        self.config_path = Path(config_path)
        self.tasks: Dict[str, TaskAssignment] = {}
        self.evidence_types = self._load_evidence_types()
        self.config = self._load_config()
        self.monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None
        
        logger.info("AccountabilityFramework initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load accountability configuration."""
        default_config = {
            "default_deadline_hours": 4,
            "checkpoint_intervals": [0.25, 0.5, 0.75, 1.0],  # 25%, 50%, 75%, 100%
            "escalation_thresholds": {
                "warning": 0.75,  # 75% of deadline
                "critical": 0.9,  # 90% of deadline
                "urgent": 1.0,    # At deadline
                "emergency": 1.25  # 25% past deadline
            },
            "max_reassignments": 2,
            "evidence_validation_timeout": 30
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    default_config.update(config)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        
        return default_config
    
    def _load_evidence_types(self) -> Dict[str, EvidenceRequirement]:
        """Define evidence requirement types."""
        return {
            "git_commit": EvidenceRequirement(
                type="git_commit",
                description="Git commit with relevant changes",
                validation_command="git log --oneline -1",
                required=True
            ),
            "file_modified": EvidenceRequirement(
                type="file_modified",
                description="Modified files matching task scope",
                validation_command="git status --porcelain",
                required=True
            ),
            "tests_passing": EvidenceRequirement(
                type="tests_passing",
                description="All relevant tests passing",
                validation_command="python -m pytest tests/ -x --tb=short",
                required=True
            ),
            "pr_created": EvidenceRequirement(
                type="pr_created",
                description="Pull request created for review",
                validation_command="gh pr list --state open",
                required=False
            ),
            "quality_gates": EvidenceRequirement(
                type="quality_gates",
                description="Quality gates passed (lint, type check)",
                validation_command="python -m py_compile **/*.py",
                required=True
            )
        }
    
    async def assign_task(
        self,
        agent_id: str,
        task_description: str,
        deadline_hours: Optional[int] = None,
        priority: str = "medium",
        evidence_types: Optional[List[str]] = None
    ) -> str:
        """
        Assign task with mandatory accountability tracking.
        
        Args:
            agent_id: Target agent identifier
            task_description: Clear task description
            deadline_hours: Hours until deadline (default from config)
            priority: Task priority level
            evidence_types: Required evidence types
            
        Returns:
            Task ID for tracking
        """
        if deadline_hours is None:
            deadline_hours = self.config["default_deadline_hours"]
        
        if evidence_types is None:
            evidence_types = ["git_commit", "file_modified", "tests_passing"]
        
        task_id = f"task_{int(time.time())}_{agent_id}"
        assigned_at = datetime.now()
        deadline = assigned_at + timedelta(hours=deadline_hours)
        
        # Calculate progress checkpoints
        checkpoints = []
        for interval in self.config["checkpoint_intervals"]:
            checkpoint_time = assigned_at + timedelta(hours=deadline_hours * interval)
            checkpoints.append(checkpoint_time)
        
        task = TaskAssignment(
            task_id=task_id,
            agent_id=agent_id,
            task_description=task_description,
            assigned_at=assigned_at,
            deadline=deadline,
            priority=priority,
            status=TaskStatus.ASSIGNED,
            evidence_required=evidence_types,
            progress_checkpoints=checkpoints
        )
        
        self.tasks[task_id] = task
        
        # Start monitoring if not active
        if not self.monitoring_active:
            await self.start_monitoring()
        
        logger.info(f"Task {task_id} assigned to {agent_id}, deadline: {deadline}")
        return task_id
    
    async def update_task_progress(
        self,
        task_id: str,
        status: TaskStatus,
        evidence: Optional[List[str]] = None
    ) -> bool:
        """
        Update task progress with evidence.
        
        Args:
            task_id: Task identifier
            status: New task status
            evidence: Evidence of progress
            
        Returns:
            True if update successful
        """
        if task_id not in self.tasks:
            logger.error(f"Task {task_id} not found")
            return False
        
        task = self.tasks[task_id]
        task.status = status
        task.last_update = datetime.now()
        
        if evidence:
            task.evidence_collected.extend(evidence)
        
        # Validate evidence if task is completed
        if status == TaskStatus.COMPLETED:
            evidence_valid = await self._validate_evidence(task)
            if not evidence_valid:
                task.status = TaskStatus.BLOCKED
                logger.warning(f"Task {task_id} completion blocked: insufficient evidence")
                return False
        
        logger.info(f"Task {task_id} updated to {status.value}")
        return True
    
    async def _validate_evidence(self, task: TaskAssignment) -> bool:
        """
        Validate required evidence for task completion.
        
        Args:
            task: Task assignment to validate
            
        Returns:
            True if all required evidence provided
        """
        for evidence_type in task.evidence_required:
            if evidence_type not in self.evidence_types:
                continue
            
            requirement = self.evidence_types[evidence_type]
            if not requirement.required:
                continue
            
            try:
                # Run validation command safely without shell=True
                command_parts = requirement.validation_command.split()
                result = subprocess.run(
                    command_parts,
                    capture_output=True,
                    text=True,
                    timeout=self.config["evidence_validation_timeout"]
                )
                
                if result.returncode != 0:
                    logger.warning(f"Evidence validation failed for {evidence_type}: {result.stderr}")
                    return False
                
            except subprocess.TimeoutExpired:
                logger.error(f"Evidence validation timeout for {evidence_type}")
                return False
            except Exception as e:
                logger.error(f"Evidence validation error for {evidence_type}: {e}")
                return False
        
        return True
    
    async def start_monitoring(self) -> None:
        """Start automated monitoring and escalation."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Accountability monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop automated monitoring."""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Accountability monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for deadline and escalation tracking."""
        while self.monitoring_active:
            try:
                await self._check_deadlines()
                await self._check_checkpoints()
                await self._process_escalations()
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)
    
    async def _check_deadlines(self) -> None:
        """Check task deadlines and update escalation levels."""
        current_time = datetime.now()
        
        for task_id, task in self.tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.REASSIGNED]:
                continue
            
            # Calculate deadline progress
            total_time = (task.deadline - task.assigned_at).total_seconds()
            elapsed_time = (current_time - task.assigned_at).total_seconds()
            progress = elapsed_time / total_time if total_time > 0 else 1.0
            
            # Determine escalation level
            thresholds = self.config["escalation_thresholds"]
            if progress >= thresholds["emergency"]:
                new_level = EscalationLevel.EMERGENCY
                task.status = TaskStatus.OVERDUE
            elif progress >= thresholds["urgent"]:
                new_level = EscalationLevel.URGENT
            elif progress >= thresholds["critical"]:
                new_level = EscalationLevel.CRITICAL
            elif progress >= thresholds["warning"]:
                new_level = EscalationLevel.WARNING
            else:
                continue
            
            if new_level != task.escalation_level:
                task.escalation_level = new_level
                await self._escalate_task(task)
    
    async def _check_checkpoints(self) -> None:
        """Check progress checkpoints and request updates."""
        current_time = datetime.now()
        
        for task_id, task in self.tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.REASSIGNED]:
                continue
            
            # Check if any checkpoint has passed without update
            for checkpoint in task.progress_checkpoints:
                if (current_time >= checkpoint and 
                    task.last_update < checkpoint):
                    await self._request_progress_update(task)
                    break
    
    async def _escalate_task(self, task: TaskAssignment) -> None:
        """
        Escalate task based on escalation level.
        
        Args:
            task: Task to escalate
        """
        escalation_actions = {
            EscalationLevel.WARNING: self._warning_escalation,
            EscalationLevel.CRITICAL: self._critical_escalation,
            EscalationLevel.URGENT: self._urgent_escalation,
            EscalationLevel.EMERGENCY: self._emergency_escalation
        }
        
        action = escalation_actions.get(task.escalation_level)
        if action:
            await action(task)
    
    async def _warning_escalation(self, task: TaskAssignment) -> None:
        """Handle warning level escalation."""
        message = f"[WARNING] Task {task.task_id} approaching deadline - {task.task_description}"
        logger.warning(message)
        # Send notification to agent
    
    async def _critical_escalation(self, task: TaskAssignment) -> None:
        """Handle critical level escalation."""
        message = f"[CRITICAL] Task {task.task_id} critically overdue - Immediate attention required"
        logger.critical(message)
        # Send urgent notification to agent and PM
    
    async def _urgent_escalation(self, task: TaskAssignment) -> None:
        """Handle urgent level escalation."""
        message = f"[URGENT] Task {task.task_id} at deadline - Escalating to human intervention"
        logger.error(message)
        # Escalate to human coordination
    
    async def _emergency_escalation(self, task: TaskAssignment) -> None:
        """Handle emergency level escalation - task reassignment."""
        if task.reassignment_count >= self.config["max_reassignments"]:
            message = f"[EMERGENCY] Task {task.task_id} failed after {task.reassignment_count} reassignments"
            logger.critical(message)
            task.status = TaskStatus.ESCALATED
            return
        
        # Automatic task reassignment
        await self._reassign_task(task)
    
    async def _reassign_task(self, task: TaskAssignment) -> None:
        """
        Automatically reassign task to different agent.
        
        Args:
            task: Task to reassign
        """
        task.reassignment_count += 1
        task.status = TaskStatus.REASSIGNED
        old_agent = task.agent_id
        
        # Logic to select new agent (placeholder)
        new_agent = f"agent-backup-{task.reassignment_count}"
        
        # Create new task assignment
        new_task_id = await self.assign_task(
            agent_id=new_agent,
            task_description=f"[REASSIGNED] {task.task_description}",
            deadline_hours=self.config["default_deadline_hours"],
            priority=task.priority,
            evidence_types=task.evidence_required
        )
        
        logger.critical(
            f"Task {task.task_id} reassigned from {old_agent} to {new_agent} "
            f"as {new_task_id}"
        )
    
    async def _request_progress_update(self, task: TaskAssignment) -> None:
        """Request progress update from agent."""
        message = f"[CHECKPOINT] Progress update required for task {task.task_id}"
        logger.info(message)
        # Send progress request to agent
    
    async def _process_escalations(self) -> None:
        """Process any pending escalations."""
        # Additional escalation processing logic
        pass
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current task status and progress."""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        current_time = datetime.now()
        
        total_time = (task.deadline - task.assigned_at).total_seconds()
        elapsed_time = (current_time - task.assigned_at).total_seconds()
        progress = min(elapsed_time / total_time, 1.0) if total_time > 0 else 1.0
        
        return {
            "task_id": task.task_id,
            "agent_id": task.agent_id,
            "status": task.status.value,
            "escalation_level": task.escalation_level.value,
            "progress_percentage": round(progress * 100, 1),
            "deadline": task.deadline.isoformat(),
            "evidence_required": task.evidence_required,
            "evidence_collected": task.evidence_collected,
            "reassignment_count": task.reassignment_count
        }
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get status of all tasks."""
        return [self.get_task_status(task_id) for task_id in self.tasks.keys()]
    
    async def generate_accountability_report(self) -> Dict[str, Any]:
        """Generate comprehensive accountability report."""
        current_time = datetime.now()
        
        total_tasks = len(self.tasks)
        completed_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED])
        overdue_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.OVERDUE])
        reassigned_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.REASSIGNED])
        
        return {
            "generated_at": current_time.isoformat(),
            "summary": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "overdue_tasks": overdue_tasks,
                "reassigned_tasks": reassigned_tasks,
                "completion_rate": round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0
            },
            "tasks": self.get_all_tasks()
        }


# CLI Interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Accountability Framework CLI")
    parser.add_argument("--assign", help="Assign task to agent")
    parser.add_argument("--agent", help="Target agent ID")
    parser.add_argument("--deadline", type=int, help="Deadline in hours")
    parser.add_argument("--status", help="Get task status")
    parser.add_argument("--report", action="store_true", help="Generate accountability report")
    parser.add_argument("--monitor", action="store_true", help="Start monitoring")
    
    args = parser.parse_args()
    
    async def main():
        framework = AccountabilityFramework()
        
        if args.assign and args.agent:
            task_id = await framework.assign_task(
                agent_id=args.agent,
                task_description=args.assign,
                deadline_hours=args.deadline or 4
            )
            print(f"Task assigned: {task_id}")
        
        elif args.status:
            status = framework.get_task_status(args.status)
            if status:
                print(json.dumps(status, indent=2))
            else:
                print("Task not found")
        
        elif args.report:
            report = await framework.generate_accountability_report()
            print(json.dumps(report, indent=2))
        
        elif args.monitor:
            print("Starting accountability monitoring...")
            await framework.start_monitoring()
            try:
                while True:
                    await asyncio.sleep(60)
            except KeyboardInterrupt:
                await framework.stop_monitoring()
                print("Monitoring stopped")
    
    asyncio.run(main())