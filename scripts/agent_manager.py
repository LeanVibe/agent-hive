#!/usr/bin/env python3
"""
CANONICAL: This is the canonical script for agent lifecycle management (spawn, monitor, manage, resume) in the LeanVibe Agent Hive. Use this for all agent lifecycle operations.

Agent Manager for LeanVibe Agent Hive

Manages agent lifecycle using tmux sessions and windows.
Provides capabilities to spawn, monitor, and manage agents in separate tmux windows.
"""

import os
import subprocess
import json
import time
import sys
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

        # First, discover agents in standard worktrees/ directory
        if self.worktrees_dir.exists():
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
                            "status": "unknown",
                        }

        # Then, discover agents from git worktree list (for agents outside worktrees/)
        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.base_dir,
            )

            if result.returncode == 0:
                current_worktree = None
                for line in result.stdout.splitlines():
                    if line.startswith("worktree "):
                        current_worktree = Path(line.split(" ", 1)[1])
                    elif line.startswith("branch ") and current_worktree:
                        # Check if this is an agent worktree (not main repo)
                        if (
                            current_worktree != self.base_dir
                            and current_worktree.name not in agents
                            and current_worktree.name != "agent-hive"
                        ):
                            claude_file = current_worktree / "CLAUDE.md"
                            if claude_file.exists():
                                # Extract agent name from path
                                agent_name = current_worktree.name
                                if agent_name.endswith("-worktree"):
                                    agent_name = agent_name[
                                        :-9
                                    ]  # Remove "-worktree" suffix

                                # Skip if this agent looks like a generic orchestrator
                                if self._is_agent_specific_claude(claude_file):
                                    agents[agent_name] = {
                                        "name": agent_name,
                                        "path": current_worktree,
                                        "claude_file": claude_file,
                                        "window_name": f"agent-{agent_name}",
                                        "last_activity": self._get_last_activity(
                                            current_worktree
                                        ),
                                        "status": "unknown",
                                    }
        except Exception as e:
            print(f"Warning: Could not discover git worktrees: {e}")

        return agents

    def _is_agent_specific_claude(self, claude_file: Path) -> bool:
        """Check if CLAUDE.md file is agent-specific (not generic orchestrator)."""
        try:
            content = claude_file.read_text()
            # Skip if it looks like a generic orchestrator file
            if "LeanVibe Orchestrator" in content and "Role: Orchestrator" in content:
                return False
            # Must contain agent-specific content
            if any(
                term in content.lower()
                for term in [
                    "agent identity",
                    "agent instructions",
                    "specialization",
                    "mission statement",
                ]
            ):
                return True
            return False
        except Exception:
            return False

    def _get_last_activity(self, worktree_dir: Path) -> Optional[datetime]:
        """Get last git activity in worktree."""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ct"],
                cwd=worktree_dir,
                capture_output=True,
                text=True,
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
        result = self._tmux_command(
            ["list-windows", "-t", self.session_name, "-F", "#{window_name}"]
        )
        if result.returncode == 0:
            return window_name in result.stdout.splitlines()
        return False

    def _get_window_status(self, window_name: str) -> Optional[str]:
        """Get status of a specific tmux window."""
        result = self._tmux_command(
            [
                "list-windows",
                "-t",
                self.session_name,
                "-F",
                "#{window_name}:#{window_active}:#{window_flags}",
            ]
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith(window_name + ":"):
                    parts = line.split(":")
                    if len(parts) >= 3:
                        active = parts[1] == "1"
                        flags = parts[2]
                        return f"{'active' if active else 'inactive'}:{flags}"
        return None

    def _get_starting_prompt(self, agent_name: str) -> Optional[str]:
        """Get starting prompt from agent's CLAUDE.md file."""
        if agent_name not in self.agents:
            return None
            
        agent = self.agents[agent_name]
        claude_file = agent.get("claude_file")
        
        if not claude_file or not claude_file.exists():
            return None
            
        try:
            # Read CLAUDE.md and extract mission/objectives
            with open(claude_file, 'r') as f:
                content = f.read()
            
            # Extract agent type and mission from CLAUDE.md content
            lines = content.split('\n')
            agent_type = "Agent"
            mission = ""
            
            for i, line in enumerate(lines):
                if line.startswith('# ') and any(keyword in line.lower() for keyword in ['specialist', 'agent', 'frontend', 'pm', 'security', 'performance']):
                    agent_type = line.replace('#', '').strip()
                if line.startswith('## 🎯 **Mission:') and i + 1 < len(lines):
                    mission = lines[i].replace('## 🎯 **Mission:', '').strip().rstrip('**')
                    break
                elif 'Mission:' in line or 'Objectives' in line:
                    mission = line.split('Mission:')[-1].split('Objectives')[-1].strip()
                    break
            
            if not mission:
                # Fallback to first few lines after title
                for line in lines[2:8]:
                    if line.strip() and not line.startswith('#') and not line.startswith('You are'):
                        mission = line.strip()
                        break
            
            # Generate dynamic starting prompt
            prompt = f"Hello! I'm the {agent_type}. I'm ready to work on: {mission}\n\nLet me start by reading my CLAUDE.md instructions and current project status, then begin executing my assigned mission."
            
            return prompt
            
        except Exception as e:
            # Fallback prompt if file reading fails
            return f"Hello! I'm ready to work as the {agent_name}. Let me start by reading my CLAUDE.md instructions and begin executing my assigned tasks."

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

    def spawn_agent(
        self, agent_name: str, with_prompt: bool = True, force_recreate: bool = False
    ) -> bool:
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
            if force_recreate:
                print(f"🔄 Force recreating window '{window_name}'")
                self._tmux_command(
                    ["kill-window", "-t", f"{self.session_name}:{window_name}"]
                )
            else:
                print(f"⚠️  Window '{window_name}' already exists")
                try:
                    choice = input("Kill existing window and recreate? (y/N): ")
                    if choice.lower() == "y":
                        self._tmux_command(
                            ["kill-window", "-t", f"{self.session_name}:{window_name}"]
                        )
                    else:
                        print("Aborted")
                        return False
                except EOFError:
                    print("Non-interactive mode - skipping existing window")
                    return False

        # Create new window
        result = self._tmux_command(
            [
                "new-window",
                "-t",
                self.session_name,
                "-n",
                window_name,
                "-c",
                str(agent["path"]),
            ]
        )

        if result.returncode != 0:
            print(f"❌ Failed to create window: {result.stderr}")
            return False

        # Send command to start Claude with proper permissions
        claude_cmd = "claude --dangerously-skip-permissions"
        self._tmux_command(
            [
                "send-keys",
                "-t",
                f"{self.session_name}:{window_name}",
                claude_cmd,
                "Enter",
            ]
        )

        # Send starting prompt if requested
        if with_prompt:
            time.sleep(3)  # Wait for Claude to initialize
            starting_prompt = self._get_starting_prompt(agent_name)
            if starting_prompt:
                # Log the prompt
                try:
                    sys.path.append(str(self.base_dir))
                    from dashboard.prompt_logger import prompt_logger

                    prompt_logger.log_prompt(
                        agent_name, starting_prompt, "Starting prompt sent", True
                    )
                except ImportError:
                    pass  # Continue without logging if dashboard not available

                # Use buffer method for reliable prompt sending
                # Set prompt in buffer
                self._tmux_command(["set-buffer", starting_prompt])

                # Clear any existing input
                self._tmux_command(
                    ["send-keys", "-t", f"{self.session_name}:{window_name}", "C-c"]
                )

                time.sleep(0.3)  # Brief pause

                # Paste buffer content
                self._tmux_command(
                    ["paste-buffer", "-t", f"{self.session_name}:{window_name}"]
                )

                # Send Enter to submit
                time.sleep(0.2)
                self._tmux_command(
                    ["send-keys", "-t", f"{self.session_name}:{window_name}", "Enter"]
                )

        print(f"✅ Spawned agent '{agent_name}' in window '{window_name}'")
        print(f"📁 Working directory: {agent['path']}")
        print(f"💬 Command: {claude_cmd}")
        if with_prompt:
            print(f"🚀 Starting prompt sent")

        return True

    def spawn_all_agents(
        self, with_prompt: bool = True, force_recreate: bool = False
    ) -> Dict[str, bool]:
        """Spawn all discovered agents."""
        results = {}

        print(f"🚀 Spawning {len(self.agents)} agents...")

        for agent_name in self.agents:
            print(f"\n🔄 Spawning {agent_name}...")
            results[agent_name] = self.spawn_agent(
                agent_name, with_prompt, force_recreate
            )

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
                "path": str(agent["path"]),
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
                status_parts = (
                    info["status"].split(":") if info["status"] else ["unknown"]
                )
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

        # Use subprocess.run safely instead of os.system
        try:
            subprocess.run(
                ["tmux", "select-window", "-t", f"{self.session_name}:{window_name}"],
                check=True,
            )
            subprocess.run(
                ["tmux", "attach-session", "-t", self.session_name], check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to attach to agent: {e}")

    def kill_agent(self, agent_name: str) -> bool:
        """Kill specific agent window."""
        if agent_name not in self.agents:
            print(f"❌ Agent '{agent_name}' not found")
            return False

        window_name = self.agents[agent_name]["window_name"]

        if not self._window_exists(window_name):
            print(f"⚠️  Window '{window_name}' does not exist")
            return True

        result = self._tmux_command(
            ["kill-window", "-t", f"{self.session_name}:{window_name}"]
        )

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

    def restart_agent(self, agent_name: str, with_prompt: bool = True) -> bool:
        """Restart specific agent (kill and spawn)."""
        print(f"🔄 Restarting agent '{agent_name}'...")

        self.kill_agent(agent_name)
        time.sleep(1)  # Brief pause
        return self.spawn_agent(agent_name, with_prompt, force_recreate=True)

    def get_session_overview(self) -> Dict:
        """Get comprehensive session overview."""
        overview = {
            "session_name": self.session_name,
            "session_exists": self._session_exists(),
            "timestamp": datetime.now().isoformat(),
            "agents": {},
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
        script_content += (
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )

        script_content += "echo 'Available agents:'\n"

        for i, agent_name in enumerate(self.agents.keys(), 1):
            window_name = self.agents[agent_name]["window_name"]
            script_content += f"echo '{i}. {agent_name} ({window_name})'\n"

        script_content += "\necho 'Commands:'\n"
        script_content += (
            f"echo 'tmux attach-session -t {self.session_name}  # Attach to session'\n"
        )
        script_content += (
            f"echo 'tmux list-windows -t {self.session_name}    # List windows'\n"
        )

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
    parser.add_argument(
        "--create-session", action="store_true", help="Create tmux session"
    )
    parser.add_argument(
        "--attach-script", action="store_true", help="Create attach script"
    )
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Don't send starting prompt when spawning",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recreate existing windows without prompting",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output status in JSON format"
    )

    args = parser.parse_args()

    manager = TmuxAgentManager(session_name=args.session)
    with_prompt = not args.no_prompt

    if args.create_session:
        manager.create_session()

    elif args.spawn:
        manager.spawn_agent(
            args.spawn, with_prompt=with_prompt, force_recreate=args.force
        )

    elif args.spawn_all:
        results = manager.spawn_all_agents(
            with_prompt=with_prompt, force_recreate=args.force
        )
        success_count = sum(1 for success in results.values() if success)
        print(
            f"\n📊 Results: {success_count}/{len(results)} agents spawned successfully"
        )

    elif args.kill:
        manager.kill_agent(args.kill)

    elif args.kill_all:
        results = manager.kill_all_agents()
        success_count = sum(1 for success in results.values() if success)
        print(
            f"\n📊 Results: {success_count}/{len(results)} agents killed successfully"
        )

    elif args.restart:
        manager.restart_agent(args.restart, with_prompt=with_prompt)

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
