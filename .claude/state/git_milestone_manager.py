"""Git milestone management for LeanVibe orchestrator."""

import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path

import git


@dataclass
class GitMilestone:
    """Represents a git milestone."""
    name: str
    tag: str
    commit_hash: str
    timestamp: float
    description: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass 
class CommitRecommendation:
    """Recommendation for a commit action."""
    action: str  # 'commit', 'skip', 'wait'
    message: str
    confidence: float
    reason: str


class GitMilestoneManager:
    """Manages git milestones and commit recommendations."""
    
    def __init__(self, repo_path: Path):
        """Initialize with repository path."""
        try:
            self.repo = git.Repo(repo_path)
        except git.exc.InvalidGitRepositoryError:
            # Initialize a new repository if one doesn't exist
            self.repo = git.Repo.init(repo_path)
        
        self.milestones: List[GitMilestone] = []
        self._load_milestones()
    
    def _load_milestones(self):
        """Load existing milestones from git tags."""
        try:
            for tag in self.repo.tags:
                milestone = GitMilestone(
                    name=tag.name,
                    tag=tag.name,
                    commit_hash=tag.commit.hexsha,
                    timestamp=tag.commit.committed_date,
                    description=tag.commit.message.strip()
                )
                self.milestones.append(milestone)
        except Exception:
            # Handle case where repository has no tags yet
            pass
    
    def create_milestone(self, name: str, description: str = "") -> GitMilestone:
        """Create a new milestone at current HEAD."""
        current_commit = self.repo.head.commit
        
        # Create git tag
        tag = self.repo.create_tag(name, message=description)
        
        milestone = GitMilestone(
            name=name,
            tag=tag.name,
            commit_hash=current_commit.hexsha,
            timestamp=time.time(),
            description=description
        )
        
        self.milestones.append(milestone)
        return milestone
    
    def get_milestones(self) -> List[GitMilestone]:
        """Get all milestones."""
        return self.milestones
    
    def get_milestone(self, name: str) -> Optional[GitMilestone]:
        """Get a specific milestone by name."""
        for milestone in self.milestones:
            if milestone.name == name:
                return milestone
        return None
    
    def recommend_commit(self, context: Dict[str, Any]) -> CommitRecommendation:
        """Recommend whether to commit based on context."""
        # Simple recommendation logic
        changes_count = len(list(self.repo.index.diff(None))) + len(list(self.repo.index.diff("HEAD")))
        
        if changes_count == 0:
            return CommitRecommendation(
                action="skip",
                message="No changes to commit",
                confidence=1.0,
                reason="No staged or unstaged changes detected"
            )
        
        if changes_count > 20:
            return CommitRecommendation(
                action="wait",
                message="Consider breaking into smaller commits",
                confidence=0.8,
                reason=f"Large changeset ({changes_count} files) detected"
            )
        
        # Default recommendation
        return CommitRecommendation(
            action="commit",
            message="Ready to commit changes",
            confidence=0.9,
            reason=f"Reasonable changeset size ({changes_count} files)"
        )
    
    def get_commit_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent commit history."""
        commits = []
        for commit in self.repo.iter_commits(max_count=limit):
            commits.append({
                "hash": commit.hexsha[:8],
                "message": commit.message.strip(),
                "author": commit.author.name,
                "timestamp": commit.committed_date
            })
        return commits