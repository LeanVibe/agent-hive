"""
Tutorial Manager for Interactive Tutorial Framework

Handles tutorial loading, progress tracking, and user management.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import os
from datetime import datetime


class TutorialStatus(Enum):
    """Tutorial status enumeration."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DifficultyLevel(Enum):
    """Tutorial difficulty levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass
class TutorialStep:
    """Individual tutorial step with validation."""
    step_id: str
    title: str
    description: str
    instructions: List[str]
    code_examples: List[str]
    validation_command: Optional[str] = None
    expected_output: Optional[str] = None
    hints: List[str] = field(default_factory=list)
    estimated_time: int = 5  # minutes
    dependencies: List[str] = field(default_factory=list)


@dataclass
class TutorialMetadata:
    """Tutorial metadata and configuration."""
    tutorial_id: str
    title: str
    description: str
    difficulty: DifficultyLevel
    estimated_time: int  # minutes
    prerequisites: List[str]
    learning_objectives: List[str]
    tags: List[str]
    version: str = "1.0"
    author: str = "LeanVibe Team"


@dataclass
class UserProgress:
    """User progress tracking."""
    user_id: str
    tutorial_id: str
    current_step: int
    status: TutorialStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    step_progress: Dict[str, TutorialStatus] = field(default_factory=dict)
    hints_used: List[str] = field(default_factory=list)
    time_spent: int = 0  # minutes


class Tutorial:
    """Complete tutorial with steps and metadata."""

    def __init__(self, metadata: TutorialMetadata, steps: List[TutorialStep]):
        self.metadata = metadata
        self.steps = steps

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tutorial':
        """Create tutorial from dictionary."""
        metadata = TutorialMetadata(
            tutorial_id=data['metadata']['tutorial_id'],
            title=data['metadata']['title'],
            description=data['metadata']['description'],
            difficulty=DifficultyLevel(data['metadata']['difficulty']),
            estimated_time=data['metadata']['estimated_time'],
            prerequisites=data['metadata']['prerequisites'],
            learning_objectives=data['metadata']['learning_objectives'],
            tags=data['metadata']['tags'],
            version=data['metadata'].get('version', '1.0'),
            author=data['metadata'].get('author', 'LeanVibe Team')
        )

        steps = []
        for step_data in data['steps']:
            step = TutorialStep(
                step_id=step_data['step_id'],
                title=step_data['title'],
                description=step_data['description'],
                instructions=step_data['instructions'],
                code_examples=step_data['code_examples'],
                validation_command=step_data.get('validation_command'),
                expected_output=step_data.get('expected_output'),
                hints=step_data.get('hints', []),
                estimated_time=step_data.get('estimated_time', 5),
                dependencies=step_data.get('dependencies', [])
            )
            steps.append(step)

        return cls(metadata, steps)

    def to_dict(self) -> Dict[str, Any]:
        """Convert tutorial to dictionary."""
        return {
            "metadata": {
                "tutorial_id": self.metadata.tutorial_id,
                "title": self.metadata.title,
                "description": self.metadata.description,
                "difficulty": self.metadata.difficulty.value,
                "estimated_time": self.metadata.estimated_time,
                "prerequisites": self.metadata.prerequisites,
                "learning_objectives": self.metadata.learning_objectives,
                "tags": self.metadata.tags,
                "version": self.metadata.version,
                "author": self.metadata.author
            },
            "steps": [
                {
                    "step_id": step.step_id,
                    "title": step.title,
                    "description": step.description,
                    "instructions": step.instructions,
                    "code_examples": step.code_examples,
                    "validation_command": step.validation_command,
                    "expected_output": step.expected_output,
                    "hints": step.hints,
                    "estimated_time": step.estimated_time
                }
                for step in self.steps
            ]
        }


class TutorialManager:
    """Main tutorial management system."""

    def __init__(self, tutorial_path: str = "tutorials"):
        self.tutorial_path = tutorial_path
        self.tutorials: Dict[str, Tutorial] = {}
        self.user_progress: Dict[str, Dict[str, UserProgress]] = {}
        self.load_tutorials()

    def load_tutorials(self):
        """Load all available tutorials."""
        tutorial_dir = os.path.join(self.tutorial_path, "content")
        if not os.path.exists(tutorial_dir):
            os.makedirs(tutorial_dir, exist_ok=True)
            return

        for filename in os.listdir(tutorial_dir):
            if filename.endswith('.json'):
                tutorial_file = os.path.join(tutorial_dir, filename)
                try:
                    with open(tutorial_file, 'r') as f:
                        tutorial_data = json.load(f)
                        tutorial = Tutorial.from_dict(tutorial_data)
                        self.tutorials[tutorial.metadata.tutorial_id] = tutorial
                except Exception as e:
                    print(f"Error loading tutorial {filename}: {e}")

    def get_tutorial(self, tutorial_id: str) -> Optional[Tutorial]:
        """Get tutorial by ID."""
        return self.tutorials.get(tutorial_id)

    def list_tutorials(self, difficulty: Optional[DifficultyLevel] = None) -> List[Tutorial]:
        """List available tutorials, optionally filtered by difficulty."""
        tutorials = list(self.tutorials.values())
        if difficulty:
            tutorials = [t for t in tutorials if t.metadata.difficulty == difficulty]
        return sorted(tutorials, key=lambda t: t.metadata.estimated_time)

    def start_tutorial(self, user_id: str, tutorial_id: str) -> bool:
        """Start a tutorial for a user."""
        tutorial = self.get_tutorial(tutorial_id)
        if not tutorial:
            return False

        if user_id not in self.user_progress:
            self.user_progress[user_id] = {}

        progress = UserProgress(
            user_id=user_id,
            tutorial_id=tutorial_id,
            current_step=0,
            status=TutorialStatus.IN_PROGRESS,
            started_at=datetime.now()
        )

        self.user_progress[user_id][tutorial_id] = progress
        self.save_progress(user_id)
        return True

    def get_progress(self, user_id: str, tutorial_id: str) -> Optional[UserProgress]:
        """Get user progress for a tutorial."""
        return self.user_progress.get(user_id, {}).get(tutorial_id)

    def complete_step(self, user_id: str, tutorial_id: str, step_id: str) -> bool:
        """Mark a step as completed."""
        progress = self.get_progress(user_id, tutorial_id)
        if not progress:
            return False

        progress.step_progress[step_id] = TutorialStatus.COMPLETED
        progress.current_step += 1

        tutorial = self.get_tutorial(tutorial_id)
        if tutorial and progress.current_step >= len(tutorial.steps):
            progress.status = TutorialStatus.COMPLETED
            progress.completed_at = datetime.now()

        self.save_progress(user_id)
        return True

    def save_progress(self, user_id: str) -> None:
        """Save user progress to file."""
        progress_dir = os.path.join(self.tutorial_path, "progress")
        os.makedirs(progress_dir, exist_ok=True)

        progress_file = os.path.join(progress_dir, f"{user_id}.json")

        progress_data = {}
        for tutorial_id, progress in self.user_progress.get(user_id, {}).items():
            progress_data[tutorial_id] = {
                "user_id": progress.user_id,
                "tutorial_id": progress.tutorial_id,
                "current_step": progress.current_step,
                "status": progress.status.value,
                "started_at": progress.started_at.isoformat(),
                "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
                "step_progress": {k: v.value for k, v in progress.step_progress.items()},
                "hints_used": progress.hints_used,
                "time_spent": progress.time_spent
            }

        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
