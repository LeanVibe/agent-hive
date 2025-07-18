#!/usr/bin/env python3
"""
Secure Git Operations Module

Provides secure, validated git operations for the development system.
All operations are sanitized and validated to prevent command injection.
"""

import subprocess
import shlex
import re
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class GitOperationError(Exception):
    """Git operation specific error"""
    pass

class SecurityError(Exception):
    """Security validation error"""
    pass

@dataclass
class GitConfig:
    """Git operation configuration"""
    timeout: int = 30
    max_retries: int = 3
    allowed_commands: List[str] = None
    safe_mode: bool = True
    
    def __post_init__(self):
        if self.allowed_commands is None:
            self.allowed_commands = [
                'status', 'log', 'diff', 'show', 'branch', 'rev-list', 
                'rev-parse', 'merge-base', 'merge-tree', 'checkout', 
                'add', 'commit', 'push', 'cherry-pick', 'config'
            ]

class SecureGitOperations:
    """Secure git operations with input validation and sanitization"""
    
    def __init__(self, repo_path: Union[str, Path], config: GitConfig = None):
        self.repo_path = Path(repo_path).resolve()
        self.config = config or GitConfig()
        self._validate_repository()
        
    def _validate_repository(self):
        """Validate that the path is a valid git repository"""
        if not self.repo_path.exists():
            raise GitOperationError(f"Repository path does not exist: {self.repo_path}")
        
        if not self.repo_path.is_dir():
            raise GitOperationError(f"Repository path is not a directory: {self.repo_path}")
        
        # Check if it's a git repository
        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            raise GitOperationError(f"Not a git repository: {self.repo_path}")
        
        # Ensure we're within allowed paths
        if self.config.safe_mode:
            self._validate_safe_path()
    
    def _validate_safe_path(self):
        """Validate that the repository path is safe"""
        # Prevent path traversal attacks
        try:
            # Check if path contains suspicious patterns
            path_str = str(self.repo_path)
            if any(pattern in path_str for pattern in ['..', '~', '$', '`', '|', ';', '&']):
                raise SecurityError(f"Unsafe path detected: {path_str}")
            
            # Ensure path is absolute and normalized
            if not self.repo_path.is_absolute():
                raise SecurityError(f"Repository path must be absolute: {self.repo_path}")
                
        except Exception as e:
            raise SecurityError(f"Path validation failed: {e}")
    
    def _validate_git_command(self, command: str) -> str:
        """Validate and sanitize git command"""
        if not command or not isinstance(command, str):
            raise SecurityError("Invalid git command")
        
        # Check if command is in allowed list
        if command not in self.config.allowed_commands:
            raise SecurityError(f"Git command not allowed: {command}")
        
        # Sanitize command
        sanitized = re.sub(r'[^a-zA-Z0-9\-_]', '', command)
        if sanitized != command:
            raise SecurityError(f"Command contains invalid characters: {command}")
        
        return sanitized
    
    def _validate_git_args(self, args: List[str]) -> List[str]:
        """Validate and sanitize git arguments"""
        if not args:
            return []
        
        sanitized_args = []
        for arg in args:
            if not isinstance(arg, str):
                raise SecurityError(f"Invalid argument type: {type(arg)}")
            
            # Allow git format strings for branch command
            if arg.startswith('--format='):
                # Validate format string separately
                format_content = arg[9:]  # Remove '--format=' prefix
                if not re.match(r'^[a-zA-Z0-9%():\-_\|\ ]+$', format_content):
                    raise SecurityError(f"Invalid format string: {format_content}")
                sanitized_args.append(arg)
                continue
            
            # Check for dangerous patterns (excluding | in format strings)
            if any(pattern in arg for pattern in ['`', '$', ';', '&', '>', '<']):
                raise SecurityError(f"Dangerous characters in argument: {arg}")
            
            # Validate branch/ref names
            if arg.startswith('refs/') or ('/' in arg and not arg.startswith('-')):
                if not re.match(r'^[a-zA-Z0-9/_\-\.]+$', arg):
                    raise SecurityError(f"Invalid ref/branch name: {arg}")
            
            sanitized_args.append(arg)
        
        return sanitized_args
    
    def _execute_git_command(self, command: str, args: List[str] = None, 
                           timeout: int = None, capture_output: bool = True) -> subprocess.CompletedProcess:
        """Execute git command with security validation"""
        # Validate inputs
        validated_command = self._validate_git_command(command)
        validated_args = self._validate_git_args(args or [])
        
        # Build command
        cmd = ['git', validated_command] + validated_args
        
        # Use timeout
        timeout = timeout or self.config.timeout
        
        try:
            logger.debug(f"Executing git command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=False  # Don't raise exception on non-zero exit
            )
            
            logger.debug(f"Git command completed with exit code: {result.returncode}")
            return result
            
        except subprocess.TimeoutExpired:
            raise GitOperationError(f"Git command timed out after {timeout} seconds")
        except Exception as e:
            raise GitOperationError(f"Git command failed: {e}")
    
    def get_branch_info(self, format_string: str = "%(refname:short)|%(committerdate:iso)|%(subject)") -> List[Dict[str, str]]:
        """Get branch information with validated format string"""
        # Validate format string
        if not re.match(r'^[a-zA-Z0-9%():\-_\|\ ]+$', format_string):
            raise SecurityError(f"Invalid format string: {format_string}")
        
        result = self._execute_git_command('branch', ['-a', f'--format={format_string}'])
        
        if result.returncode != 0:
            raise GitOperationError(f"Failed to get branch info: {result.stderr}")
        
        branches = []
        for line in result.stdout.strip().split('\n'):
            if line and '|' in line:
                parts = line.split('|', 2)
                if len(parts) >= 3:
                    branches.append({
                        'name': parts[0].strip(),
                        'last_commit': parts[1].strip(),
                        'subject': parts[2].strip()
                    })
        
        return branches
    
    def get_commit_count(self, rev_range: str) -> int:
        """Get commit count for a revision range"""
        # Validate revision range
        if not re.match(r'^[a-zA-Z0-9/_\-\.]+\.\.[a-zA-Z0-9/_\-\.]+$', rev_range):
            raise SecurityError(f"Invalid revision range: {rev_range}")
        
        result = self._execute_git_command('rev-list', ['--count', rev_range])
        
        if result.returncode != 0:
            raise GitOperationError(f"Failed to get commit count: {result.stderr}")
        
        try:
            return int(result.stdout.strip())
        except ValueError:
            raise GitOperationError(f"Invalid commit count output: {result.stdout}")
    
    def get_diff_stats(self, rev_range: str) -> str:
        """Get diff statistics for a revision range"""
        # Validate revision range
        if not re.match(r'^[a-zA-Z0-9/_\-\.]+\.\.[a-zA-Z0-9/_\-\.]+$', rev_range):
            raise SecurityError(f"Invalid revision range: {rev_range}")
        
        result = self._execute_git_command('diff', ['--stat', rev_range])
        
        if result.returncode != 0:
            raise GitOperationError(f"Failed to get diff stats: {result.stderr}")
        
        return result.stdout.strip()
    
    def get_file_content(self, branch: str, file_path: str) -> Optional[str]:
        """Get file content from a specific branch"""
        # Validate branch name
        if not re.match(r'^[a-zA-Z0-9/_\-\.]+$', branch):
            raise SecurityError(f"Invalid branch name: {branch}")
        
        # Validate file path
        if not re.match(r'^[a-zA-Z0-9/_\-\.]+$', file_path):
            raise SecurityError(f"Invalid file path: {file_path}")
        
        # Prevent path traversal
        if '..' in file_path or file_path.startswith('/'):
            raise SecurityError(f"Path traversal attempt detected: {file_path}")
        
        result = self._execute_git_command('show', [f'{branch}:{file_path}'])
        
        if result.returncode != 0:
            if 'does not exist' in result.stderr or 'exists on disk' in result.stderr:
                return None
            raise GitOperationError(f"Failed to get file content: {result.stderr}")
        
        return result.stdout
    
    def checkout_branch(self, branch: str) -> bool:
        """Checkout a branch safely"""
        # Validate branch name
        if not re.match(r'^[a-zA-Z0-9/_\-\.]+$', branch):
            raise SecurityError(f"Invalid branch name: {branch}")
        
        result = self._execute_git_command('checkout', [branch])
        
        if result.returncode != 0:
            raise GitOperationError(f"Failed to checkout branch: {result.stderr}")
        
        return True
    
    def get_current_branch(self) -> str:
        """Get current branch name"""
        result = self._execute_git_command('rev-parse', ['--abbrev-ref', 'HEAD'])
        
        if result.returncode != 0:
            raise GitOperationError(f"Failed to get current branch: {result.stderr}")
        
        return result.stdout.strip()
    
    def add_file(self, file_path: str) -> bool:
        """Add file to git index"""
        # Validate file path
        if not re.match(r'^[a-zA-Z0-9/_\-\.]+$', file_path):
            raise SecurityError(f"Invalid file path: {file_path}")
        
        # Prevent path traversal
        if '..' in file_path or file_path.startswith('/'):
            raise SecurityError(f"Path traversal attempt detected: {file_path}")
        
        result = self._execute_git_command('add', [file_path])
        
        if result.returncode != 0:
            raise GitOperationError(f"Failed to add file: {result.stderr}")
        
        return True
    
    def commit_changes(self, message: str) -> bool:
        """Commit changes with validated message"""
        # Validate commit message
        if not message or len(message) > 1000:
            raise SecurityError("Invalid commit message")
        
        # Sanitize commit message - remove dangerous characters
        sanitized_message = re.sub(r'[`$;&><()]', '', message)
        
        # Use a safer approach - write message to temporary file if needed
        if len(sanitized_message) > 50:  # For long messages
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(sanitized_message)
                temp_file = f.name
            
            try:
                result = self._execute_git_command('commit', ['-F', temp_file])
            finally:
                os.unlink(temp_file)
        else:
            result = self._execute_git_command('commit', ['-m', sanitized_message])
        
        if result.returncode != 0:
            if 'nothing to commit' in result.stdout:
                return False
            raise GitOperationError(f"Failed to commit changes: {result.stderr}")
        
        return True
    
    def push_branch(self, branch: str, remote: str = 'origin') -> bool:
        """Push branch to remote"""
        # Validate branch and remote names
        if not re.match(r'^[a-zA-Z0-9/_\-\.]+$', branch):
            raise SecurityError(f"Invalid branch name: {branch}")
        
        if not re.match(r'^[a-zA-Z0-9/_\-\.]+$', remote):
            raise SecurityError(f"Invalid remote name: {remote}")
        
        result = self._execute_git_command('push', [remote, branch])
        
        if result.returncode != 0:
            raise GitOperationError(f"Failed to push branch: {result.stderr}")
        
        return True
    
    def get_merge_base(self, branch1: str, branch2: str) -> str:
        """Get merge base between two branches"""
        # Validate branch names
        for branch in [branch1, branch2]:
            if not re.match(r'^[a-zA-Z0-9/_\-\.]+$', branch):
                raise SecurityError(f"Invalid branch name: {branch}")
        
        result = self._execute_git_command('merge-base', [branch1, branch2])
        
        if result.returncode != 0:
            raise GitOperationError(f"Failed to get merge base: {result.stderr}")
        
        return result.stdout.strip()
    
    def check_merge_conflicts(self, branch1: str, branch2: str) -> bool:
        """Check if there are merge conflicts between branches"""
        try:
            merge_base = self.get_merge_base(branch1, branch2)
            result = self._execute_git_command('merge-tree', [merge_base, branch1, branch2])
            return bool(result.stdout.strip())
        except GitOperationError:
            return True  # Assume conflicts if we can't determine
    
    def get_status(self) -> str:
        """Get git status"""
        result = self._execute_git_command('status', ['--porcelain'])
        
        if result.returncode != 0:
            raise GitOperationError(f"Failed to get status: {result.stderr}")
        
        return result.stdout.strip()


class SecureGitOperationsFactory:
    """Factory for creating secure git operations instances"""
    
    @staticmethod
    def create_for_repo(repo_path: Union[str, Path], safe_mode: bool = True) -> SecureGitOperations:
        """Create a secure git operations instance for a repository"""
        config = GitConfig(safe_mode=safe_mode)
        return SecureGitOperations(repo_path, config)
    
    @staticmethod
    def create_with_config(repo_path: Union[str, Path], config: GitConfig) -> SecureGitOperations:
        """Create a secure git operations instance with custom configuration"""
        return SecureGitOperations(repo_path, config)


def validate_git_environment() -> Dict[str, Any]:
    """Validate git environment and return status"""
    try:
        # Check if git is available
        result = subprocess.run(['git', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return {'status': 'error', 'message': 'Git not found'}
        
        return {
            'status': 'success',
            'git_version': result.stdout.strip(),
            'security_mode': 'enabled'
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


if __name__ == "__main__":
    # Test the security validation
    try:
        git_ops = SecureGitOperations(".")
        print("✅ Git operations initialized successfully")
        
        # Test basic operations
        branches = git_ops.get_branch_info()
        print(f"📊 Found {len(branches)} branches")
        
        current_branch = git_ops.get_current_branch()
        print(f"🌿 Current branch: {current_branch}")
        
    except Exception as e:
        print(f"❌ Error: {e}")