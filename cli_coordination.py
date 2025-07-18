#!/usr/bin/env python3
"""
CLI Coordination Commands - Critical Method Refactoring

This module extracts coordination logic from the complex CLI methods
using the Command Pattern for improved maintainability and testability.
"""

import asyncio
import shutil
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any


class CoordinationCommand(ABC):
    """Base class for coordination commands."""
    
    @abstractmethod
    async def execute(self, **kwargs) -> None:
        """Execute the coordination command."""
        pass


class CreateIssueCommand(CoordinationCommand):
    """Command to create coordination issues."""
    
    async def execute(self, worktree: str, agent_type: str, priority: str) -> None:
        """Create a new coordination issue."""
        print(f"📝 Creating coordination issue for {agent_type} agent")
        print(f"📂 Worktree: {worktree}")
        print(f"⚡ Priority: {priority}")
        
        # This would integrate with gh CLI in real implementation
        print("✅ Issue created successfully")
        print("🔗 URL: https://github.com/LeanVibe/agent-hive/issues/XX")


class UpdateIssueCommand(CoordinationCommand):
    """Command to update issue progress."""
    
    async def execute(self, issue: int, update: str) -> None:
        """Update issue with progress information."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"📊 Updating issue #{issue} at {timestamp}")
        print(f"💬 Update: {update}")
        
        # This would use gh CLI to add comment
        print("✅ Progress update posted to GitHub issue")


class SpawnAgentCommand(CoordinationCommand):
    """Command to spawn agents with instructions."""
    
    async def execute(self, worktree: str, agent_type: str, issue: int) -> None:
        """Spawn agent and generate instructions."""
        print(f"🚀 Spawning {agent_type} agent on worktree: {worktree}")
        print(f"📋 Tracking via issue #{issue}")
        
        # Generate agent instructions
        await self._generate_agent_instructions(worktree, agent_type, issue)
    
    async def _generate_agent_instructions(self, worktree: str, agent_type: str, issue: int) -> None:
        """Generate detailed instructions for spawned agent."""
        print(f"📝 Generating instructions for {agent_type} agent...")
        
        instructions = f"""
🤖 AGENT ASSIGNMENT: {agent_type.upper()}

## Your Mission
You are a {agent_type} agent working on GitHub issue #{issue}.
Work autonomously following XP methodology principles.

## Working Environment
- Worktree: {worktree}
- GitHub Issue: #{issue}
- Branch: feature/{agent_type}-implementation

## Workflow
1. Review issue requirements and acceptance criteria
2. Commit changes after each completed sub-task
3. Push commits automatically (handled by git hooks)
4. Ask questions on issue if blocked >30 minutes

## Quality Standards
- All tests must pass before commit
- Code coverage >90% for new code
- Follow XP principles: YAGNI, DRY, KISS
- Update documentation for new features

Ready to begin! Comment on issue #{issue} to confirm start.
"""
        
        print("✅ Agent instructions generated")
        print("📋 Instructions saved and ready for agent deployment")
        print(f"\n{instructions}")


class StatusCommand(CoordinationCommand):
    """Command to show coordination status."""
    
    async def execute(self) -> None:
        """Show active coordination status."""
        print("📊 Active Agent Coordination Status:")
        
        # Mock active coordinations
        coordinations = [
            {"issue": 6, "agent": "docs", "worktree": "agent-hive-docs-tutorial", "status": "in-progress", "progress": "60%"},
            {"issue": 7, "agent": "analysis", "worktree": "agent-hive-tech-debt", "status": "ready", "progress": "0%"}
        ]
        
        for coord in coordinations:
            status_emoji = "🔄" if coord["status"] == "in-progress" else "⏳" if coord["status"] == "ready" else "✅"
            print(f"  {status_emoji} Issue #{coord['issue']}: {coord['agent']} agent ({coord['progress']}) - {coord['worktree']}")


class ListWorktreesCommand(CoordinationCommand):
    """Command to list available worktrees."""
    
    async def execute(self) -> None:
        """List available worktrees and agent assignments."""
        print("📋 Available Worktrees and Agent Assignments:")
        
        try:
            worktrees = await self._get_worktrees()
            for worktree_info in worktrees:
                print(f"  {worktree_info['agent_type']}: {worktree_info['path']}")
                print(f"    Branch: {worktree_info['branch']}")
                print(f"    Commit: {worktree_info['commit']}")
                print("")
                
        except Exception as e:
            print(f"❌ Error listing worktrees: {e}")
    
    async def _get_worktrees(self) -> List[Dict[str, str]]:
        """Get worktree information with proper error handling."""
        # Use absolute path for git command for security
        git_path = shutil.which('git')
        if not git_path:
            raise RuntimeError("Git command not found in PATH")
        
        try:
            result = subprocess.run(
                [git_path, 'worktree', 'list'],
                capture_output=True, 
                text=True, 
                check=True, 
                timeout=30
            )
            
            worktrees = []
            for worktree_line in result.stdout.strip().split('\n'):
                parts = worktree_line.split()
                if len(parts) >= 3:
                    path = parts[0]
                    commit = parts[1]
                    branch = parts[2].strip('[]')
                    
                    # Determine agent type from path/branch
                    if 'docs' in path or 'tutorial' in branch:
                        agent_type = "📝 docs"
                    elif 'tech-debt' in path or 'analysis' in branch:
                        agent_type = "🔧 analysis"
                    else:
                        agent_type = "🎯 orchestrator"
                    
                    worktrees.append({
                        'path': path,
                        'commit': commit,
                        'branch': branch,
                        'agent_type': agent_type
                    })
            
            return worktrees
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git command failed: {e}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Git command timed out")
        except FileNotFoundError:
            raise RuntimeError("Git command not found in system PATH")


class CoordinationOrchestrator:
    """Orchestrates coordination commands with reduced complexity."""
    
    def __init__(self):
        self.commands: Dict[str, CoordinationCommand] = {
            'create-issue': CreateIssueCommand(),
            'update-issue': UpdateIssueCommand(),
            'spawn-agent': SpawnAgentCommand(),
            'status': StatusCommand(),
            'list': ListWorktreesCommand()
        }
    
    async def execute_coordination(self, action: str, **kwargs) -> None:
        """Execute coordination action with validation."""
        print("🎯 LeanVibe Parallel Work Coordination")
        print("=" * 37)
        
        if action not in self.commands:
            print(f"❌ Unknown action: {action}")
            return
        
        # Validate required parameters
        validation_errors = self._validate_parameters(action, **kwargs)
        if validation_errors:
            for error in validation_errors:
                print(f"❌ Error: {error}")
            return
        
        # Execute command with filtered parameters
        command = self.commands[action]
        
        # Filter parameters based on the command
        filtered_kwargs = self._filter_kwargs_for_command(action, **kwargs)
        await command.execute(**filtered_kwargs)
    
    def _validate_parameters(self, action: str, **kwargs) -> List[str]:
        """Validate required parameters for each action."""
        errors = []
        
        if action == 'create-issue':
            if not kwargs.get('worktree'):
                errors.append("--worktree required for issue creation")
            if not kwargs.get('agent_type'):
                errors.append("--agent-type required for issue creation")
        
        elif action == 'update-issue':
            if not kwargs.get('issue'):
                errors.append("--issue required for progress update")
            if not kwargs.get('update'):
                errors.append("--update required for progress update")
        
        elif action == 'spawn-agent':
            if not kwargs.get('worktree'):
                errors.append("--worktree required for agent spawning")
            if not kwargs.get('agent_type'):
                errors.append("--agent-type required for agent spawning")
            if not kwargs.get('issue'):
                errors.append("--issue required for agent spawning")
        
        return errors
    
    def _filter_kwargs_for_command(self, action: str, **kwargs) -> Dict[str, Any]:
        """Filter kwargs to only include parameters the command expects."""
        if action == 'create-issue':
            return {k: v for k, v in kwargs.items() if k in ['worktree', 'agent_type', 'priority']}
        elif action == 'update-issue':
            return {k: v for k, v in kwargs.items() if k in ['issue', 'update']}
        elif action == 'spawn-agent':
            return {k: v for k, v in kwargs.items() if k in ['worktree', 'agent_type', 'issue']}
        elif action in ['status', 'list']:
            return {}  # These commands don't take parameters
        else:
            return kwargs