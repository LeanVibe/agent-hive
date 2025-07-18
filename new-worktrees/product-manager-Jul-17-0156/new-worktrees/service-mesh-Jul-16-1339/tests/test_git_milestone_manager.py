"""
Unit tests for GitMilestoneManager - Git milestone and progress tracking system.

Tests the comprehensive git milestone management system including
automatic milestone creation, commit recommendations, and progress tracking.
"""

import asyncio
import pytest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import json
import sys

# Add the .claude directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / '.claude'))

from state.git_milestone_manager import GitMilestoneManager, GitMilestone, CommitRecommendation


class TestGitMilestone:
    """Test suite for GitMilestone dataclass."""

    def test_git_milestone_creation(self):
        """Test GitMilestone creation with all fields."""
        now = datetime.now()
        milestone = GitMilestone(
            milestone_id="test-milestone",
            title="Test Milestone",
            description="Test description",
            commit_hash="abc123",
            branch="main",
            created_at=now,
            tags=["tag1", "tag2"],
            metrics={"commits": 10, "quality": 0.8},
            state_snapshot={"test": "data"}
        )

        assert milestone.milestone_id == "test-milestone"
        assert milestone.title == "Test Milestone"
        assert milestone.description == "Test description"
        assert milestone.commit_hash == "abc123"
        assert milestone.branch == "main"
        assert milestone.created_at == now
        assert milestone.tags == ["tag1", "tag2"]
        assert milestone.metrics == {"commits": 10, "quality": 0.8}
        assert milestone.state_snapshot == {"test": "data"}


class TestCommitRecommendation:
    """Test suite for CommitRecommendation dataclass."""

    def test_commit_recommendation_creation(self):
        """Test CommitRecommendation creation with all fields."""
        recommendation = CommitRecommendation(
            should_commit=True,
            confidence=0.85,
            reason="High quality code with tests",
            suggested_message="feat: add new feature",
            files_to_stage=["file1.py", "file2.py"],
            quality_score=0.9
        )

        assert recommendation.should_commit is True
        assert recommendation.confidence == 0.85
        assert recommendation.reason == "High quality code with tests"
        assert recommendation.suggested_message == "feat: add new feature"
        assert recommendation.files_to_stage == ["file1.py", "file2.py"]
        assert recommendation.quality_score == 0.9


class TestGitMilestoneManager:
    """Test suite for GitMilestoneManager functionality."""

    @pytest.fixture
    def temp_git_repo(self):
        """Create temporary git repository for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Initialize git repository
            subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, capture_output=True)

            # Create initial commit
            (repo_path / "README.md").write_text("# Test Repository")
            subprocess.run(["git", "add", "README.md"], cwd=repo_path, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, capture_output=True)

            yield repo_path

    @pytest.fixture
    def mock_state_manager(self):
        """Create mock StateManager for testing."""
        state_manager = Mock()

        # Mock system state
        system_state = Mock()
        system_state.total_tasks = 100
        system_state.completed_tasks = 80
        system_state.active_agents = 2
        system_state.quality_score = 0.85
        system_state.average_context_usage = 0.6

        state_manager.get_system_state = AsyncMock(return_value=system_state)
        state_manager.create_checkpoint = AsyncMock(return_value="checkpoint-123")

        # Mock quality gate
        quality_gate = Mock()
        quality_gate.evaluate = Mock(return_value={'quality_score': 0.8})
        state_manager.quality_gate = quality_gate

        return state_manager

    @pytest.fixture
    def git_manager(self, temp_git_repo, mock_state_manager):
        """Create GitMilestoneManager instance with mocked components."""
        with patch('state.git_milestone_manager.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key, default: {
                'git.milestone.min_commits': 5,
                'git.milestone.max_days': 7,
                'git.milestone.min_quality_score': 0.8,
                'git.milestone.min_completion_rate': 0.8,
                'git.milestone.min_lines_added': 100,
                'git.commit.min_quality_score': 0.6
            }.get(key, default)

            manager = GitMilestoneManager(
                state_manager=mock_state_manager,
                repo_path=str(temp_git_repo)
            )
            yield manager

    def test_init_with_valid_repo(self, temp_git_repo):
        """Test GitMilestoneManager initialization with valid git repository."""
        manager = GitMilestoneManager(repo_path=str(temp_git_repo))

        assert manager.repo_path == temp_git_repo
        assert manager.state_manager is None

    def test_init_with_invalid_repo(self):
        """Test GitMilestoneManager initialization with invalid repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="is not a git repository"):
                GitMilestoneManager(repo_path=temp_dir)

    def test_is_git_repo_valid(self, temp_git_repo):
        """Test _is_git_repo method with valid repository."""
        manager = GitMilestoneManager(repo_path=str(temp_git_repo))

        assert manager._is_git_repo() is True

    def test_is_git_repo_invalid(self):
        """Test _is_git_repo method with invalid repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = GitMilestoneManager.__new__(GitMilestoneManager)
            manager.repo_path = Path(temp_dir)

            assert manager._is_git_repo() is False

    def test_get_git_status(self, git_manager, temp_git_repo):
        """Test _get_git_status method."""
        # Create test files
        (temp_git_repo / "test.py").write_text("def test(): pass")
        (temp_git_repo / "new.py").write_text("def new(): pass")

        # Stage one file
        subprocess.run(["git", "add", "test.py"], cwd=temp_git_repo)

        status = git_manager._get_git_status()

        assert isinstance(status, dict)
        assert 'modified_files' in status
        assert 'added_files' in status
        assert 'untracked_files' in status
        assert 'commit_count' in status
        assert 'has_changes' in status

        assert status['has_changes'] is True
        assert status['commit_count'] >= 1

    def test_get_current_commit(self, git_manager):
        """Test _get_current_commit method."""
        commit_hash = git_manager._get_current_commit()

        assert isinstance(commit_hash, str)
        assert len(commit_hash) >= 7  # Short hash is at least 7 chars

    def test_get_current_branch(self, git_manager):
        """Test _get_current_branch method."""
        branch = git_manager._get_current_branch()

        assert isinstance(branch, str)
        assert branch in ['main', 'master']  # Default branch names

    def test_calculate_milestone_metrics(self, git_manager, mock_state_manager):
        """Test _calculate_milestone_metrics method."""
        git_status = {
            'commit_count': 50,
            'has_changes': True
        }

        system_state = mock_state_manager.get_system_state()

        metrics = git_manager._calculate_milestone_metrics(git_status, system_state)

        assert isinstance(metrics, dict)
        assert 'commits_since_last_milestone' in metrics
        assert 'days_since_last_milestone' in metrics
        assert 'quality_score' in metrics
        assert 'completion_rate' in metrics
        assert 'active_agents' in metrics

        assert metrics['quality_score'] == 0.85
        assert metrics['completion_rate'] == 0.8
        assert metrics['active_agents'] == 2

    def test_calculate_commit_metrics(self, git_manager):
        """Test _calculate_commit_metrics method."""
        files = [
            "src/main.py",
            "tests/test_main.py",
            "docs/README.md",
            "config.json"
        ]

        metrics = git_manager._calculate_commit_metrics(files)

        assert isinstance(metrics, dict)
        assert metrics['file_count'] == 4
        assert metrics['test_files'] == 1
        assert metrics['source_files'] == 1
        assert metrics['config_files'] == 1
        assert metrics['doc_files'] == 1
        assert metrics['has_breaking_changes'] is False
        assert 'complexity_score' in metrics

    def test_should_commit_high_quality(self, git_manager):
        """Test _should_commit method with high quality code."""
        commit_metrics = {
            'file_count': 3,
            'source_files': 2,
            'test_files': 1,
            'config_files': 0,
            'doc_files': 0,
            'has_breaking_changes': False
        }

        should_commit = git_manager._should_commit(commit_metrics, 0.8)

        assert should_commit is True

    def test_should_commit_low_quality(self, git_manager):
        """Test _should_commit method with low quality code."""
        commit_metrics = {
            'file_count': 1,
            'source_files': 1,
            'test_files': 0,
            'config_files': 0,
            'doc_files': 0,
            'has_breaking_changes': False
        }

        should_commit = git_manager._should_commit(commit_metrics, 0.4)

        assert should_commit is False

    def test_should_commit_no_files(self, git_manager):
        """Test _should_commit method with no files."""
        commit_metrics = {
            'file_count': 0,
            'source_files': 0,
            'test_files': 0,
            'config_files': 0,
            'doc_files': 0,
            'has_breaking_changes': False
        }

        should_commit = git_manager._should_commit(commit_metrics, 0.8)

        assert should_commit is False

    def test_should_commit_only_docs(self, git_manager):
        """Test _should_commit method with only documentation files."""
        commit_metrics = {
            'file_count': 2,
            'source_files': 0,
            'test_files': 0,
            'config_files': 0,
            'doc_files': 2,
            'has_breaking_changes': False
        }

        should_commit = git_manager._should_commit(commit_metrics, 0.7)

        assert should_commit is True

    def test_calculate_commit_confidence(self, git_manager):
        """Test _calculate_commit_confidence method."""
        commit_metrics = {
            'test_files': 2,
            'source_files': 3,
            'has_breaking_changes': False,
            'complexity_score': 0.5
        }

        confidence = git_manager._calculate_commit_confidence(commit_metrics, 0.8)

        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be above base confidence

    def test_calculate_commit_confidence_breaking_changes(self, git_manager):
        """Test _calculate_commit_confidence method with breaking changes."""
        commit_metrics = {
            'test_files': 1,
            'source_files': 1,
            'has_breaking_changes': True,
            'complexity_score': 0.3
        }

        confidence = git_manager._calculate_commit_confidence(commit_metrics, 0.8)

        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        # Should be lower due to breaking changes

    def test_generate_commit_reason_should_commit(self, git_manager):
        """Test _generate_commit_reason method when should commit."""
        commit_metrics = {
            'test_files': 2,
            'source_files': 1,
            'doc_files': 0,
            'file_count': 3
        }

        reason = git_manager._generate_commit_reason(commit_metrics, 0.85, True)

        assert isinstance(reason, str)
        assert "Ready to commit" in reason
        assert "test files" in reason
        assert "source files" in reason
        assert "high quality score" in reason

    def test_generate_commit_reason_should_not_commit(self, git_manager):
        """Test _generate_commit_reason method when should not commit."""
        commit_metrics = {
            'file_count': 1,
            'source_files': 1
        }

        reason = git_manager._generate_commit_reason(commit_metrics, 0.4, False)

        assert isinstance(reason, str)
        assert "Quality score too low" in reason

    def test_generate_commit_message(self, git_manager):
        """Test _generate_commit_message method."""
        files = ["src/main.py", "tests/test_main.py"]
        commit_metrics = {
            'file_count': 2,
            'test_files': 1,
            'source_files': 1,
            'doc_files': 0,
            'config_files': 0
        }

        message = git_manager._generate_commit_message(files, commit_metrics)

        assert isinstance(message, str)
        assert "feat:" in message
        assert "🤖 Generated with [Claude Code]" in message
        assert "Co-Authored-By: Claude" in message

    def test_generate_commit_message_single_file(self, git_manager):
        """Test _generate_commit_message method with single file."""
        files = ["README.md"]
        commit_metrics = {
            'file_count': 1,
            'test_files': 0,
            'source_files': 0,
            'doc_files': 1,
            'config_files': 0
        }

        message = git_manager._generate_commit_message(files, commit_metrics)

        assert isinstance(message, str)
        assert "docs:" in message
        assert "update README.md" in message

    def test_get_files_to_stage(self, git_manager):
        """Test _get_files_to_stage method."""
        files = ["file1.py", "file2.py", "file3.py"]
        commit_metrics = {'file_count': 3}

        files_to_stage = git_manager._get_files_to_stage(files, commit_metrics)

        assert files_to_stage == files

    def test_generate_milestone_title(self, git_manager):
        """Test _generate_milestone_title method."""
        title = git_manager._generate_milestone_title()

        assert isinstance(title, str)
        assert "Development Milestone" in title
        assert str(datetime.now().year) in title

    @pytest.mark.asyncio
    async def test_generate_milestone_description(self, git_manager):
        """Test _generate_milestone_description method."""
        description = await git_manager._generate_milestone_description()

        assert isinstance(description, str)
        assert "Automatic milestone" in description
        assert "Recent commits" in description
        assert "System State" in description

    def test_create_git_tag_success(self, git_manager):
        """Test _create_git_tag method with successful tag creation."""
        success = git_manager._create_git_tag("test-tag", "Test tag message")

        assert success is True

        # Verify tag was created
        result = subprocess.run(
            ["git", "tag", "-l", "test-tag"],
            cwd=git_manager.repo_path,
            capture_output=True,
            text=True
        )
        assert "test-tag" in result.stdout

    @pytest.mark.asyncio
    async def test_save_milestone_to_state(self, git_manager, mock_state_manager):
        """Test _save_milestone_to_state method."""
        milestone = GitMilestone(
            milestone_id="test-milestone",
            title="Test Milestone",
            description="Test description",
            commit_hash="abc123",
            branch="main",
            created_at=datetime.now(),
            tags=["tag1"],
            metrics={"test": 1},
            state_snapshot={"test": "data"}
        )

        await git_manager._save_milestone_to_state(milestone)

        # Verify StateManager was called
        mock_state_manager.create_checkpoint.assert_called_once()
        args, kwargs = mock_state_manager.create_checkpoint.call_args
        assert args[0] == 'git_milestone'
        assert 'state_data' in kwargs
        assert kwargs['state_data']['type'] == 'git_milestone'

    @pytest.mark.asyncio
    async def test_should_create_milestone_true(self, git_manager, temp_git_repo):
        """Test should_create_milestone method returning True."""
        # Add some commits to meet threshold
        for i in range(6):
            test_file = temp_git_repo / f"test_{i}.py"
            test_file.write_text(f"def test_{i}(): pass")
            subprocess.run(["git", "add", str(test_file)], cwd=temp_git_repo)
            subprocess.run(["git", "commit", "-m", f"Add test_{i}"], cwd=temp_git_repo)

        should_create, reason, data = await git_manager.should_create_milestone()

        assert should_create is True
        assert isinstance(reason, str)
        assert isinstance(data, dict)
        assert 'metrics' in data
        assert 'system_state' in data
        assert 'git_status' in data

    @pytest.mark.asyncio
    async def test_should_create_milestone_false(self, git_manager):
        """Test should_create_milestone method returning False."""
        should_create, reason, data = await git_manager.should_create_milestone()

        # Should be False for new repo with minimal commits
        assert should_create is False
        assert isinstance(reason, str)
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_create_milestone_success(self, git_manager):
        """Test create_milestone method with successful creation."""
        milestone = await git_manager.create_milestone(
            title="Test Milestone",
            description="Test description",
            tags=["test", "milestone"]
        )

        assert milestone is not None
        assert isinstance(milestone, GitMilestone)
        assert milestone.title == "Test Milestone"
        assert milestone.description == "Test description"
        assert milestone.tags == ["test", "milestone"]
        assert milestone.commit_hash is not None
        assert milestone.branch is not None

    @pytest.mark.asyncio
    async def test_create_milestone_auto_generated(self, git_manager):
        """Test create_milestone method with auto-generated fields."""
        milestone = await git_manager.create_milestone()

        assert milestone is not None
        assert isinstance(milestone, GitMilestone)
        assert "Development Milestone" in milestone.title
        assert "Automatic milestone" in milestone.description
        assert milestone.tags == []

    @pytest.mark.asyncio
    async def test_get_commit_recommendation_should_commit(self, git_manager, temp_git_repo):
        """Test get_commit_recommendation method recommending commit."""
        # Create test files
        (temp_git_repo / "src.py").write_text("def func(): pass")
        (temp_git_repo / "test.py").write_text("def test_func(): pass")

        # Stage files
        subprocess.run(["git", "add", "."], cwd=temp_git_repo)

        recommendation = await git_manager.get_commit_recommendation()

        assert isinstance(recommendation, CommitRecommendation)
        assert recommendation.should_commit is True
        assert 0.0 <= recommendation.confidence <= 1.0
        assert isinstance(recommendation.reason, str)
        assert isinstance(recommendation.suggested_message, str)
        assert isinstance(recommendation.files_to_stage, list)
        assert 0.0 <= recommendation.quality_score <= 1.0

    @pytest.mark.asyncio
    async def test_get_commit_recommendation_should_not_commit(self, git_manager):
        """Test get_commit_recommendation method not recommending commit."""
        # No files changed
        recommendation = await git_manager.get_commit_recommendation([])

        assert isinstance(recommendation, CommitRecommendation)
        assert recommendation.should_commit is False
        assert recommendation.confidence >= 0.0
        assert "No files to commit" in recommendation.reason

    @pytest.mark.asyncio
    async def test_get_commit_recommendation_specific_files(self, git_manager, temp_git_repo):
        """Test get_commit_recommendation method with specific files."""
        # Create test files
        (temp_git_repo / "test1.py").write_text("def test1(): pass")
        (temp_git_repo / "test2.py").write_text("def test2(): pass")

        files = ["test1.py", "test2.py"]
        recommendation = await git_manager.get_commit_recommendation(files)

        assert isinstance(recommendation, CommitRecommendation)
        assert isinstance(recommendation.files_to_stage, list)
        assert set(recommendation.files_to_stage) == set(files)

    @pytest.mark.asyncio
    async def test_get_milestone_history_empty(self, git_manager):
        """Test get_milestone_history method with no milestones."""
        history = await git_manager.get_milestone_history()

        assert isinstance(history, list)
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_get_milestone_history_with_milestones(self, git_manager):
        """Test get_milestone_history method with existing milestones."""
        # Create a milestone first
        milestone = await git_manager.create_milestone("Test Milestone")
        assert milestone is not None

        # Get history
        history = await git_manager.get_milestone_history()

        assert isinstance(history, list)
        assert len(history) >= 1
        assert isinstance(history[0], GitMilestone)
        assert history[0].title == "Test Milestone"

    @pytest.mark.asyncio
    async def test_get_milestone_history_limit(self, git_manager):
        """Test get_milestone_history method with limit parameter."""
        # Create multiple milestones
        for i in range(3):
            await git_manager.create_milestone(f"Milestone {i}")

        # Get limited history
        history = await git_manager.get_milestone_history(limit=2)

        assert isinstance(history, list)
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_progress_summary(self, git_manager):
        """Test get_progress_summary method."""
        # Create a milestone
        await git_manager.create_milestone("Test Milestone")

        summary = await git_manager.get_progress_summary()

        assert isinstance(summary, dict)
        assert 'total_milestones' in summary
        assert 'recent_milestones' in summary
        assert 'current_progress' in summary
        assert 'git_status' in summary
        assert 'system_state' in summary
        assert 'next_milestone_recommendation' in summary

        assert summary['total_milestones'] >= 1
        assert isinstance(summary['recent_milestones'], list)
        assert isinstance(summary['current_progress'], dict)
        assert isinstance(summary['git_status'], dict)
        assert isinstance(summary['next_milestone_recommendation'], tuple)

    @pytest.mark.asyncio
    async def test_error_handling_in_methods(self, git_manager):
        """Test error handling in various methods."""
        # Test with mocked subprocess that fails
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'git')

            # Should not raise exception
            status = git_manager._get_git_status()
            assert isinstance(status, dict)

            # Should handle error gracefully
            recommendation = await git_manager.get_commit_recommendation()
            assert isinstance(recommendation, CommitRecommendation)
            assert recommendation.should_commit is False

    @pytest.mark.asyncio
    async def test_integration_with_state_manager(self, git_manager, mock_state_manager):
        """Test integration with StateManager."""
        # Create milestone
        milestone = await git_manager.create_milestone("Integration Test")

        # Verify StateManager integration
        assert milestone is not None
        mock_state_manager.create_checkpoint.assert_called()

        # Test commit recommendation with quality gate
        recommendation = await git_manager.get_commit_recommendation(["test.py"])

        assert isinstance(recommendation, CommitRecommendation)
        assert recommendation.quality_score == 0.8  # From mocked quality gate

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, git_manager):
        """Test concurrent operations on GitMilestoneManager."""
        # Create multiple milestones concurrently
        tasks = [
            git_manager.create_milestone(f"Concurrent Milestone {i}")
            for i in range(3)
        ]

        results = await asyncio.gather(*tasks)

        # All milestones should be created successfully
        assert all(result is not None for result in results)
        assert all(isinstance(result, GitMilestone) for result in results)

        # All should have unique IDs
        milestone_ids = [m.milestone_id for m in results]
        assert len(set(milestone_ids)) == len(milestone_ids)

    def test_config_integration(self, git_manager):
        """Test configuration integration."""
        # Test that configuration values are used
        commit_metrics = {
            'file_count': 1,
            'source_files': 1,
            'test_files': 0
        }

        # Should use configured min_quality_score (0.6)
        should_commit_high = git_manager._should_commit(commit_metrics, 0.7)
        should_commit_low = git_manager._should_commit(commit_metrics, 0.5)

        assert should_commit_high is True
        assert should_commit_low is False
