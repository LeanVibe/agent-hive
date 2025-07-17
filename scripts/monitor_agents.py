#!/usr/bin/env python3
"""
Agent Monitor Script for LeanVibe Agent Hive

Monitors agent activity across worktrees and GitHub issues.
Provides tools to check agent status and resume inactive agents.
"""

import os
import subprocess
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse


class AgentMonitor:
    """Monitors agent activity and provides resumption capabilities."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.worktrees_dir = self.base_dir / "worktrees"
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

    def _get_github_issue_activity(self, agent_name: str) -> Optional[Dict]:
        """Get GitHub issue activity for agent."""
        try:
            # Map agent names to likely issue numbers
            issue_mapping = {
                "documentation-agent": 22,
                "intelligence-agent": 24,
                "orchestration-agent": 26,
                "quality-agent": 27,
                "integration-agent": 23,
                "production-agent": 21
            }

            issue_num = issue_mapping.get(agent_name)
            if not issue_num:
                return None

            result = subprocess.run(
                ["gh", "issue", "view", str(issue_num), "--json", "updatedAt,comments"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
        except:
            pass
        return None

    def _get_agent_status(self, agent_name: str) -> str:
        """Determine agent status based on activity."""
        agent = self.agents.get(agent_name)
        if not agent:
            return "not_found"

        last_activity = agent["last_activity"]
        github_activity = self._get_github_issue_activity(agent_name)

        now = datetime.now()

        # Check if agent has been active recently (within 2 hours)
        if last_activity and (now - last_activity) < timedelta(hours=2):
            return "active"

        # Check GitHub issue activity
        if github_activity:
            try:
                updated_at = datetime.fromisoformat(github_activity["updatedAt"].replace("Z", "+00:00"))
                if (now - updated_at.replace(tzinfo=None)) < timedelta(hours=2):
                    return "github_active"
            except:
                pass

        # Check if agent has been idle for more than 4 hours
        if last_activity and (now - last_activity) > timedelta(hours=4):
            return "idle"

        return "inactive"

    def get_agent_status_report(self) -> Dict[str, Dict]:
        """Get comprehensive status report for all agents."""
        report = {}

        for agent_name, agent_info in self.agents.items():
            status = self._get_agent_status(agent_name)
            github_info = self._get_github_issue_activity(agent_name)

            report[agent_name] = {
                "name": agent_name,
                "status": status,
                "path": str(agent_info["path"]),
                "last_activity": agent_info["last_activity"].isoformat() if agent_info["last_activity"] else None,
                "github_issue": github_info is not None,
                "github_updated": github_info["updatedAt"] if github_info else None,
                "needs_attention": status in ["idle", "inactive"]
            }

        return report

    def print_status_report(self):
        """Print a formatted status report."""
        report = self.get_agent_status_report()

        print("🔍 LeanVibe Agent Hive - Agent Status Report")
        print("=" * 50)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        active_agents = []
        inactive_agents = []

        for agent_name, info in report.items():
            if info["status"] in ["active", "github_active"]:
                active_agents.append((agent_name, info))
            else:
                inactive_agents.append((agent_name, info))

        print(f"✅ Active Agents: {len(active_agents)}")
        for agent_name, info in active_agents:
            status_icon = "🟢" if info["status"] == "active" else "🟡"
            print(f"  {status_icon} {agent_name}")
            if info["last_activity"]:
                print(f"    Last activity: {info['last_activity']}")

        print(f"\n⚠️  Inactive Agents: {len(inactive_agents)}")
        for agent_name, info in inactive_agents:
            status_icon = "🔴" if info["status"] == "idle" else "🟠"
            print(f"  {status_icon} {agent_name} ({info['status']})")
            if info["last_activity"]:
                print(f"    Last activity: {info['last_activity']}")
            print(f"    Path: {info['path']}")

        print(f"\n📊 Summary:")
        print(f"  Total agents: {len(report)}")
        print(f"  Active: {len(active_agents)}")
        print(f"  Inactive: {len(inactive_agents)}")
        print(f"  Needs attention: {len([a for a in report.values() if a['needs_attention']])}")

    def generate_resume_commands(self) -> List[str]:
        """Generate commands to resume inactive agents."""
        report = self.get_agent_status_report()
        commands = []

        for agent_name, info in report.items():
            if info["needs_attention"]:
                commands.append(f"# Resume {agent_name}")
                commands.append(f"cd {info['path']}")
                commands.append("claude --resume")
                commands.append("")

        return commands

    def create_resume_script(self, output_file: str = "resume_agents.sh"):
        """Create a script to resume all inactive agents."""
        commands = self.generate_resume_commands()

        script_content = "#!/bin/bash\n"
        script_content += "# LeanVibe Agent Hive - Resume Inactive Agents\n"
        script_content += f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        for command in commands:
            script_content += command + "\n"

        with open(output_file, "w") as f:
            f.write(script_content)

        # Make script executable
        os.chmod(output_file, 0o755)

        print(f"✅ Resume script created: {output_file}")
        print(f"📝 Run: ./{output_file}")

    def resume_agent(self, agent_name: str) -> bool:
        """Resume a specific agent."""
        if agent_name not in self.agents:
            print(f"❌ Agent '{agent_name}' not found")
            return False

        agent_path = self.agents[agent_name]["path"]

        print(f"🔄 Resuming agent: {agent_name}")
        print(f"📁 Path: {agent_path}")

        # Change to agent directory and show instructions
        print(f"\n📋 To resume this agent, run:")
        print(f"  cd {agent_path}")
        print(f"  claude --resume")

        return True

    def ping_agents(self):
        """Ping all agents via GitHub issues."""
        print("📡 Pinging all agents via GitHub issues...")

        issue_mapping = {
            "documentation-agent": 22,
            "intelligence-agent": 24,
            "orchestration-agent": 26,
            "quality-agent": 27,
            "integration-agent": 23,
            "production-agent": 21
        }

        for agent_name, issue_num in issue_mapping.items():
            try:
                message = f"🔔 Agent Status Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                message += "This is an automated status check. Please respond with:\n"
                message += "1. Current work status\n"
                message += "2. Any blockers or issues\n"
                message += "3. Expected completion time\n\n"
                message += "If you are not actively working, please update your status."

                subprocess.run(
                    ["gh", "issue", "comment", str(issue_num), "--body", message],
                    check=True
                )
                print(f"  ✅ Pinged {agent_name} (issue #{issue_num})")
            except subprocess.CalledProcessError:
                print(f"  ❌ Failed to ping {agent_name} (issue #{issue_num})")


def main():
    parser = argparse.ArgumentParser(description="Monitor and manage LeanVibe agents")
    parser.add_argument("--status", action="store_true", help="Show agent status report")
    parser.add_argument("--resume", metavar="AGENT", help="Resume specific agent")
    parser.add_argument("--resume-all", action="store_true", help="Create script to resume all inactive agents")
    parser.add_argument("--ping", action="store_true", help="Ping all agents via GitHub")
    parser.add_argument("--json", action="store_true", help="Output status in JSON format")

    args = parser.parse_args()

    monitor = AgentMonitor()

    if args.status:
        if args.json:
            report = monitor.get_agent_status_report()
            print(json.dumps(report, indent=2, default=str))
        else:
            monitor.print_status_report()

    elif args.resume:
        monitor.resume_agent(args.resume)

    elif args.resume_all:
        monitor.create_resume_script()

    elif args.ping:
        monitor.ping_agents()

    else:
        # Default: show status
        monitor.print_status_report()


if __name__ == "__main__":
    main()
