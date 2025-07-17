"""
Git Milestone Manager for tracking development milestones.

This module provides functionality to manage git milestones and track
development progress in relation to git commits and branches.
"""

import logging
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import os


class MilestoneType(Enum):
    """Types of milestones."""
    FEATURE_COMPLETE = "feature_complete"
    BUG_FIX = "bug_fix"
    RELEASE = "release"
    HOTFIX = "hotfix"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    CUSTOM = "custom"


class MilestoneStatus(Enum):
    """Status of a milestone."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class GitMilestone:
    """Represents a git milestone."""
    id: str
    name: str
    description: str
    type: MilestoneType
    status: MilestoneStatus = MilestoneStatus.PENDING
    branch: Optional[str] = None
    commit_hash: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GitStats:
    """Git repository statistics."""
    total_commits: int
    branches: List[str]
    current_branch: str
    last_commit_hash: str
    last_commit_message: str
    last_commit_date: datetime
    uncommitted_changes: bool
    repository_path: str


@dataclass
class CommitRecommendation:
    """Represents a commit recommendation."""
    should_commit: bool
    reason: str
    confidence: float
    suggested_message: str
    files_to_commit: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class GitMilestoneManager:
    """Manages git milestones and tracks development progress."""
    
    def __init__(self, state_manager=None):
        """
        Initialize the GitMilestoneManager.
        
        Args:
            state_manager: State manager for integration
        """
        self.logger = logging.getLogger(__name__)
        self.state_manager = state_manager
        
        # Milestone storage
        self.milestones: Dict[str, GitMilestone] = {}
        
        # Git repository info
        self.repository_path = self._get_repository_path()
        
        # Statistics
        self.stats = {
            "total_milestones": 0,
            "completed_milestones": 0,
            "pending_milestones": 0,
            "in_progress_milestones": 0,
            "last_milestone_date": None,
            "git_stats": None
        }
        
        # Initialize git stats
        self._update_git_stats()
        
        self.logger.info(f"GitMilestoneManager initialized for repository: {self.repository_path}")
    
    def _get_repository_path(self) -> str:
        """Get the current repository path."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            # Fallback to current directory
            return os.getcwd()
    
    def _update_git_stats(self):
        """Update git repository statistics."""
        try:
            # Get current branch
            current_branch = self._run_git_command(["git", "branch", "--show-current"])
            
            # Get all branches
            branches_output = self._run_git_command(["git", "branch", "-a"])
            branches = [
                branch.strip().replace("* ", "").replace("remotes/origin/", "")
                for branch in branches_output.split("\n")
                if branch.strip() and not branch.strip().startswith("remotes/origin/HEAD")
            ]
            
            # Get last commit info
            last_commit_hash = self._run_git_command(["git", "rev-parse", "HEAD"])
            last_commit_message = self._run_git_command(["git", "log", "-1", "--pretty=format:%s"])
            last_commit_date_str = self._run_git_command(["git", "log", "-1", "--pretty=format:%ci"])
            
            # Parse commit date
            try:
                last_commit_date = datetime.fromisoformat(last_commit_date_str.replace(" ", "T", 1).rsplit(" ", 1)[0])
            except:
                last_commit_date = datetime.now()
            
            # Get total commits
            total_commits_str = self._run_git_command(["git", "rev-list", "--count", "HEAD"])
            total_commits = int(total_commits_str) if total_commits_str.isdigit() else 0
            
            # Check for uncommitted changes
            status_output = self._run_git_command(["git", "status", "--porcelain"])
            uncommitted_changes = bool(status_output.strip())
            
            self.stats["git_stats"] = GitStats(
                total_commits=total_commits,
                branches=list(set(branches)),
                current_branch=current_branch,
                last_commit_hash=last_commit_hash,
                last_commit_message=last_commit_message,
                last_commit_date=last_commit_date,
                uncommitted_changes=uncommitted_changes,
                repository_path=self.repository_path
            )
            
        except Exception as e:
            self.logger.error(f"Error updating git stats: {e}")
            self.stats["git_stats"] = None
    
    def _run_git_command(self, command: List[str]) -> str:
        """
        Run a git command and return the output.
        
        Args:
            command: Git command as list of strings
            
        Returns:
            str: Command output
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repository_path
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git command failed: {' '.join(command)}, error: {e}")
            return ""
    
    def create_milestone(self, name: str, description: str, milestone_type: MilestoneType,
                        branch: Optional[str] = None, tags: Optional[List[str]] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> GitMilestone:
        """
        Create a new milestone.
        
        Args:
            name: Milestone name
            description: Milestone description
            milestone_type: Type of milestone
            branch: Git branch associated with the milestone
            tags: Tags for the milestone
            metadata: Additional metadata
            
        Returns:
            GitMilestone: Created milestone
        """
        milestone_id = f"milestone_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        milestone = GitMilestone(
            id=milestone_id,
            name=name,
            description=description,
            type=milestone_type,
            branch=branch or self._get_current_branch(),
            tags=tags or [],
            metadata=metadata or {}
        )
        
        self.milestones[milestone_id] = milestone
        self._update_milestone_stats()
        
        self.logger.info(f"Created milestone: {name} ({milestone_id})")
        return milestone
    
    def complete_milestone(self, milestone_id: str, commit_hash: Optional[str] = None) -> bool:
        """
        Mark a milestone as completed.
        
        Args:
            milestone_id: ID of the milestone to complete
            commit_hash: Git commit hash associated with completion
            
        Returns:
            bool: True if milestone was completed successfully
        """
        try:
            if milestone_id not in self.milestones:
                self.logger.error(f"Milestone not found: {milestone_id}")
                return False
            
            milestone = self.milestones[milestone_id]
            milestone.status = MilestoneStatus.COMPLETED
            milestone.completed_at = datetime.now()
            milestone.commit_hash = commit_hash or self._get_current_commit_hash()
            
            self._update_milestone_stats()
            
            self.logger.info(f"Completed milestone: {milestone.name} ({milestone_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error completing milestone {milestone_id}: {e}")
            return False
    
    def cancel_milestone(self, milestone_id: str, reason: str = "") -> bool:
        """
        Cancel a milestone.
        
        Args:
            milestone_id: ID of the milestone to cancel
            reason: Reason for cancellation
            
        Returns:
            bool: True if milestone was cancelled successfully
        """
        try:
            if milestone_id not in self.milestones:
                self.logger.error(f"Milestone not found: {milestone_id}")
                return False
            
            milestone = self.milestones[milestone_id]
            milestone.status = MilestoneStatus.CANCELLED
            milestone.metadata["cancellation_reason"] = reason
            milestone.metadata["cancelled_at"] = datetime.now().isoformat()
            
            self._update_milestone_stats()
            
            self.logger.info(f"Cancelled milestone: {milestone.name} ({milestone_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling milestone {milestone_id}: {e}")
            return False
    
    def _get_current_branch(self) -> str:
        """Get the current git branch."""
        return self._run_git_command(["git", "branch", "--show-current"])
    
    def _get_current_commit_hash(self) -> str:
        """Get the current commit hash."""
        return self._run_git_command(["git", "rev-parse", "HEAD"])
    
    def _update_milestone_stats(self):
        """Update milestone statistics."""
        self.stats["total_milestones"] = len(self.milestones)
        self.stats["completed_milestones"] = len([m for m in self.milestones.values() if m.status == MilestoneStatus.COMPLETED])
        self.stats["pending_milestones"] = len([m for m in self.milestones.values() if m.status == MilestoneStatus.PENDING])
        self.stats["in_progress_milestones"] = len([m for m in self.milestones.values() if m.status == MilestoneStatus.IN_PROGRESS])
        
        # Update last milestone date
        completed_milestones = [m for m in self.milestones.values() if m.completed_at]
        if completed_milestones:
            self.stats["last_milestone_date"] = max(m.completed_at for m in completed_milestones)
    
    async def should_create_milestone(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Check if a milestone should be created based on current state.
        
        Returns:
            Tuple[bool, str, Dict[str, Any]]: (should_create, reason, milestone_data)
        """
        try:
            # Update git stats
            self._update_git_stats()
            
            git_stats = self.stats["git_stats"]
            if not git_stats:
                return False, "Git statistics not available", {}
            
            # Check if there are uncommitted changes
            if git_stats.uncommitted_changes:
                return False, "Uncommitted changes present", {}
            
            # Check if enough commits have been made since last milestone
            if self.stats["total_milestones"] == 0:
                return True, "No milestones created yet", {
                    "suggested_name": "Initial Milestone",
                    "suggested_type": MilestoneType.FEATURE_COMPLETE,
                    "commit_hash": git_stats.last_commit_hash
                }
            
            # Check time since last milestone
            if self.stats["last_milestone_date"]:
                time_since_last = datetime.now() - self.stats["last_milestone_date"]
                if time_since_last > timedelta(days=1):
                    return True, "Time-based milestone trigger", {
                        "suggested_name": f"Daily Milestone {datetime.now().strftime('%Y-%m-%d')}",
                        "suggested_type": MilestoneType.FEATURE_COMPLETE,
                        "commit_hash": git_stats.last_commit_hash
                    }
            
            return False, "No milestone creation criteria met", {}
            
        except Exception as e:
            self.logger.error(f"Error checking milestone creation: {e}")
            return False, f"Error: {e}", {}
    
    def get_milestone(self, milestone_id: str) -> Optional[GitMilestone]:
        """
        Get a specific milestone.
        
        Args:
            milestone_id: ID of the milestone
            
        Returns:
            Optional[GitMilestone]: Milestone if found
        """
        return self.milestones.get(milestone_id)
    
    def list_milestones(self, status: Optional[MilestoneStatus] = None,
                       milestone_type: Optional[MilestoneType] = None) -> List[GitMilestone]:
        """
        List milestones with optional filtering.
        
        Args:
            status: Filter by status
            milestone_type: Filter by type
            
        Returns:
            List[GitMilestone]: Filtered list of milestones
        """
        milestones = list(self.milestones.values())
        
        if status:
            milestones = [m for m in milestones if m.status == status]
        
        if milestone_type:
            milestones = [m for m in milestones if m.type == milestone_type]
        
        return sorted(milestones, key=lambda x: x.created_at, reverse=True)
    
    def get_milestone_stats(self) -> Dict[str, Any]:
        """
        Get milestone statistics.
        
        Returns:
            Dict[str, Any]: Statistics about milestones
        """
        self._update_milestone_stats()
        return self.stats.copy()
    
    def export_milestones(self, filename: str) -> bool:
        """
        Export milestones to a JSON file.
        
        Args:
            filename: Output filename
            
        Returns:
            bool: True if export was successful
        """
        try:
            milestone_data = []
            for milestone in self.milestones.values():
                data = {
                    "id": milestone.id,
                    "name": milestone.name,
                    "description": milestone.description,
                    "type": milestone.type.value,
                    "status": milestone.status.value,
                    "branch": milestone.branch,
                    "commit_hash": milestone.commit_hash,
                    "created_at": milestone.created_at.isoformat(),
                    "completed_at": milestone.completed_at.isoformat() if milestone.completed_at else None,
                    "tags": milestone.tags,
                    "metadata": milestone.metadata
                }
                milestone_data.append(data)
            
            with open(filename, 'w') as f:
                json.dump(milestone_data, f, indent=2)
            
            self.logger.info(f"Exported {len(milestone_data)} milestones to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting milestones: {e}")
            return False
    
    def import_milestones(self, filename: str) -> bool:
        """
        Import milestones from a JSON file.
        
        Args:
            filename: Input filename
            
        Returns:
            bool: True if import was successful
        """
        try:
            with open(filename, 'r') as f:
                milestone_data = json.load(f)
            
            imported_count = 0
            for data in milestone_data:
                milestone = GitMilestone(
                    id=data["id"],
                    name=data["name"],
                    description=data["description"],
                    type=MilestoneType(data["type"]),
                    status=MilestoneStatus(data["status"]),
                    branch=data.get("branch"),
                    commit_hash=data.get("commit_hash"),
                    created_at=datetime.fromisoformat(data["created_at"]),
                    completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
                    tags=data.get("tags", []),
                    metadata=data.get("metadata", {})
                )
                
                self.milestones[milestone.id] = milestone
                imported_count += 1
            
            self._update_milestone_stats()
            self.logger.info(f"Imported {imported_count} milestones from {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error importing milestones: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check.
        
        Returns:
            Dict[str, Any]: Health check results
        """
        try:
            # Check git repository access
            git_accessible = bool(self._run_git_command(["git", "status"]))
            
            # Check milestone data integrity
            milestone_count = len(self.milestones)
            
            return {
                "status": "healthy" if git_accessible else "degraded",
                "git_accessible": git_accessible,
                "repository_path": self.repository_path,
                "milestone_count": milestone_count,
                "git_stats_available": self.stats["git_stats"] is not None,
                "last_update": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_update": datetime.now().isoformat()
            }