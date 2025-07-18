#!/usr/bin/env python3
"""
Agent Status Checker

Provides real-time status of all agents in the system.
"""

import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class AgentStatusChecker:
    """Check status of all agents in the system"""

    def __init__(self):
        self.base_dir = Path(".")
        self.worktrees_dir = self.base_dir / "worktrees"
        self.session_name = "agent-hive"

    def check_all_agents(self) -> Dict[str, Dict]:
        """Check status of all agents"""
        agents = {}

        # Check tmux sessions
        tmux_agents = self._get_tmux_agents()

        # Check worktrees
        worktree_agents = self._get_worktree_agents()

        # Combine information
        all_agent_names = set(tmux_agents.keys()) | set(worktree_agents.keys())

        for agent_name in all_agent_names:
            agents[agent_name] = {
                "name": agent_name,
                "tmux_active": agent_name in tmux_agents,
                "has_worktree": agent_name in worktree_agents,
                "worktree_path": worktree_agents.get(agent_name, {}).get("path"),
                "last_activity": worktree_agents.get(agent_name, {}).get("last_activity"),
                "status": self._determine_status(agent_name, tmux_agents, worktree_agents)
            }

        return agents

    def _get_tmux_agents(self) -> Dict[str, Dict]:
        """Get agents from tmux sessions"""
        agents = {}

        try:
            result = subprocess.run([
                "tmux", "list-windows", "-t", self.session_name, "-F",
                "#{window_name}:#{window_active}:#{window_flags}"
            ], capture_output=True, text=True)

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line and line.startswith("agent-"):
                        parts = line.split(':')
                        if len(parts) >= 2:
                            window_name = parts[0]
                            is_active = parts[1] == "1"

                            # Extract agent name
                            if window_name.startswith("agent-"):
                                agent_name = window_name[6:]  # Remove "agent-" prefix
                                agents[agent_name] = {
                                    "window_name": window_name,
                                    "active": is_active
                                }

        except Exception as e:
            print(f"Warning: Could not check tmux sessions: {e}")

        return agents

    def _get_worktree_agents(self) -> Dict[str, Dict]:
        """Get agents from worktrees"""
        agents = {}

        # Check standard worktrees
        if self.worktrees_dir.exists():
            for worktree_dir in self.worktrees_dir.iterdir():
                if worktree_dir.is_dir():
                    claude_file = worktree_dir / "CLAUDE.md"
                    if claude_file.exists():
                        agent_name = worktree_dir.name
                        last_activity = self._get_last_git_activity(worktree_dir)

                        agents[agent_name] = {
                            "path": str(worktree_dir),
                            "last_activity": last_activity
                        }

        # Check new worktrees
        new_worktrees_dir = self.base_dir / "new-worktrees"
        if new_worktrees_dir.exists():
            for worktree_dir in new_worktrees_dir.iterdir():
                if worktree_dir.is_dir():
                    claude_file = worktree_dir / "CLAUDE.md"
                    if claude_file.exists():
                        agent_name = worktree_dir.name
                        last_activity = self._get_last_git_activity(worktree_dir)

                        agents[agent_name] = {
                            "path": str(worktree_dir),
                            "last_activity": last_activity
                        }

        return agents

    def _get_last_git_activity(self, worktree_path: Path) -> Optional[str]:
        """Get last git activity in worktree"""
        try:
            result = subprocess.run([
                "git", "log", "-1", "--format=%ci"
            ], capture_output=True, text=True, cwd=worktree_path)

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except:
            pass

        return None

    def _determine_status(self, agent_name: str, tmux_agents: Dict, worktree_agents: Dict) -> str:
        """Determine overall agent status"""
        has_tmux = agent_name in tmux_agents
        has_worktree = agent_name in worktree_agents

        if has_tmux and has_worktree:
            return "ACTIVE"
        elif has_tmux:
            return "TMUX_ONLY"
        elif has_worktree:
            return "WORKTREE_ONLY"
        else:
            return "UNKNOWN"

    def print_status_report(self, agents: Dict[str, Dict]):
        """Print formatted status report"""
        print("🤖 AGENT STATUS REPORT")
        print("=" * 50)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        if not agents:
            print("No agents found")
            return

        # Group by status
        status_groups = {}
        for agent_name, info in agents.items():
            status = info["status"]
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append((agent_name, info))

        # Print each group
        for status, agent_list in status_groups.items():
            if status == "ACTIVE":
                emoji = "✅"
            elif status in ["TMUX_ONLY", "WORKTREE_ONLY"]:
                emoji = "⚠️"
            else:
                emoji = "❓"

            print(f"{emoji} {status} ({len(agent_list)} agents):")

            for agent_name, info in sorted(agent_list):
                tmux_status = "🟢" if info["tmux_active"] else "🔴"
                worktree_status = "📁" if info["has_worktree"] else "❌"

                print(f"  {agent_name}:")
                print(f"    Tmux: {tmux_status} | Worktree: {worktree_status}")

                if info["worktree_path"]:
                    print(f"    Path: {info['worktree_path']}")

                if info["last_activity"]:
                    print(f"    Last activity: {info['last_activity']}")

                print()

    def get_agent_capabilities(self, agent_name: str) -> Optional[str]:
        """Get agent capabilities from CLAUDE.md"""
        # Check worktrees for agent
        possible_paths = [
            self.worktrees_dir / agent_name / "CLAUDE.md",
            self.base_dir / "new-worktrees" / agent_name / "CLAUDE.md"
        ]

        for claude_file in possible_paths:
            if claude_file.exists():
                try:
                    content = claude_file.read_text()
                    # Extract capabilities section
                    if "capabilities" in content.lower() or "specialization" in content.lower():
                        return content[:500] + "..." if len(content) > 500 else content
                except:
                    pass

        return None

def main():
    """Main CLI interface"""
    import sys

    checker = AgentStatusChecker()

    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        # JSON output
        agents = checker.check_all_agents()
        print(json.dumps(agents, indent=2, default=str))
    else:
        # Human readable output
        agents = checker.check_all_agents()
        checker.print_status_report(agents)

        # Show capabilities if specific agent requested
        if len(sys.argv) > 2 and sys.argv[1] == "--capabilities":
            agent_name = sys.argv[2]
            capabilities = checker.get_agent_capabilities(agent_name)
            if capabilities:
                print(f"\n📋 CAPABILITIES for {agent_name}:")
                print("-" * 40)
                print(capabilities)
            else:
                print(f"\n❓ No capabilities found for {agent_name}")

if __name__ == "__main__":
    main()
