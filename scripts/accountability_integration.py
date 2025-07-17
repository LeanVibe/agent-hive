#!/usr/bin/env python3
"""
Accountability Integration

Integrates accountability system with existing agent spawning and management systems.
Provides seamless integration without disrupting existing workflows.
"""

import os
import json
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from accountability_system import AccountabilitySystem, TaskStatus


class AccountabilityIntegration:
    """Integration layer for accountability system."""
    
    def __init__(self):
        self.system = AccountabilitySystem()
        self.integration_config = {
            "auto_assign_on_spawn": True,
            "auto_track_progress": True,
            "escalation_notifications": True,
            "default_deadline_hours": 24,
            "progress_check_interval": 300  # 5 minutes
        }
        
        # Integration state
        self.spawned_agents = {}
        self.tracked_tasks = {}
        
    def integrate_with_spawner(self, agent_spawner_path: str):
        """Integrate with existing agent spawner."""
        # Hook into spawner to automatically assign tasks
        spawner_script = Path(agent_spawner_path)
        if not spawner_script.exists():
            raise FileNotFoundError(f"Agent spawner not found: {agent_spawner_path}")
        
        # Create integration wrapper
        wrapper_path = spawner_script.parent / f"integrated_{spawner_script.name}"
        self._create_spawner_wrapper(spawner_script, wrapper_path)
        
        return str(wrapper_path)
    
    def _create_spawner_wrapper(self, original_spawner: Path, wrapper_path: Path):
        """Create wrapper script that adds accountability."""
        wrapper_content = f'''#!/usr/bin/env python3
"""
Accountability-Integrated Agent Spawner
Automatically created wrapper that adds accountability tracking.
"""

import sys
import subprocess
from pathlib import Path

# Add accountability integration
sys.path.insert(0, str(Path(__file__).parent))
from accountability_integration import AccountabilityIntegration

def main():
    integration = AccountabilityIntegration()
    
    # Run original spawner
    result = subprocess.run([
        sys.executable, "{original_spawner}"
    ] + sys.argv[1:], capture_output=True, text=True)
    
    # Parse spawner output for agent info
    if result.returncode == 0:
        output = result.stdout
        # Extract agent info and auto-assign task
        integration.handle_agent_spawn(output, sys.argv)
    
    # Forward output
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
'''
        
        with open(wrapper_path, 'w') as f:
            f.write(wrapper_content)
        
        os.chmod(wrapper_path, 0o755)
    
    def handle_agent_spawn(self, spawner_output: str, spawn_args: List[str]):
        """Handle agent spawn event and auto-assign accountability task."""
        try:
            # Parse spawner output to extract agent info
            agent_info = self._parse_spawner_output(spawner_output)
            
            if agent_info and self.integration_config["auto_assign_on_spawn"]:
                # Auto-assign accountability task
                task_id = self.auto_assign_task(agent_info, spawn_args)
                
                # Track the spawned agent
                self.spawned_agents[agent_info["agent_id"]] = {
                    "spawn_time": datetime.now(),
                    "task_id": task_id,
                    "agent_info": agent_info
                }
                
                print(f"🚨 ACCOUNTABILITY: Task {task_id} auto-assigned to {agent_info['agent_id']}")
        
        except Exception as e:
            print(f"⚠️  Accountability integration warning: {e}")
    
    def _parse_spawner_output(self, output: str) -> Optional[Dict[str, Any]]:
        """Parse spawner output to extract agent information."""
        lines = output.splitlines()
        
        agent_info = {}
        
        for line in lines:
            if "Agent:" in line:
                agent_info["agent_id"] = line.split("Agent:")[-1].strip()
            elif "Path:" in line:
                agent_info["path"] = line.split("Path:")[-1].strip()
            elif "Priority:" in line:
                try:
                    agent_info["priority"] = float(line.split("Priority:")[-1].strip())
                except:
                    agent_info["priority"] = 1.0
            elif "Task:" in line:
                agent_info["task_description"] = line.split("Task:")[-1].strip()
        
        return agent_info if "agent_id" in agent_info else None
    
    def auto_assign_task(self, agent_info: Dict[str, Any], spawn_args: List[str]) -> str:
        """Automatically assign accountability task to spawned agent."""
        
        # Determine task details
        title = f"Complete {agent_info.get('agent_id', 'Unknown')} Mission"
        description = agent_info.get('task_description', 'Complete assigned mission objectives')
        
        # Determine deadline based on agent type and priority
        deadline_hours = self._calculate_deadline_hours(agent_info, spawn_args)
        priority = agent_info.get('priority', 1.0)
        
        # Assign task
        task_id = self.system.assign_task(
            agent_id=agent_info["agent_id"],
            title=title,
            description=description,
            deadline_hours=deadline_hours,
            priority=priority
        )
        
        return task_id
    
    def _calculate_deadline_hours(self, agent_info: Dict[str, Any], spawn_args: List[str]) -> int:
        """Calculate appropriate deadline based on agent type and task."""
        
        # Base deadline
        base_hours = self.integration_config["default_deadline_hours"]
        
        # Adjust based on priority
        priority = agent_info.get('priority', 1.0)
        if priority < 1.5:  # High priority
            return max(4, int(base_hours * 0.5))  # Minimum 4 hours
        elif priority < 2.0:  # Medium priority
            return int(base_hours * 0.75)
        else:  # Low priority
            return int(base_hours * 1.5)
    
    def monitor_agent_progress(self):
        """Monitor progress of spawned agents."""
        current_time = datetime.now()
        
        for agent_id, agent_data in self.spawned_agents.items():
            task_id = agent_data["task_id"]
            
            # Check if task exists in accountability system
            if task_id not in self.system.active_tasks:
                continue
            
            task = self.system.active_tasks[task_id]
            
            # Check for progress updates needed
            if task.last_update is None or (current_time - task.last_update).total_seconds() > self.integration_config["progress_check_interval"]:
                
                # Try to get progress from agent directory
                progress_info = self._extract_agent_progress(agent_data["agent_info"])
                
                if progress_info:
                    # Update progress automatically
                    success = self.system.update_task_progress(
                        agent_id=agent_id,
                        task_id=task_id,
                        progress_percentage=progress_info["progress"],
                        status_summary=progress_info["summary"],
                        evidence_files=progress_info.get("evidence_files", []),
                        blockers=progress_info.get("blockers", [])
                    )
                    
                    if success:
                        print(f"📊 Auto-updated progress for {agent_id}: {progress_info['progress']}%")
    
    def _extract_agent_progress(self, agent_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract progress information from agent's working directory."""
        try:
            agent_path = Path(agent_info.get("path", ""))
            if not agent_path.exists():
                return None
            
            # Check git activity
            git_progress = self._check_git_progress(agent_path)
            
            # Check for progress files
            progress_files = self._check_progress_files(agent_path)
            
            # Estimate progress
            estimated_progress = self._estimate_progress(git_progress, progress_files)
            
            return {
                "progress": estimated_progress,
                "summary": f"Auto-detected: {git_progress.get('commits', 0)} commits, {len(progress_files)} evidence files",
                "evidence_files": progress_files,
                "blockers": []
            }
            
        except Exception as e:
            print(f"⚠️  Progress extraction failed for {agent_info.get('agent_id', 'unknown')}: {e}")
            return None
    
    def _check_git_progress(self, agent_path: Path) -> Dict[str, Any]:
        """Check git activity in agent directory."""
        try:
            # Get recent commits
            result = subprocess.run([
                "git", "log", "--oneline", "--since=1 day ago"
            ], cwd=agent_path, capture_output=True, text=True)
            
            commits = len(result.stdout.splitlines()) if result.returncode == 0 else 0
            
            # Get file changes
            result = subprocess.run([
                "git", "diff", "--stat", "HEAD~1", "HEAD"
            ], cwd=agent_path, capture_output=True, text=True)
            
            file_changes = len(result.stdout.splitlines()) if result.returncode == 0 else 0
            
            return {
                "commits": commits,
                "file_changes": file_changes
            }
            
        except Exception:
            return {"commits": 0, "file_changes": 0}
    
    def _check_progress_files(self, agent_path: Path) -> List[str]:
        """Check for evidence files in agent directory."""
        evidence_patterns = [
            "*.py", "*.md", "*.json", "*.yml", "*.yaml",
            "tests/**/*.py", "scripts/**/*.py"
        ]
        
        evidence_files = []
        
        try:
            for pattern in evidence_patterns:
                files = list(agent_path.glob(pattern))
                evidence_files.extend([str(f.relative_to(agent_path)) for f in files])
        
        except Exception:
            pass
        
        return evidence_files[:10]  # Limit to first 10 files
    
    def _estimate_progress(self, git_progress: Dict[str, Any], evidence_files: List[str]) -> int:
        """Estimate progress percentage based on activity."""
        
        # Base progress from git activity
        commits = git_progress.get("commits", 0)
        file_changes = git_progress.get("file_changes", 0)
        evidence_count = len(evidence_files)
        
        # Simple estimation algorithm
        progress = 0
        
        # Progress from commits (up to 60%)
        progress += min(60, commits * 15)
        
        # Progress from file changes (up to 30%)
        progress += min(30, file_changes * 3)
        
        # Progress from evidence files (up to 20%)
        progress += min(20, evidence_count * 2)
        
        return min(100, progress)
    
    def create_accountability_hook(self, hook_dir: str):
        """Create git hooks for automatic progress tracking."""
        hook_dir = Path(hook_dir)
        hook_dir.mkdir(exist_ok=True)
        
        # Post-commit hook
        post_commit_hook = hook_dir / "post-commit"
        hook_content = f'''#!/bin/bash
# Accountability system git hook
python3 {Path(__file__).parent}/accountability_integration.py --git-hook post-commit
'''
        
        with open(post_commit_hook, 'w') as f:
            f.write(hook_content)
        
        os.chmod(post_commit_hook, 0o755)
        
        print(f"✅ Accountability git hook created: {post_commit_hook}")
    
    def handle_git_hook(self, hook_type: str):
        """Handle git hook events."""
        if hook_type == "post-commit":
            # Find current agent and update progress
            cwd = Path.cwd()
            
            # Try to identify agent from current directory
            for agent_id, agent_data in self.spawned_agents.items():
                if str(cwd) == agent_data["agent_info"].get("path"):
                    
                    # Update progress based on latest commit
                    progress_info = self._extract_agent_progress(agent_data["agent_info"])
                    
                    if progress_info:
                        self.system.update_task_progress(
                            agent_id=agent_id,
                            task_id=agent_data["task_id"],
                            progress_percentage=progress_info["progress"],
                            status_summary=f"Git commit detected: {progress_info['summary']}",
                            evidence_files=progress_info.get("evidence_files", [])
                        )
                    
                    break
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get current integration status."""
        return {
            "spawned_agents": len(self.spawned_agents),
            "tracked_tasks": len(self.tracked_tasks),
            "active_tasks": len([t for t in self.system.active_tasks.values() 
                               if t.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]]),
            "config": self.integration_config,
            "timestamp": datetime.now().isoformat()
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Accountability Integration")
    parser.add_argument("--integrate-spawner", help="Integrate with spawner script")
    parser.add_argument("--monitor", action="store_true", help="Run continuous monitoring")
    parser.add_argument("--git-hook", help="Handle git hook (post-commit)")
    parser.add_argument("--status", action="store_true", help="Show integration status")
    
    args = parser.parse_args()
    
    integration = AccountabilityIntegration()
    
    if args.integrate_spawner:
        wrapper_path = integration.integrate_with_spawner(args.integrate_spawner)
        print(f"✅ Created integrated spawner: {wrapper_path}")
        
    elif args.monitor:
        print("🔄 Starting accountability monitoring...")
        try:
            while True:
                integration.monitor_agent_progress()
                time.sleep(integration.integration_config["progress_check_interval"])
        except KeyboardInterrupt:
            print("\n✅ Monitoring stopped")
            
    elif args.git_hook:
        integration.handle_git_hook(args.git_hook)
        
    elif args.status:
        status = integration.get_integration_status()
        print(json.dumps(status, indent=2))
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()