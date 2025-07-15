#!/usr/bin/env python3
"""
Agent Manager for LeanVibe Agent Hive

Manages agent lifecycle using tmux sessions and windows.
Provides capabilities to spawn, monitor, and manage agents in separate tmux windows.
"""

import os
import subprocess
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse


class TmuxAgentManager:
    """Manages agents using tmux sessions and windows."""
    
    def __init__(self, base_dir: str = ".", session_name: str = "agent-hive"):
        self.base_dir = Path(base_dir)
        self.worktrees_dir = self.base_dir / "worktrees"
        self.session_name = session_name
        self.agents = self._discover_agents()
        
    def _discover_agents(self) -> Dict[str, Dict]:
        """Discover all agent worktrees and their configurations."""
        agents = {}
        
        if not self.worktrees_dir.exists():
            return agents
            
        for worktree_dir in self.worktrees_dir.iterdir():
            if worktree_dir.is_dir():
                agent_name = worktree_dir.name
                claude_file = worktree_dir / "CLAUDE.md"
                
                if claude_file.exists():
                    agents[agent_name] = {
                        "name": agent_name,
                        "path": worktree_dir,
                        "claude_file": claude_file,
                        "window_name": f"agent-{agent_name}",
                        "last_activity": self._get_last_activity(worktree_dir),
                        "status": "unknown"
                    }
        
        return agents
    
    def _get_last_activity(self, worktree_dir: Path) -> Optional[datetime]:
        """Get last git activity in worktree."""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ct"],
                cwd=worktree_dir,
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                timestamp = int(result.stdout.strip())
                return datetime.fromtimestamp(timestamp)
        except:
            pass
        return None
    
    def _tmux_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Execute tmux command."""
        return subprocess.run(["tmux"] + cmd, capture_output=True, text=True)
    
    def _session_exists(self) -> bool:
        """Check if tmux session exists."""
        result = self._tmux_command(["has-session", "-t", self.session_name])
        return result.returncode == 0
    
    def _window_exists(self, window_name: str) -> bool:
        """Check if tmux window exists in session."""
        result = self._tmux_command(["list-windows", "-t", self.session_name, "-F", "#{window_name}"])
        if result.returncode == 0:
            return window_name in result.stdout.splitlines()
        return False
    
    def _get_window_status(self, window_name: str) -> Optional[str]:
        """Get status of a specific tmux window."""
        result = self._tmux_command([
            "list-windows", "-t", self.session_name, "-F", "#{window_name}:#{window_active}:#{window_flags}"
        ])
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith(window_name + ":"):
                    parts = line.split(":")
                    if len(parts) >= 3:
                        active = parts[1] == "1"
                        flags = parts[2]
                        return f"{'active' if active else 'inactive'}:{flags}"
        return None
    
    def create_session(self) -> bool:
        """Create tmux session if it doesn't exist."""
        if self._session_exists():
            print(f"✅ Session '{self.session_name}' already exists")
            return True
        
        result = self._tmux_command(["new-session", "-d", "-s", self.session_name])
        if result.returncode == 0:
            print(f"✅ Created session '{self.session_name}'")
            return True
        else:
            print(f"❌ Failed to create session: {result.stderr}")
            return False
    
    def spawn_agent(self, agent_name: str, resume: bool = True) -> bool:
        """Spawn an agent in a new tmux window."""
        if agent_name not in self.agents:
            print(f"❌ Agent '{agent_name}' not found")
            return False
        
        agent = self.agents[agent_name]
        window_name = agent["window_name"]
        
        # Ensure session exists
        if not self.create_session():
            return False
        
        # Check if window already exists
        if self._window_exists(window_name):
            print(f"⚠️  Window '{window_name}' already exists")
            choice = input("Kill existing window and recreate? (y/N): ")
            if choice.lower() == 'y':
                self._tmux_command(["kill-window", "-t", f"{self.session_name}:{window_name}"])
            else:
                print("Aborted")
                return False
        
        # Create new window
        result = self._tmux_command([
            "new-window", "-t", self.session_name, "-n", window_name, "-c", str(agent["path"])
        ])
        
        if result.returncode != 0:
            print(f"❌ Failed to create window: {result.stderr}")
            return False
        
        # Send command to start Claude
        claude_cmd = "claude --resume" if resume else "claude"
        self._tmux_command([
            "send-keys", "-t", f"{self.session_name}:{window_name}", claude_cmd, "Enter"
        ])
        
        print(f"✅ Spawned agent '{agent_name}' in window '{window_name}'")
        print(f"📁 Working directory: {agent['path']}")
        print(f"💬 Command: {claude_cmd}")
        
        return True
    
    def spawn_all_agents(self, resume: bool = True) -> Dict[str, bool]:
        """Spawn all discovered agents."""
        results = {}
        
        print(f"🚀 Spawning {len(self.agents)} agents...")
        
        for agent_name in self.agents:
            print(f"\n🔄 Spawning {agent_name}...")
            results[agent_name] = self.spawn_agent(agent_name, resume)
        
        return results
    
    def list_agent_windows(self) -> Dict[str, Dict]:
        """List all agent windows and their status."""
        if not self._session_exists():
            return {}
        
        status = {}
        for agent_name, agent in self.agents.items():
            window_name = agent["window_name"]
            window_status = self._get_window_status(window_name)
            
            status[agent_name] = {
                "name": agent_name,
                "window_name": window_name,
                "exists": self._window_exists(window_name),
                "status": window_status,
                "path": str(agent["path"])
            }
        
        return status
    
    def print_status(self):
        """Print comprehensive agent status."""
        print("🔍 LeanVibe Agent Hive - Tmux Agent Status")
        print("=" * 50)
        print(f"Session: {self.session_name}")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        if not self._session_exists():
            print("❌ Tmux session does not exist")
            print(f"💡 Run: tmux new-session -s {self.session_name}")
            return
        
        status = self.list_agent_windows()
        
        active_count = 0
        inactive_count = 0
        
        for agent_name, info in status.items():
            if info["exists"]:
                status_parts = info["status"].split(":") if info["status"] else ["unknown"]
                is_active = status_parts[0] == "active"
                
                if is_active:
                    active_count += 1
                    print(f"✅ {agent_name} ({info['window_name']}) - ACTIVE")
                else:
                    inactive_count += 1
                    print(f"🟡 {agent_name} ({info['window_name']}) - INACTIVE")
                
                print(f"   📁 {info['path']}")
            else:
                inactive_count += 1
                print(f"❌ {agent_name} - NOT SPAWNED")
                print(f"   📁 {info['path']}")
        
        print(f"\n📊 Summary:")
        print(f"  Total agents: {len(status)}")
        print(f"  Active windows: {active_count}")
        print(f"  Inactive/Missing: {inactive_count}")
    
    def attach_to_agent(self, agent_name: str):
        """Attach to specific agent window."""
        if agent_name not in self.agents:
            print(f"❌ Agent '{agent_name}' not found")
            return
        
        window_name = self.agents[agent_name]["window_name"]
        
        if not self._window_exists(window_name):
            print(f"❌ Window '{window_name}' does not exist")
            print(f"💡 Run: python scripts/agent_manager.py --spawn {agent_name}")
            return
        
        print(f"🔗 Attaching to agent '{agent_name}'...")
        print(f"💡 Press Ctrl+B then D to detach")
        
        # Use os.system to replace current process with tmux attach
        os.system(f"tmux select-window -t {self.session_name}:{window_name} && tmux attach-session -t {self.session_name}")
    
    def kill_agent(self, agent_name: str) -> bool:
        """Kill specific agent window."""
        if agent_name not in self.agents:
            print(f"❌ Agent '{agent_name}' not found")
            return False
        
        window_name = self.agents[agent_name]["window_name"]
        
        if not self._window_exists(window_name):
            print(f"⚠️  Window '{window_name}' does not exist")
            return True
        
        result = self._tmux_command(["kill-window", "-t", f"{self.session_name}:{window_name}"])
        
        if result.returncode == 0:
            print(f"✅ Killed agent '{agent_name}' window")
            return True
        else:
            print(f"❌ Failed to kill window: {result.stderr}")
            return False
    
    def kill_all_agents(self) -> Dict[str, bool]:
        """Kill all agent windows."""
        results = {}
        
        print("🔥 Killing all agent windows...")
        
        for agent_name in self.agents:
            results[agent_name] = self.kill_agent(agent_name)
        
        return results
    
    def restart_agent(self, agent_name: str) -> bool:
        """Restart specific agent (kill and spawn)."""
        print(f"🔄 Restarting agent '{agent_name}'...")
        
        self.kill_agent(agent_name)
        time.sleep(1)  # Brief pause
        return self.spawn_agent(agent_name)
    
    def get_session_overview(self) -> Dict:
        """Get comprehensive session overview."""
        overview = {
            "session_name": self.session_name,
            "session_exists": self._session_exists(),
            "timestamp": datetime.now().isoformat(),
            "agents": {}
        }
        
        if overview["session_exists"]:
            status = self.list_agent_windows()
            overview["agents"] = status
        
        return overview
    
    def create_attach_script(self, output_file: str = "attach_agents.sh"):
        """Create script with tmux attach commands."""
        script_content = "#!/bin/bash\n"
        script_content += "# LeanVibe Agent Hive - Attach to Agent Windows\n"
        script_content += f"# Session: {self.session_name}\n"
        script_content += f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        script_content += "echo 'Available agents:'\n"
        
        for i, agent_name in enumerate(self.agents.keys(), 1):
            window_name = self.agents[agent_name]["window_name"]
            script_content += f"echo '{i}. {agent_name} ({window_name})'\n"
        
        script_content += "\necho 'Commands:'\n"
        script_content += f"echo 'tmux attach-session -t {self.session_name}  # Attach to session'\n"
        script_content += f"echo 'tmux list-windows -t {self.session_name}    # List windows'\n"
        
        for agent_name in self.agents:
            window_name = self.agents[agent_name]["window_name"]
            script_content += f"echo 'tmux select-window -t {self.session_name}:{window_name} && tmux attach-session -t {self.session_name}  # Attach to {agent_name}'\n"
        
        with open(output_file, "w") as f:
            f.write(script_content)
        
        os.chmod(output_file, 0o755)
        print(f"✅ Attach script created: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Manage LeanVibe agents with tmux")
    parser.add_argument("--session", default="agent-hive", help="Tmux session name")
    parser.add_argument("--spawn", metavar="AGENT", help="Spawn specific agent")
    parser.add_argument("--spawn-all", action="store_true", help="Spawn all agents")
    parser.add_argument("--kill", metavar="AGENT", help="Kill specific agent")
    parser.add_argument("--kill-all", action="store_true", help="Kill all agents")
    parser.add_argument("--restart", metavar="AGENT", help="Restart specific agent")
    parser.add_argument("--attach", metavar="AGENT", help="Attach to specific agent")
    parser.add_argument("--status", action="store_true", help="Show agent status")
    parser.add_argument("--create-session", action="store_true", help="Create tmux session")
    parser.add_argument("--attach-script", action="store_true", help="Create attach script")
    parser.add_argument("--no-resume", action="store_true", help="Don't use --resume when spawning")
    parser.add_argument("--json", action="store_true", help="Output status in JSON format")
    
    args = parser.parse_args()
    
    manager = TmuxAgentManager(session_name=args.session)
    resume = not args.no_resume
    
    if args.create_session:
        manager.create_session()
    
    elif args.spawn:
        manager.spawn_agent(args.spawn, resume=resume)
    
    elif args.spawn_all:
        results = manager.spawn_all_agents(resume=resume)
        success_count = sum(1 for success in results.values() if success)
        print(f"\n📊 Results: {success_count}/{len(results)} agents spawned successfully")
    
    elif args.kill:
        manager.kill_agent(args.kill)
    
    elif args.kill_all:
        results = manager.kill_all_agents()
        success_count = sum(1 for success in results.values() if success)
        print(f"\n📊 Results: {success_count}/{len(results)} agents killed successfully")
    
    elif args.restart:
        manager.restart_agent(args.restart)
    
    elif args.attach:
        manager.attach_to_agent(args.attach)
    
    elif args.attach_script:
        manager.create_attach_script()
    
    elif args.status:
        if args.json:
            overview = manager.get_session_overview()
            print(json.dumps(overview, indent=2, default=str))
        else:
            manager.print_status()
    
    else:
        # Default: show status
        manager.print_status()


if __name__ == "__main__":
    main()