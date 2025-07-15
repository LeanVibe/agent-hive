#!/usr/bin/env python3
"""
New Worktree Manager

Creates and manages new worktrees with strict quality gates for future work.
Enforces clean separation between legacy and new development.
"""

import subprocess
import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class NewWorktreeManager:
    """Manages new worktree creation with strict quality gates"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.worktrees_dir = self.base_dir / "new-worktrees"
        self.worktrees_dir.mkdir(exist_ok=True)
        
        # Strict quality gates for new work
        self.quality_gates = {
            "max_pr_size": 500,  # Reduced from 1000
            "required_tests": True,
            "required_docs": True,
            "required_security_review": True,
            "required_performance_check": True,
            "max_complexity": 15,  # Cyclomatic complexity
            "min_coverage": 85,    # Test coverage percentage
        }
    
    def create_new_worktree(self, agent_name: str, task_description: str) -> Dict[str, any]:
        """Create a new worktree for an agent with strict quality gates"""
        try:
            # Create unique branch name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            branch_name = f"new-work/{agent_name}-{timestamp}"
            worktree_path = self.worktrees_dir / f"{agent_name}-{timestamp}"
            
            print(f"🚀 Creating new worktree for {agent_name}")
            print(f"📁 Path: {worktree_path}")
            print(f"🌿 Branch: {branch_name}")
            
            # Create worktree with new branch
            subprocess.run([
                "git", "worktree", "add", "-b", branch_name, str(worktree_path), "main"
            ], check=True)
            
            # Setup quality gates in worktree
            self._setup_quality_gates(worktree_path, agent_name, task_description)
            
            # Create agent-specific CLAUDE.md
            self._create_agent_claude_file(worktree_path, agent_name, task_description)
            
            # Setup pre-commit hooks
            self._setup_pre_commit_hooks(worktree_path)
            
            print(f"✅ New worktree created successfully!")
            
            return {
                "success": True,
                "worktree_path": str(worktree_path),
                "branch_name": branch_name,
                "agent_name": agent_name,
                "task_description": task_description,
                "quality_gates": self.quality_gates
            }
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git command failed: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            print(f"❌ Error creating worktree: {e}")
            return {"success": False, "error": str(e)}
    
    def _setup_quality_gates(self, worktree_path: Path, agent_name: str, task_description: str):
        """Setup quality gates configuration in worktree"""
        quality_config = {
            "agent_name": agent_name,
            "task_description": task_description,
            "created_at": datetime.now().isoformat(),
            "quality_gates": self.quality_gates,
            "enforcement_level": "strict",
            "rules": {
                "pr_size_limit": self.quality_gates["max_pr_size"],
                "test_coverage_required": self.quality_gates["min_coverage"],
                "documentation_required": True,
                "security_review_required": True,
                "performance_check_required": True,
                "code_review_required": True,
                "linting_required": True,
                "type_checking_required": True
            }
        }
        
        quality_file = worktree_path / ".quality-gates.json"
        with open(quality_file, 'w') as f:
            json.dump(quality_config, f, indent=2)
        
        print(f"✅ Quality gates configured: {quality_file}")
    
    def _create_agent_claude_file(self, worktree_path: Path, agent_name: str, task_description: str):
        """Create agent-specific CLAUDE.md file"""
        claude_content = f"""# {agent_name.title()} Agent - New Work Environment

## Task Description
{task_description}

## Quality Gates (STRICT ENFORCEMENT)
- **PR Size Limit**: {self.quality_gates['max_pr_size']} lines maximum
- **Test Coverage**: {self.quality_gates['min_coverage']}% minimum
- **Documentation**: Required for all new features
- **Security Review**: Required for all changes
- **Performance Check**: Required for all optimizations
- **Code Review**: Required from another agent
- **Linting**: Zero warnings/errors allowed
- **Type Checking**: Full type annotations required

## Agent Instructions
1. **ALWAYS** work in small increments (<{self.quality_gates['max_pr_size']} lines per PR)
2. **ALWAYS** write comprehensive tests before implementing features
3. **ALWAYS** update documentation for any new functionality
4. **ALWAYS** run quality gates before committing: `python scripts/run_quality_gates.py`
5. **ALWAYS** request security review for any authentication/authorization changes
6. **NEVER** commit code that doesn't pass all quality gates
7. **NEVER** merge PRs without proper review

## Workflow
1. Plan your work in small, focused tasks
2. Create feature branch: `git checkout -b feature/your-feature`
3. Implement with tests and documentation
4. Run quality gates: `python scripts/run_quality_gates.py`
5. Create PR with detailed description
6. Address all review feedback
7. Merge only after all gates pass

## Communication
- All communication logged to SQLite dashboard
- Use enhanced dashboard for coordination: http://localhost:8002
- Report blockers immediately to orchestrator
- Coordinate with other agents through PM agent

## Success Metrics
- 100% quality gate compliance
- {self.quality_gates['min_coverage']}%+ test coverage
- Zero security vulnerabilities
- Clean, maintainable code
- Comprehensive documentation

Remember: Quality over speed. Better to deliver fewer, high-quality features than many poorly implemented ones.
"""
        
        claude_file = worktree_path / "CLAUDE.md"
        with open(claude_file, 'w') as f:
            f.write(claude_content)
        
        print(f"✅ Agent CLAUDE.md created: {claude_file}")
    
    def _setup_pre_commit_hooks(self, worktree_path: Path):
        """Setup pre-commit hooks for quality enforcement"""
        try:
            # In worktrees, git hooks are in .git file, not .git directory
            git_dir = worktree_path / ".git"
            
            # Check if .git is a file (worktree) or directory (main repo)
            if git_dir.is_file():
                # Read .git file to find actual git directory
                with open(git_dir, 'r') as f:
                    git_content = f.read().strip()
                    if git_content.startswith("gitdir: "):
                        actual_git_dir = Path(git_content[8:])  # Remove "gitdir: " prefix
                        hooks_dir = actual_git_dir / "hooks"
                    else:
                        # Fallback to main repo hooks
                        hooks_dir = Path(".git") / "hooks"
            else:
                # Regular git directory
                hooks_dir = git_dir / "hooks"
            
            hooks_dir.mkdir(exist_ok=True)
            
            pre_commit_hook = hooks_dir / "pre-commit"
            hook_content = """#!/bin/bash
# Strict quality gates pre-commit hook

echo "🔍 Running quality gates..."

# Run quality gates
python scripts/run_quality_gates.py
if [ $? -ne 0 ]; then
    echo "❌ Quality gates failed. Commit rejected."
    exit 1
fi

echo "✅ Quality gates passed. Proceeding with commit."
"""
            
            with open(pre_commit_hook, 'w') as f:
                f.write(hook_content)
            
            # Make hook executable
            os.chmod(pre_commit_hook, 0o755)
            
            print(f"✅ Pre-commit hooks installed: {pre_commit_hook}")
            
        except Exception as e:
            print(f"⚠️ Could not install pre-commit hooks: {e}")
            # Don't fail the entire worktree creation for hook setup issues
    
    def list_new_worktrees(self) -> List[Dict[str, any]]:
        """List all new worktrees with their status"""
        worktrees = []
        
        if not self.worktrees_dir.exists():
            return worktrees
        
        for worktree_dir in self.worktrees_dir.iterdir():
            if worktree_dir.is_dir():
                quality_file = worktree_dir / ".quality-gates.json"
                if quality_file.exists():
                    try:
                        with open(quality_file, 'r') as f:
                            config = json.load(f)
                        
                        # Get git status
                        try:
                            result = subprocess.run([
                                "git", "status", "--porcelain"
                            ], cwd=worktree_dir, capture_output=True, text=True)
                            
                            has_changes = bool(result.stdout.strip())
                            
                            worktrees.append({
                                "path": str(worktree_dir),
                                "agent_name": config["agent_name"],
                                "task_description": config["task_description"],
                                "created_at": config["created_at"],
                                "has_changes": has_changes,
                                "quality_gates": config["quality_gates"]
                            })
                            
                        except subprocess.CalledProcessError:
                            # Skip if git command fails
                            pass
                            
                    except (json.JSONDecodeError, KeyError):
                        # Skip invalid quality config files
                        pass
        
        return worktrees
    
    def run_quality_gates(self, worktree_path: Path) -> Dict[str, any]:
        """Run quality gates for a specific worktree"""
        try:
            quality_file = worktree_path / ".quality-gates.json"
            if not quality_file.exists():
                return {"success": False, "error": "No quality gates configuration found"}
            
            with open(quality_file, 'r') as f:
                config = json.load(f)
            
            results = {
                "success": True,
                "checks": {},
                "warnings": [],
                "errors": []
            }
            
            # Check PR size (count modified lines)
            try:
                result = subprocess.run([
                    "git", "diff", "--stat", "main"
                ], cwd=worktree_path, capture_output=True, text=True)
                
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    if lines:
                        # Parse git diff stat output
                        last_line = lines[-1]
                        if "insertion" in last_line or "deletion" in last_line:
                            # Extract number of changes
                            parts = last_line.split()
                            changes = 0
                            for part in parts:
                                if part.isdigit():
                                    changes += int(part)
                            
                            max_size = config["quality_gates"]["max_pr_size"]
                            if changes > max_size:
                                results["errors"].append(f"PR size {changes} exceeds limit {max_size}")
                                results["success"] = False
                            else:
                                results["checks"]["pr_size"] = f"✅ {changes}/{max_size} lines"
                        else:
                            results["checks"]["pr_size"] = "✅ No changes detected"
                    else:
                        results["checks"]["pr_size"] = "✅ No changes detected"
                else:
                    results["checks"]["pr_size"] = "✅ No changes detected"
                    
            except subprocess.CalledProcessError as e:
                results["warnings"].append(f"Could not check PR size: {e}")
            
            # Add more quality checks here (tests, docs, security, etc.)
            results["checks"]["tests"] = "⚠️ Test coverage check not implemented"
            results["checks"]["docs"] = "⚠️ Documentation check not implemented"
            results["checks"]["security"] = "⚠️ Security review not implemented"
            results["checks"]["linting"] = "⚠️ Linting check not implemented"
            
            return results
            
        except Exception as e:
            return {"success": False, "error": str(e)}

def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python new_worktree_manager.py create <agent-name> <task-description>")
        print("  python new_worktree_manager.py list")
        print("  python new_worktree_manager.py quality-check <worktree-path>")
        return
    
    manager = NewWorktreeManager()
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 4:
            print("Usage: python new_worktree_manager.py create <agent-name> <task-description>")
            return
        
        agent_name = sys.argv[2]
        task_description = " ".join(sys.argv[3:])
        
        result = manager.create_new_worktree(agent_name, task_description)
        
        if result["success"]:
            print(f"🎉 New worktree created successfully!")
            print(f"📁 Path: {result['worktree_path']}")
            print(f"🌿 Branch: {result['branch_name']}")
            print(f"🔒 Quality gates: {result['quality_gates']['max_pr_size']} line limit")
        else:
            print(f"❌ Failed to create worktree: {result['error']}")
    
    elif command == "list":
        worktrees = manager.list_new_worktrees()
        
        if not worktrees:
            print("📝 No new worktrees found")
        else:
            print(f"📋 Found {len(worktrees)} new worktree(s):")
            for wt in worktrees:
                status = "🔄 Modified" if wt["has_changes"] else "✅ Clean"
                print(f"  - {wt['agent_name']}: {wt['task_description']} ({status})")
                print(f"    Path: {wt['path']}")
                print(f"    Created: {wt['created_at']}")
    
    elif command == "quality-check":
        if len(sys.argv) < 3:
            print("Usage: python new_worktree_manager.py quality-check <worktree-path>")
            return
        
        worktree_path = Path(sys.argv[2])
        result = manager.run_quality_gates(worktree_path)
        
        if result["success"]:
            print("✅ Quality gates check completed")
            for check, status in result["checks"].items():
                print(f"  {check}: {status}")
        else:
            print(f"❌ Quality gates failed: {result['error']}")
        
        if result.get("warnings"):
            print("⚠️ Warnings:")
            for warning in result["warnings"]:
                print(f"  - {warning}")
        
        if result.get("errors"):
            print("❌ Errors:")
            for error in result["errors"]:
                print(f"  - {error}")

if __name__ == "__main__":
    main()