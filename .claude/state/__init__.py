"""State management module for LeanVibe orchestrator.

Provides compatibility re-exports for tests importing from `.claude.state`.
"""

from .state_manager import StateManager, AgentState, TaskState, SystemState  # type: ignore
from .git_milestone_manager import GitMilestoneManager, GitMilestone, CommitRecommendation  # type: ignore

__all__ = [
    'StateManager',
    'AgentState',
    'TaskState',
    'SystemState',
    'GitMilestoneManager',
    'GitMilestone',
    'CommitRecommendation',
]