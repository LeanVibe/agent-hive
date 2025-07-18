#!/usr/bin/env python3
"""
Real-time Agent Activity Monitor

Provides real-time monitoring of agent activities including:
- Git activity and commits
- Resource usage (CPU, memory)
- Task progress and completion
- Communication patterns
- Health metrics
"""

import asyncio
import logging
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class AgentActivity:
    """Real-time agent activity data"""
    agent_name: str
    timestamp: datetime
    activity_type: str  # 'git', 'resource', 'communication', 'task'
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class AgentMetrics:
    """Agent performance metrics"""
    agent_name: str
    cpu_percent: float
    memory_percent: float
    disk_usage: float
    git_commits_today: int
    lines_changed_today: int
    communication_count: int
    task_completion_rate: float
    last_activity: datetime
    health_score: float

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['last_activity'] = self.last_activity.isoformat()
        return data


class RealtimeAgentMonitor:
    """Real-time agent activity monitoring system"""

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.worktrees_dir = self.base_dir / "worktrees"
        self.new_worktrees_dir = self.base_dir / "new-worktrees"

        # Activity tracking
        self.activities: List[AgentActivity] = []
        self.agent_metrics: Dict[str, AgentMetrics] = {}
        self.git_activity_cache: Dict[str, List[Dict]] = {}

        # Monitoring configuration
        self.monitoring_interval = 5  # seconds
        self.activity_retention_hours = 24
        self.max_activities = 1000

        # Add dashboard integration
        try:
            from dashboard.prompt_logger import prompt_logger
            self.prompt_logger = prompt_logger
        except ImportError:
            self.prompt_logger = None
            logger.warning("Dashboard prompt logger not available")

    async def start_monitoring(self):
        """Start real-time monitoring"""
        logger.info("🔍 Starting real-time agent activity monitoring...")

        # Start monitoring tasks
        tasks = [
            asyncio.create_task(self._monitor_git_activity()),
            asyncio.create_task(self._monitor_resource_usage()),
            asyncio.create_task(self._monitor_communication()),
            asyncio.create_task(self._monitor_task_progress()),
            asyncio.create_task(self._cleanup_old_activities())
        ]

        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"❌ Monitoring error: {e}")

    async def _monitor_git_activity(self):
        """Monitor git activity across all agent worktrees"""
        while True:
            try:
                agents = await self._discover_agents()

                for agent_name, agent_path in agents.items():
                    git_activity = await self._get_git_activity(agent_name, agent_path)

                    if git_activity:
                        activity = AgentActivity(
                            agent_name=agent_name,
                            timestamp=datetime.now(),
                            activity_type="git",
                            details=git_activity
                        )
                        self._add_activity(activity)

                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Git monitoring error: {e}")
                await asyncio.sleep(self.monitoring_interval)

    async def _monitor_resource_usage(self):
        """Monitor CPU, memory, and disk usage"""
        while True:
            try:
                # Get system-wide metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('.')

                # Get agent-specific metrics (approximation)
                agents = await self._discover_agents()

                for agent_name, agent_path in agents.items():
                    # Estimate resource usage per agent
                    agent_cpu = cpu_percent / max(len(agents), 1)
                    agent_memory = memory.percent / max(len(agents), 1)
                    agent_disk = disk.percent

                    # Update metrics
                    if agent_name not in self.agent_metrics:
                        self.agent_metrics[agent_name] = AgentMetrics(
                            agent_name=agent_name,
                            cpu_percent=agent_cpu,
                            memory_percent=agent_memory,
                            disk_usage=agent_disk,
                            git_commits_today=0,
                            lines_changed_today=0,
                            communication_count=0,
                            task_completion_rate=0.0,
                            last_activity=datetime.now(),
                            health_score=100.0
                        )
                    else:
                        metrics = self.agent_metrics[agent_name]
                        metrics.cpu_percent = agent_cpu
                        metrics.memory_percent = agent_memory
                        metrics.disk_usage = agent_disk
                        metrics.last_activity = datetime.now()

                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(self.monitoring_interval)

    async def _monitor_communication(self):
        """Monitor agent communication patterns"""
        while True:
            try:
                if self.prompt_logger:
                    # Get recent prompts
                    recent_prompts = self.prompt_logger.get_recent_prompts(
                        limit=10)

                    for prompt in recent_prompts:
                        # Track communication activity
                        activity = AgentActivity(
                            agent_name=prompt.agent_name,
                            timestamp=datetime.fromisoformat(prompt.timestamp),
                            activity_type="communication",
                            details={
                                "prompt_id": prompt.id,
                                "success": prompt.success,
                                "prompt_length": len(prompt.prompt_text),
                                "has_response": bool(prompt.response)
                            }
                        )
                        self._add_activity(activity)

                        # Update metrics
                        if prompt.agent_name in self.agent_metrics:
                            self.agent_metrics[prompt.agent_name].communication_count += 1

                # Less frequent
                await asyncio.sleep(self.monitoring_interval * 2)

            except Exception as e:
                logger.error(f"Communication monitoring error: {e}")
                await asyncio.sleep(self.monitoring_interval)

    async def _monitor_task_progress(self):
        """Monitor task progress and completion"""
        while True:
            try:
                agents = await self._discover_agents()

                for agent_name, agent_path in agents.items():
                    task_progress = await self._get_task_progress(agent_name, agent_path)

                    if task_progress:
                        activity = AgentActivity(
                            agent_name=agent_name,
                            timestamp=datetime.now(),
                            activity_type="task",
                            details=task_progress
                        )
                        self._add_activity(activity)

                # Less frequent
                await asyncio.sleep(self.monitoring_interval * 3)

            except Exception as e:
                logger.error(f"Task monitoring error: {e}")
                await asyncio.sleep(self.monitoring_interval)

    async def _cleanup_old_activities(self):
        """Clean up old activities to prevent memory bloat"""
        while True:
            try:
                cutoff_time = datetime.now() - timedelta(hours=self.activity_retention_hours)

                # Remove old activities
                self.activities = [
                    activity for activity in self.activities
                    if activity.timestamp > cutoff_time
                ]

                # Limit total activities
                if len(self.activities) > self.max_activities:
                    self.activities = self.activities[-self.max_activities:]

                await asyncio.sleep(300)  # Clean up every 5 minutes

            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(300)

    async def _discover_agents(self) -> Dict[str, Path]:
        """Discover all agent worktrees"""
        agents = {}

        # Check standard worktrees
        if self.worktrees_dir.exists():
            for worktree_dir in self.worktrees_dir.iterdir():
                if worktree_dir.is_dir() and (worktree_dir / "CLAUDE.md").exists():
                    agents[worktree_dir.name] = worktree_dir

        # Check new worktrees
        if self.new_worktrees_dir.exists():
            for worktree_dir in self.new_worktrees_dir.iterdir():
                if worktree_dir.is_dir() and (worktree_dir / "CLAUDE.md").exists():
                    agents[worktree_dir.name] = worktree_dir

        return agents

    async def _get_git_activity(
            self, agent_name: str, agent_path: Path) -> Optional[Dict[str, Any]]:
        """Get git activity for an agent"""
        try:
            # Get recent commits
            result = await self._run_command([
                "git", "log", "--oneline", "--since=1 hour ago", "--author=*"
            ], cwd=agent_path)

            if result.returncode == 0 and result.stdout.strip():
                commits = result.stdout.strip().split('\n')

                # Get file changes
                diff_result = await self._run_command([
                    "git", "diff", "--stat", "HEAD~1", "HEAD"
                ], cwd=agent_path)

                lines_changed = 0
                if diff_result.returncode == 0 and diff_result.stdout:
                    # Parse git diff stat output
                    lines = diff_result.stdout.strip().split('\n')
                    if lines:
                        last_line = lines[-1]
                        if "insertion" in last_line or "deletion" in last_line:
                            parts = last_line.split()
                            for part in parts:
                                if part.isdigit():
                                    lines_changed += int(part)

                return {
                    "recent_commits": len(commits),
                    "commit_messages": commits[:5],  # Last 5 commits
                    "lines_changed": lines_changed,
                    "branch": await self._get_current_branch(agent_path)
                }

        except Exception as e:
            logger.warning(f"Error getting git activity for {agent_name}: {e}")

        return None

    async def _get_task_progress(
            self, agent_name: str, agent_path: Path) -> Optional[Dict[str, Any]]:
        """Get task progress for an agent"""
        try:
            # Check for TODO/FIXME comments
            result = await self._run_command([
                "grep", "-r", "--include=*.py", "-n", "TODO\\|FIXME\\|XXX", "."
            ], cwd=agent_path)

            todos = []
            if result.returncode == 0:
                todos = result.stdout.strip().split(
                    '\n')[:10]  # First 10 todos

            # Check for recent file modifications
            mod_result = await self._run_command([
                "find", ".", "-name", "*.py", "-mtime", "-1"
            ], cwd=agent_path)

            modified_files = []
            if mod_result.returncode == 0:
                modified_files = mod_result.stdout.strip().split('\n')

            return {
                "todo_count": len(todos),
                "todos": todos,
                "recently_modified": len(modified_files),
                "modified_files": modified_files
            }

        except Exception as e:
            logger.warning(
                f"Error getting task progress for {agent_name}: {e}")

        return None

    async def _get_current_branch(self, repo_path: Path) -> str:
        """Get current git branch"""
        try:
            result = await self._run_command(["git", "branch", "--show-current"], cwd=repo_path)
            if result.returncode == 0:
                return result.stdout.strip()
        except BaseException:
            pass
        return "unknown"

    async def _run_command(
            self,
            cmd: List[str],
            cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        """Run a command asynchronously"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        stdout, stderr = await process.communicate()

        return subprocess.CompletedProcess(
            cmd, process.returncode, stdout.decode(), stderr.decode()
        )

    def _add_activity(self, activity: AgentActivity):
        """Add activity to tracking"""
        self.activities.append(activity)

        # Update agent metrics
        if activity.agent_name in self.agent_metrics:
            metrics = self.agent_metrics[activity.agent_name]

            if activity.activity_type == "git":
                metrics.git_commits_today += activity.details.get(
                    "recent_commits", 0)
                metrics.lines_changed_today += activity.details.get(
                    "lines_changed", 0)

            metrics.last_activity = activity.timestamp

            # Calculate health score
            metrics.health_score = self._calculate_health_score(metrics)

    def _calculate_health_score(self, metrics: AgentMetrics) -> float:
        """Calculate agent health score"""
        score = 100.0

        # Penalize high resource usage
        if metrics.cpu_percent > 80:
            score -= 20
        elif metrics.cpu_percent > 60:
            score -= 10

        if metrics.memory_percent > 80:
            score -= 20
        elif metrics.memory_percent > 60:
            score -= 10

        # Reward recent activity
        time_since_activity = (
            datetime.now() - metrics.last_activity).total_seconds()
        if time_since_activity > 3600:  # 1 hour
            score -= 30
        elif time_since_activity > 1800:  # 30 minutes
            score -= 15

        # Reward productivity
        if metrics.git_commits_today > 5:
            score += 10
        elif metrics.git_commits_today > 2:
            score += 5

        return max(0, min(100, score))

    def get_recent_activities(
            self, limit: int = 50, agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent activities"""
        activities = self.activities

        if agent_name:
            activities = [a for a in activities if a.agent_name == agent_name]

        # Sort by timestamp, most recent first
        activities.sort(key=lambda x: x.timestamp, reverse=True)

        return [activity.to_dict() for activity in activities[:limit]]

    def get_agent_metrics(
            self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Get agent metrics"""
        if agent_name:
            return self.agent_metrics.get(agent_name, {}).to_dict(
            ) if agent_name in self.agent_metrics else {}

        return {name: metrics.to_dict()
                for name, metrics in self.agent_metrics.items()}

    def get_system_overview(self) -> Dict[str, Any]:
        """Get system overview"""
        total_agents = len(self.agent_metrics)
        active_agents = sum(1 for m in self.agent_metrics.values() if (
            datetime.now() - m.last_activity).total_seconds() < 3600)

        avg_health = sum(
            m.health_score for m in self.agent_metrics.values()) / max(total_agents, 1)

        total_commits = sum(
            m.git_commits_today for m in self.agent_metrics.values())
        total_lines = sum(
            m.lines_changed_today for m in self.agent_metrics.values())

        return {
            "total_agents": total_agents,
            "active_agents": active_agents,
            "average_health_score": round(avg_health, 1),
            "total_commits_today": total_commits,
            "total_lines_changed_today": total_lines,
            "monitoring_uptime": time.time(),
            "activity_count": len(self.activities)
        }


# Global monitor instance
monitor = RealtimeAgentMonitor()


async def main():
    """Main function for standalone monitoring"""
    await monitor.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
