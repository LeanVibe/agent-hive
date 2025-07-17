"""
GitMilestoneManager - Git milestone and progress tracking system for LeanVibe Agent Hive.

Provides comprehensive git milestone management including automatic milestone creation,
commit recommendations, and progress tracking integrated with the state management system.
"""

import asyncio
import subprocess
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class GitMilestone:
    """Represents a git milestone with metadata."""
    milestone_id: str
    title: str
    description: str
    commit_hash: str
    branch: str
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    state_snapshot: Dict[str, Any] = field(default_factory=dict)
    is_major: bool = False
    parent_milestone_id: Optional[str] = None


@dataclass
class CommitRecommendation:
    """Represents a commit recommendation."""
    recommendation_id: str
    commit_hash: str
    branch: str
    message: str
    priority: int
    reasoning: str
    files_changed: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    applied: bool = False


@dataclass
class GitProgress:
    """Represents git progress metrics."""
    branch: str
    commits_ahead: int
    commits_behind: int
    uncommitted_changes: int
    last_commit_hash: str
    last_commit_message: str
    last_commit_author: str
    last_commit_date: datetime
    branch_age: timedelta
    is_clean: bool


class GitMilestoneManager:
    """Manages git milestones and progress tracking."""
    
    def __init__(self, repo_path: Optional[Path] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize the GitMilestoneManager."""
        self.repo_path = repo_path or Path.cwd()
        self.config = config or {}
        self.milestones: Dict[str, GitMilestone] = {}
        self.recommendations: Dict[str, CommitRecommendation] = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize git repository check
        self.is_git_repo = self._check_git_repo()
        
    def _check_git_repo(self) -> bool:
        """Check if the current directory is a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    async def create_milestone(self, title: str, description: str, 
                             tags: Optional[List[str]] = None,
                             is_major: bool = False) -> Optional[GitMilestone]:
        """Create a new git milestone."""
        try:
            if not self.is_git_repo:
                self.logger.error("Not a git repository")
                return None
            
            # Get current commit info
            commit_info = await self._get_current_commit_info()
            if not commit_info:
                return None
            
            # Generate milestone ID
            milestone_id = self._generate_milestone_id(title, commit_info["hash"])
            
            # Create milestone
            milestone = GitMilestone(
                milestone_id=milestone_id,
                title=title,
                description=description,
                commit_hash=commit_info["hash"],
                branch=commit_info["branch"],
                tags=tags or [],
                is_major=is_major,
                metrics=await self._calculate_milestone_metrics(commit_info["hash"]),
                state_snapshot=await self._capture_state_snapshot()
            )
            
            # Store milestone
            self.milestones[milestone_id] = milestone
            
            self.logger.info(f"Created milestone: {milestone_id}")
            return milestone
            
        except Exception as e:
            self.logger.error(f"Error creating milestone: {e}")
            return None
    
    async def get_milestone(self, milestone_id: str) -> Optional[GitMilestone]:
        """Get a milestone by ID."""
        return self.milestones.get(milestone_id)
    
    async def list_milestones(self, branch: Optional[str] = None) -> List[GitMilestone]:
        """List all milestones, optionally filtered by branch."""
        milestones = list(self.milestones.values())
        
        if branch:
            milestones = [m for m in milestones if m.branch == branch]
        
        # Sort by creation date (newest first)
        milestones.sort(key=lambda m: m.created_at, reverse=True)
        return milestones
    
    async def delete_milestone(self, milestone_id: str) -> bool:
        """Delete a milestone."""
        try:
            if milestone_id in self.milestones:
                del self.milestones[milestone_id]
                self.logger.info(f"Deleted milestone: {milestone_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error deleting milestone {milestone_id}: {e}")
            return False
    
    async def get_progress(self, branch: Optional[str] = None) -> Optional[GitProgress]:
        """Get current git progress information."""
        try:
            if not self.is_git_repo:
                return None
            
            current_branch = branch or await self._get_current_branch()
            if not current_branch:
                return None
            
            # Get commit counts
            ahead_behind = await self._get_ahead_behind_counts(current_branch)
            
            # Get uncommitted changes
            uncommitted = await self._get_uncommitted_changes_count()
            
            # Get last commit info
            last_commit = await self._get_current_commit_info()
            
            # Calculate branch age
            branch_age = await self._get_branch_age(current_branch)
            
            # Check if working directory is clean
            is_clean = await self._is_working_directory_clean()
            
            progress = GitProgress(
                branch=current_branch,
                commits_ahead=ahead_behind["ahead"],
                commits_behind=ahead_behind["behind"],
                uncommitted_changes=uncommitted,
                last_commit_hash=last_commit["hash"],
                last_commit_message=last_commit["message"],
                last_commit_author=last_commit["author"],
                last_commit_date=last_commit["date"],
                branch_age=branch_age,
                is_clean=is_clean
            )
            
            return progress
            
        except Exception as e:
            self.logger.error(f"Error getting progress: {e}")
            return None
    
    async def analyze_commit_patterns(self, days: int = 30) -> Dict[str, Any]:
        """Analyze commit patterns over the specified number of days."""
        try:
            if not self.is_git_repo:
                return {}
            
            # Get commits from the last N days
            since_date = datetime.now() - timedelta(days=days)
            commits = await self._get_commits_since(since_date)
            
            if not commits:
                return {}
            
            # Analyze patterns
            analysis = {
                "total_commits": len(commits),
                "commits_per_day": len(commits) / days,
                "authors": {},
                "hourly_distribution": {},
                "daily_distribution": {},
                "file_changes": {},
                "message_patterns": {}
            }
            
            # Process each commit
            for commit in commits:
                # Author analysis
                author = commit.get("author", "Unknown")
                analysis["authors"][author] = analysis["authors"].get(author, 0) + 1
                
                # Time analysis
                commit_date = commit.get("date")
                if commit_date:
                    hour = commit_date.hour
                    day = commit_date.strftime("%A")
                    analysis["hourly_distribution"][hour] = analysis["hourly_distribution"].get(hour, 0) + 1
                    analysis["daily_distribution"][day] = analysis["daily_distribution"].get(day, 0) + 1
                
                # File changes analysis
                files = commit.get("files", [])
                for file in files:
                    analysis["file_changes"][file] = analysis["file_changes"].get(file, 0) + 1
                
                # Message patterns
                message = commit.get("message", "")
                if message:
                    words = message.lower().split()
                    for word in words:
                        if len(word) > 3:  # Skip short words
                            analysis["message_patterns"][word] = analysis["message_patterns"].get(word, 0) + 1
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing commit patterns: {e}")
            return {}
    
    async def generate_commit_recommendation(self, context: Dict[str, Any]) -> Optional[CommitRecommendation]:
        """Generate a commit recommendation based on current context."""
        try:
            if not self.is_git_repo:
                return None
            
            # Get current state
            current_commit = await self._get_current_commit_info()
            changed_files = await self._get_changed_files()
            
            if not changed_files:
                return None
            
            # Generate recommendation
            recommendation_id = self._generate_recommendation_id(current_commit["hash"])
            
            # Analyze changes to suggest commit message
            message = await self._suggest_commit_message(changed_files, context)
            
            # Calculate priority based on file types and changes
            priority = await self._calculate_commit_priority(changed_files)
            
            # Generate reasoning
            reasoning = await self._generate_commit_reasoning(changed_files, context)
            
            recommendation = CommitRecommendation(
                recommendation_id=recommendation_id,
                commit_hash=current_commit["hash"],
                branch=current_commit["branch"],
                message=message,
                priority=priority,
                reasoning=reasoning,
                files_changed=changed_files
            )
            
            # Store recommendation
            self.recommendations[recommendation_id] = recommendation
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Error generating commit recommendation: {e}")
            return None
    
    async def apply_commit_recommendation(self, recommendation_id: str) -> bool:
        """Apply a commit recommendation."""
        try:
            if recommendation_id not in self.recommendations:
                return False
            
            recommendation = self.recommendations[recommendation_id]
            
            # Apply the commit
            result = await self._execute_commit(recommendation.message)
            
            if result:
                recommendation.applied = True
                self.logger.info(f"Applied commit recommendation: {recommendation_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error applying recommendation {recommendation_id}: {e}")
            return False
    
    async def _get_current_commit_info(self) -> Dict[str, Any]:
        """Get information about the current commit."""
        try:
            # Get commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            commit_hash = result.stdout.strip()
            
            # Get branch name
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            branch = result.stdout.strip()
            
            # Get commit message
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=format:%s"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            message = result.stdout.strip()
            
            # Get author
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=format:%an"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            author = result.stdout.strip()
            
            # Get date
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=format:%ci"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            date_str = result.stdout.strip()
            date = datetime.fromisoformat(date_str.replace(' ', 'T', 1).rsplit(' ', 1)[0])
            
            return {
                "hash": commit_hash,
                "branch": branch,
                "message": message,
                "author": author,
                "date": date
            }
            
        except Exception as e:
            self.logger.error(f"Error getting current commit info: {e}")
            return {}
    
    async def _get_current_branch(self) -> Optional[str]:
        """Get the current branch name."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None
    
    async def _get_ahead_behind_counts(self, branch: str) -> Dict[str, int]:
        """Get ahead/behind counts for a branch."""
        try:
            result = subprocess.run(
                ["git", "rev-list", "--count", "--left-right", f"origin/{branch}...HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                counts = result.stdout.strip().split()
                return {
                    "behind": int(counts[0]) if len(counts) > 0 else 0,
                    "ahead": int(counts[1]) if len(counts) > 1 else 0
                }
            
            return {"ahead": 0, "behind": 0}
            
        except Exception:
            return {"ahead": 0, "behind": 0}
    
    async def _get_uncommitted_changes_count(self) -> int:
        """Get the number of uncommitted changes."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            
            return 0
            
        except Exception:
            return 0
    
    async def _get_branch_age(self, branch: str) -> timedelta:
        """Get the age of a branch."""
        try:
            result = subprocess.run(
                ["git", "log", "--pretty=format:%ci", "-1", branch],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                date_str = result.stdout.strip()
                branch_date = datetime.fromisoformat(date_str.replace(' ', 'T', 1).rsplit(' ', 1)[0])
                return datetime.now() - branch_date
            
            return timedelta(0)
            
        except Exception:
            return timedelta(0)
    
    async def _is_working_directory_clean(self) -> bool:
        """Check if the working directory is clean."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            return result.returncode == 0 and not result.stdout.strip()
            
        except Exception:
            return False
    
    async def _get_commits_since(self, since_date: datetime) -> List[Dict[str, Any]]:
        """Get commits since a specific date."""
        try:
            since_str = since_date.strftime("%Y-%m-%d")
            result = subprocess.run(
                ["git", "log", "--since", since_str, "--pretty=format:%H|%an|%ci|%s"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return []
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 3)
                    if len(parts) >= 4:
                        commits.append({
                            "hash": parts[0],
                            "author": parts[1],
                            "date": datetime.fromisoformat(parts[2].replace(' ', 'T', 1).rsplit(' ', 1)[0]),
                            "message": parts[3]
                        })
            
            return commits
            
        except Exception as e:
            self.logger.error(f"Error getting commits since {since_date}: {e}")
            return []
    
    async def _get_changed_files(self) -> List[str]:
        """Get list of changed files."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return []
            
            files = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    # Extract filename from git status format
                    parts = line.split(None, 1)
                    if len(parts) >= 2:
                        files.append(parts[1])
            
            return files
            
        except Exception:
            return []
    
    async def _calculate_milestone_metrics(self, commit_hash: str) -> Dict[str, Any]:
        """Calculate metrics for a milestone."""
        # This is a placeholder - real implementation would calculate
        # various metrics like code quality, test coverage, etc.
        return {
            "commit_hash": commit_hash,
            "files_changed": 0,
            "lines_added": 0,
            "lines_removed": 0,
            "test_coverage": 0.0,
            "quality_score": 0.0
        }
    
    async def _capture_state_snapshot(self) -> Dict[str, Any]:
        """Capture current state snapshot."""
        # This is a placeholder - real implementation would capture
        # relevant system state
        return {
            "timestamp": datetime.now().isoformat(),
            "branch": await self._get_current_branch(),
            "working_directory_clean": await self._is_working_directory_clean()
        }
    
    async def _suggest_commit_message(self, changed_files: List[str], context: Dict[str, Any]) -> str:
        """Suggest a commit message based on changed files and context."""
        # Simple commit message generation
        if not changed_files:
            return "chore: update files"
        
        # Analyze file types
        py_files = [f for f in changed_files if f.endswith('.py')]
        test_files = [f for f in changed_files if 'test' in f.lower()]
        doc_files = [f for f in changed_files if f.endswith('.md') or f.endswith('.rst')]
        
        if test_files:
            return "test: add/update tests"
        elif py_files:
            return "feat: implement new functionality"
        elif doc_files:
            return "docs: update documentation"
        else:
            return "chore: update files"
    
    async def _calculate_commit_priority(self, changed_files: List[str]) -> int:
        """Calculate commit priority based on changed files."""
        # Simple priority calculation
        critical_files = [f for f in changed_files if any(keyword in f.lower() for keyword in ['security', 'auth', 'critical'])]
        test_files = [f for f in changed_files if 'test' in f.lower()]
        
        if critical_files:
            return 1  # High priority
        elif test_files:
            return 3  # Medium priority
        else:
            return 5  # Normal priority
    
    async def _generate_commit_reasoning(self, changed_files: List[str], context: Dict[str, Any]) -> str:
        """Generate reasoning for commit recommendation."""
        file_count = len(changed_files)
        return f"Based on {file_count} changed files, this commit should be applied to maintain project progress."
    
    async def _execute_commit(self, message: str) -> bool:
        """Execute a git commit."""
        try:
            # Add all changes
            subprocess.run(
                ["git", "add", "."],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            # Commit with message
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Error executing commit: {e}")
            return False
    
    def _generate_milestone_id(self, title: str, commit_hash: str) -> str:
        """Generate a unique milestone ID."""
        content = f"{title}:{commit_hash}:{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]
    
    def _generate_recommendation_id(self, commit_hash: str) -> str:
        """Generate a unique recommendation ID."""
        content = f"rec:{commit_hash}:{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]