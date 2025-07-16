#!/usr/bin/env python3
"""
Progress Checkpoint System - Phase 1.2 Workflow Improvement

Automated 5-minute status reporting with git monitoring and structured progress tracking.
Provides comprehensive workflow visibility and checkpoint management.
"""

import asyncio
import json
import logging
import os
import subprocess
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import sys

# Add .claude directory to path for internal imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from state.state_manager import StateManager, AgentState, TaskState
    STATE_MANAGER_AVAILABLE = True
except ImportError:
    STATE_MANAGER_AVAILABLE = False

logger = logging.getLogger(__name__)


class ProgressStatus(Enum):
    """Progress status levels."""
    ON_TRACK = "on_track"
    DELAYED = "delayed"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class CheckpointType(Enum):
    """Types of progress checkpoints."""
    SCHEDULED = "scheduled"
    MILESTONE = "milestone"
    ERROR = "error"
    MANUAL = "manual"
    GIT_CHANGE = "git_change"


@dataclass
class GitStatus:
    """Git repository status information."""
    branch: str
    commit_hash: str
    commit_message: str
    uncommitted_changes: int
    untracked_files: int
    staged_changes: int
    ahead_behind: Dict[str, int]
    last_commit_time: datetime
    repository_clean: bool


@dataclass
class TaskProgress:
    """Individual task progress tracking."""
    task_id: str
    description: str
    status: ProgressStatus
    progress_percentage: float
    estimated_completion: Optional[datetime]
    blockers: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    last_update: datetime = field(default_factory=datetime.now)
    time_spent: float = 0.0  # minutes
    quality_score: float = 0.0


@dataclass
class ProgressCheckpoint:
    """Progress checkpoint data structure."""
    checkpoint_id: str
    timestamp: datetime
    checkpoint_type: CheckpointType
    git_status: GitStatus
    tasks: List[TaskProgress]
    overall_status: ProgressStatus
    completion_percentage: float
    estimated_completion: Optional[datetime]
    blockers: List[str]
    achievements: List[str]
    next_actions: List[str]
    quality_metrics: Dict[str, float]
    session_duration: float  # minutes
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProgressReporter:
    """
    Automated progress checkpoint system with 5-minute reporting.
    
    Features:
    - Automated 5-minute status reports
    - Git status monitoring and change detection
    - Structured progress tracking
    - Checkpoint creation and validation
    - Integration with trigger system
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize progress reporter.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root or Path.cwd()
        self.checkpoints_dir = self.project_root / ".claude" / "checkpoints"
        self.reports_dir = self.project_root / ".claude" / "reports"
        
        # Create directories
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # State tracking
        self.current_tasks: Dict[str, TaskProgress] = {}
        self.last_git_status: Optional[GitStatus] = None
        self.last_checkpoint: Optional[ProgressCheckpoint] = None
        self.session_start: datetime = datetime.now()
        self.reporting_active = False
        self.report_interval = 300  # 5 minutes in seconds
        
        # State manager integration
        self.state_manager: Optional[StateManager] = None
        if STATE_MANAGER_AVAILABLE:
            try:
                self.state_manager = StateManager()
            except Exception as e:
                logger.warning(f"State manager initialization failed: {e}")
        
        # Statistics
        self.stats = {
            "checkpoints_created": 0,
            "reports_generated": 0,
            "git_changes_detected": 0,
            "tasks_tracked": 0,
            "uptime_minutes": 0
        }
        
        logger.info("Progress Reporter initialized")
    
    async def start_monitoring(self) -> None:
        """Start automated progress monitoring."""
        if self.reporting_active:
            logger.warning("Progress monitoring already active")
            return
        
        self.reporting_active = True
        logger.info(f"Starting progress monitoring with {self.report_interval}s intervals")
        
        # Create initial checkpoint
        await self.create_checkpoint(CheckpointType.SCHEDULED, "Session started")
        
        # Start monitoring loop
        asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self) -> None:
        """Stop automated progress monitoring."""
        if not self.reporting_active:
            return
        
        self.reporting_active = False
        
        # Create final checkpoint
        await self.create_checkpoint(CheckpointType.SCHEDULED, "Session ended")
        
        logger.info("Progress monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for periodic reporting."""
        while self.reporting_active:
            try:
                # Update uptime
                self.stats["uptime_minutes"] = (datetime.now() - self.session_start).total_seconds() / 60
                
                # Check for git changes
                await self._check_git_changes()
                
                # Create scheduled checkpoint
                await self.create_checkpoint(CheckpointType.SCHEDULED)
                
                # Generate progress report
                await self._generate_progress_report()
                
                # Wait for next interval
                await asyncio.sleep(self.report_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying
    
    async def _check_git_changes(self) -> None:
        """Check for git repository changes."""
        try:
            current_git_status = await self._get_git_status()
            
            if self.last_git_status:
                # Detect changes
                if (current_git_status.commit_hash != self.last_git_status.commit_hash or
                    current_git_status.uncommitted_changes != self.last_git_status.uncommitted_changes or
                    current_git_status.staged_changes != self.last_git_status.staged_changes):
                    
                    self.stats["git_changes_detected"] += 1
                    await self.create_checkpoint(CheckpointType.GIT_CHANGE, "Git changes detected")
            
            self.last_git_status = current_git_status
            
        except Exception as e:
            logger.error(f"Error checking git changes: {e}")
    
    async def _get_git_status(self) -> GitStatus:
        """Get current git repository status."""
        try:
            # Get current branch
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
            
            # Get commit hash and message
            commit_result = subprocess.run(
                ["git", "log", "-1", "--format=%H|%s|%ct"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if commit_result.returncode == 0:
                parts = commit_result.stdout.strip().split('|')
                commit_hash = parts[0][:8]  # Short hash
                commit_message = parts[1] if len(parts) > 1 else ""
                commit_time = datetime.fromtimestamp(int(parts[2])) if len(parts) > 2 else datetime.now()
            else:
                commit_hash = "unknown"
                commit_message = ""
                commit_time = datetime.now()
            
            # Get status
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            status_lines = status_result.stdout.strip().split('\n') if status_result.stdout.strip() else []
            
            uncommitted_changes = len([line for line in status_lines if line.startswith(' M') or line.startswith(' D')])
            staged_changes = len([line for line in status_lines if line.startswith('M') or line.startswith('A') or line.startswith('D')])
            untracked_files = len([line for line in status_lines if line.startswith('??')])
            
            # Get ahead/behind info
            ahead_behind = {"ahead": 0, "behind": 0}
            try:
                ahead_behind_result = subprocess.run(
                    ["git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True
                )
                if ahead_behind_result.returncode == 0:
                    parts = ahead_behind_result.stdout.strip().split()
                    if len(parts) == 2:
                        ahead_behind = {"ahead": int(parts[0]), "behind": int(parts[1])}
            except:
                pass
            
            repository_clean = uncommitted_changes == 0 and staged_changes == 0 and untracked_files == 0
            
            return GitStatus(
                branch=branch,
                commit_hash=commit_hash,
                commit_message=commit_message,
                uncommitted_changes=uncommitted_changes,
                untracked_files=untracked_files,
                staged_changes=staged_changes,
                ahead_behind=ahead_behind,
                last_commit_time=commit_time,
                repository_clean=repository_clean
            )
            
        except Exception as e:
            logger.error(f"Error getting git status: {e}")
            # Return minimal status
            return GitStatus(
                branch="unknown",
                commit_hash="unknown",
                commit_message="",
                uncommitted_changes=0,
                untracked_files=0,
                staged_changes=0,
                ahead_behind={"ahead": 0, "behind": 0},
                last_commit_time=datetime.now(),
                repository_clean=True
            )
    
    async def create_checkpoint(self, checkpoint_type: CheckpointType, description: str = "") -> str:
        """
        Create a progress checkpoint.
        
        Args:
            checkpoint_type: Type of checkpoint
            description: Optional description
            
        Returns:
            Checkpoint ID
        """
        try:
            checkpoint_id = f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Get current git status
            git_status = await self._get_git_status()
            
            # Calculate overall progress
            overall_status, completion_percentage = self._calculate_overall_progress()
            
            # Get blockers and achievements
            blockers = self._get_current_blockers()
            achievements = self._get_recent_achievements()
            next_actions = self._get_next_actions()
            
            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics()
            
            # Create checkpoint
            checkpoint = ProgressCheckpoint(
                checkpoint_id=checkpoint_id,
                timestamp=datetime.now(),
                checkpoint_type=checkpoint_type,
                git_status=git_status,
                tasks=list(self.current_tasks.values()),
                overall_status=overall_status,
                completion_percentage=completion_percentage,
                estimated_completion=self._estimate_completion(),
                blockers=blockers,
                achievements=achievements,
                next_actions=next_actions,
                quality_metrics=quality_metrics,
                session_duration=(datetime.now() - self.session_start).total_seconds() / 60,
                metadata={"description": description}
            )
            
            # Save checkpoint
            checkpoint_file = self.checkpoints_dir / f"{checkpoint_id}.json"
            with open(checkpoint_file, 'w') as f:
                json.dump(asdict(checkpoint), f, indent=2, default=str)
            
            self.last_checkpoint = checkpoint
            self.stats["checkpoints_created"] += 1
            
            logger.info(f"Created checkpoint: {checkpoint_id} ({checkpoint_type.value})")
            return checkpoint_id
            
        except Exception as e:
            logger.error(f"Error creating checkpoint: {e}")
            return ""
    
    def _calculate_overall_progress(self) -> tuple[ProgressStatus, float]:
        """Calculate overall progress status and percentage."""
        if not self.current_tasks:
            return ProgressStatus.ON_TRACK, 0.0
        
        total_progress = sum(task.progress_percentage for task in self.current_tasks.values())
        completion_percentage = total_progress / len(self.current_tasks)
        
        # Determine overall status
        failed_tasks = [task for task in self.current_tasks.values() if task.status == ProgressStatus.FAILED]
        blocked_tasks = [task for task in self.current_tasks.values() if task.status == ProgressStatus.BLOCKED]
        completed_tasks = [task for task in self.current_tasks.values() if task.status == ProgressStatus.COMPLETED]
        
        if failed_tasks:
            overall_status = ProgressStatus.FAILED
        elif blocked_tasks:
            overall_status = ProgressStatus.BLOCKED
        elif len(completed_tasks) == len(self.current_tasks):
            overall_status = ProgressStatus.COMPLETED
        elif completion_percentage < 50:
            overall_status = ProgressStatus.DELAYED
        else:
            overall_status = ProgressStatus.ON_TRACK
        
        return overall_status, completion_percentage
    
    def _get_current_blockers(self) -> List[str]:
        """Get current blockers across all tasks."""
        blockers = []
        for task in self.current_tasks.values():
            blockers.extend(task.blockers)
        return list(set(blockers))  # Remove duplicates
    
    def _get_recent_achievements(self) -> List[str]:
        """Get recent achievements."""
        achievements = []
        cutoff = datetime.now() - timedelta(minutes=self.report_interval / 60)
        
        for task in self.current_tasks.values():
            if task.status == ProgressStatus.COMPLETED and task.last_update > cutoff:
                achievements.append(f"Completed: {task.description}")
            elif task.progress_percentage > 80 and task.last_update > cutoff:
                achievements.append(f"Near completion: {task.description}")
        
        return achievements
    
    def _get_next_actions(self) -> List[str]:
        """Get suggested next actions."""
        next_actions = []
        
        # Priority tasks
        priority_tasks = sorted(
            [task for task in self.current_tasks.values() if task.status not in [ProgressStatus.COMPLETED, ProgressStatus.FAILED]],
            key=lambda t: t.progress_percentage
        )
        
        if priority_tasks:
            next_actions.append(f"Continue work on: {priority_tasks[0].description}")
        
        # Blocked tasks
        blocked_tasks = [task for task in self.current_tasks.values() if task.status == ProgressStatus.BLOCKED]
        if blocked_tasks:
            next_actions.append(f"Resolve blockers for: {blocked_tasks[0].description}")
        
        # Git status
        if self.last_git_status and not self.last_git_status.repository_clean:
            next_actions.append("Consider committing git changes")
        
        return next_actions
    
    def _calculate_quality_metrics(self) -> Dict[str, float]:
        """Calculate quality metrics."""
        metrics = {
            "task_completion_rate": 0.0,
            "average_task_quality": 0.0,
            "git_hygiene_score": 0.0,
            "productivity_score": 0.0
        }
        
        if self.current_tasks:
            completed_tasks = [task for task in self.current_tasks.values() if task.status == ProgressStatus.COMPLETED]
            metrics["task_completion_rate"] = len(completed_tasks) / len(self.current_tasks) * 100
            
            quality_scores = [task.quality_score for task in self.current_tasks.values() if task.quality_score > 0]
            if quality_scores:
                metrics["average_task_quality"] = sum(quality_scores) / len(quality_scores)
        
        # Git hygiene score
        if self.last_git_status:
            git_score = 100.0
            if self.last_git_status.uncommitted_changes > 0:
                git_score -= 20
            if self.last_git_status.untracked_files > 5:
                git_score -= 15
            if self.last_git_status.staged_changes > 0:
                git_score += 10  # Staging is good
            metrics["git_hygiene_score"] = max(0, git_score)
        
        # Productivity score based on tasks completed vs time
        session_hours = (datetime.now() - self.session_start).total_seconds() / 3600
        if session_hours > 0:
            completed_tasks = len([task for task in self.current_tasks.values() if task.status == ProgressStatus.COMPLETED])
            metrics["productivity_score"] = min(100, completed_tasks / session_hours * 20)
        
        return metrics
    
    def _estimate_completion(self) -> Optional[datetime]:
        """Estimate overall completion time."""
        if not self.current_tasks:
            return None
        
        incomplete_tasks = [task for task in self.current_tasks.values() 
                          if task.status not in [ProgressStatus.COMPLETED, ProgressStatus.FAILED]]
        
        if not incomplete_tasks:
            return datetime.now()  # Already completed
        
        # Simple estimation based on current progress rates
        total_remaining = sum(100 - task.progress_percentage for task in incomplete_tasks)
        
        if total_remaining == 0:
            return datetime.now()
        
        # Estimate based on recent progress (very rough)
        estimated_hours = total_remaining / 20  # Assume 20% per hour
        return datetime.now() + timedelta(hours=estimated_hours)
    
    async def _generate_progress_report(self) -> None:
        """Generate and save a structured progress report."""
        try:
            if not self.last_checkpoint:
                return
            
            report = {
                "report_id": f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
                "session_duration_minutes": (datetime.now() - self.session_start).total_seconds() / 60,
                "checkpoint_reference": self.last_checkpoint.checkpoint_id,
                "summary": {
                    "overall_status": self.last_checkpoint.overall_status.value,
                    "completion_percentage": round(self.last_checkpoint.completion_percentage, 1),
                    "tasks_total": len(self.current_tasks),
                    "tasks_completed": len([t for t in self.current_tasks.values() if t.status == ProgressStatus.COMPLETED]),
                    "tasks_blocked": len([t for t in self.current_tasks.values() if t.status == ProgressStatus.BLOCKED])
                },
                "git_status": asdict(self.last_checkpoint.git_status),
                "quality_metrics": self.last_checkpoint.quality_metrics,
                "achievements": self.last_checkpoint.achievements,
                "blockers": self.last_checkpoint.blockers,
                "next_actions": self.last_checkpoint.next_actions,
                "statistics": self.stats
            }
            
            # Save report
            report_file = self.reports_dir / f"progress_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            # Also save as latest report
            latest_report_file = self.reports_dir / "latest_progress_report.json"
            with open(latest_report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.stats["reports_generated"] += 1
            
            # Log summary
            logger.info(f"Progress Report: {report['summary']['completion_percentage']}% complete, "
                       f"{report['summary']['tasks_completed']}/{report['summary']['tasks_total']} tasks, "
                       f"Status: {report['summary']['overall_status']}")
            
        except Exception as e:
            logger.error(f"Error generating progress report: {e}")
    
    def add_task(self, task_id: str, description: str, estimated_completion: Optional[datetime] = None) -> None:
        """
        Add a task to progress tracking.
        
        Args:
            task_id: Unique task identifier
            description: Task description
            estimated_completion: Optional estimated completion time
        """
        task = TaskProgress(
            task_id=task_id,
            description=description,
            status=ProgressStatus.ON_TRACK,
            progress_percentage=0.0,
            estimated_completion=estimated_completion
        )
        
        self.current_tasks[task_id] = task
        self.stats["tasks_tracked"] += 1
        
        logger.info(f"Added task: {task_id} - {description}")
    
    def update_task(self, task_id: str, **kwargs) -> bool:
        """
        Update task progress.
        
        Args:
            task_id: Task identifier
            **kwargs: Fields to update
            
        Returns:
            True if update successful
        """
        if task_id not in self.current_tasks:
            logger.warning(f"Task {task_id} not found")
            return False
        
        task = self.current_tasks[task_id]
        
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        task.last_update = datetime.now()
        
        logger.debug(f"Updated task {task_id}: {kwargs}")
        return True
    
    def complete_task(self, task_id: str, quality_score: float = 100.0) -> bool:
        """
        Mark a task as completed.
        
        Args:
            task_id: Task identifier
            quality_score: Quality score (0-100)
            
        Returns:
            True if successful
        """
        return self.update_task(
            task_id,
            status=ProgressStatus.COMPLETED,
            progress_percentage=100.0,
            quality_score=quality_score
        )
    
    def block_task(self, task_id: str, blocker: str) -> bool:
        """
        Block a task with a specific reason.
        
        Args:
            task_id: Task identifier
            blocker: Description of the blocker
            
        Returns:
            True if successful
        """
        if task_id not in self.current_tasks:
            return False
        
        task = self.current_tasks[task_id]
        task.status = ProgressStatus.BLOCKED
        if blocker not in task.blockers:
            task.blockers.append(blocker)
        task.last_update = datetime.now()
        
        logger.warning(f"Task {task_id} blocked: {blocker}")
        return True
    
    async def manual_checkpoint(self, description: str) -> str:
        """
        Create a manual checkpoint.
        
        Args:
            description: Checkpoint description
            
        Returns:
            Checkpoint ID
        """
        return await self.create_checkpoint(CheckpointType.MANUAL, description)
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get current progress summary."""
        overall_status, completion_percentage = self._calculate_overall_progress()
        
        return {
            "overall_status": overall_status.value,
            "completion_percentage": round(completion_percentage, 1),
            "tasks": {
                "total": len(self.current_tasks),
                "completed": len([t for t in self.current_tasks.values() if t.status == ProgressStatus.COMPLETED]),
                "blocked": len([t for t in self.current_tasks.values() if t.status == ProgressStatus.BLOCKED]),
                "in_progress": len([t for t in self.current_tasks.values() if t.status == ProgressStatus.ON_TRACK])
            },
            "session_duration_minutes": (datetime.now() - self.session_start).total_seconds() / 60,
            "git_clean": self.last_git_status.repository_clean if self.last_git_status else True,
            "statistics": self.stats
        }
    
    def get_latest_report_path(self) -> Optional[Path]:
        """Get path to latest progress report."""
        latest_report = self.reports_dir / "latest_progress_report.json"
        return latest_report if latest_report.exists() else None


# CLI Interface
async def main():
    """CLI interface for progress reporter."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Progress Checkpoint System")
    parser.add_argument("--start", action="store_true", help="Start progress monitoring")
    parser.add_argument("--stop", action="store_true", help="Stop progress monitoring")
    parser.add_argument("--checkpoint", help="Create manual checkpoint with description")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--add-task", nargs=2, metavar=("ID", "DESC"), help="Add task")
    parser.add_argument("--complete-task", help="Complete task by ID")
    parser.add_argument("--interval", type=int, default=300, help="Report interval in seconds")
    
    args = parser.parse_args()
    
    # Initialize reporter
    reporter = ProgressReporter()
    reporter.report_interval = args.interval
    
    try:
        if args.start:
            print("Starting progress monitoring...")
            await reporter.start_monitoring()
            # Keep running
            while reporter.reporting_active:
                await asyncio.sleep(1)
                
        elif args.stop:
            print("Stopping progress monitoring...")
            await reporter.stop_monitoring()
            
        elif args.checkpoint:
            checkpoint_id = await reporter.manual_checkpoint(args.checkpoint)
            print(f"Created checkpoint: {checkpoint_id}")
            
        elif args.status:
            summary = reporter.get_progress_summary()
            print(json.dumps(summary, indent=2))
            
        elif args.add_task:
            task_id, description = args.add_task
            reporter.add_task(task_id, description)
            print(f"Added task: {task_id}")
            
        elif args.complete_task:
            success = reporter.complete_task(args.complete_task)
            print(f"Task completion: {'success' if success else 'failed'}")
            
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        print("\nStopping progress monitoring...")
        await reporter.stop_monitoring()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())