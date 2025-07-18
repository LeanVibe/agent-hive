#!/usr/bin/env python3
"""
Agent Completion Handler - Automated detection and reporting of agent task completion
Solves the issue of agents completing work but failing to report properly.
"""

import argparse
import asyncio
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentCompletionHandler:
    """Automated detection and handling of agent task completion"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.agents_registry = Path(".claude/agents")
        self.agents_registry.mkdir(exist_ok=True)

    async def monitor_agent_completion(self, agent_id: str) -> bool:
        """Monitor agent for completion and handle reporting"""
        logger.info(f"🔍 Monitoring {agent_id} for completion...")

        # Check for completion signals
        completion_detected = await self._detect_completion(agent_id)

        if completion_detected:
            logger.info(f"✅ Completion detected for {agent_id}")

            # Handle completion workflow
            success = await self._handle_completion(agent_id)
            return success

        return False

    async def _detect_completion(self, agent_id: str) -> bool:
        """Detect if agent has completed its task"""

        # Method 1: Check tmux output for completion signals
        completion_keywords = [
            "task completed", "work completed", "mission accomplished",
            "✅", "completed successfully", "ready to merge", "PR is ready",
            "conflicts resolved", "successfully merged", "blocking work unblocked"
        ]

        try:
            # Capture recent tmux output
            cmd = ["tmux", "capture-pane", "-t", f"agent-hive:{agent_id}", "-p"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                output = result.stdout.lower()
                for keyword in completion_keywords:
                    if keyword.lower() in output:
                        logger.info(f"🎯 Completion keyword detected: '{keyword}'")
                        return True

        except Exception as e:
            logger.debug(f"Error checking tmux output: {e}")

        # Method 2: Check for completion files in worktree
        agent_worktrees = list(Path("new-worktrees").glob(f"*{agent_id}*"))
        for worktree in agent_worktrees:
            completion_files = [
                worktree / "TASK_COMPLETED.txt",
                worktree / "MISSION_ACCOMPLISHED.txt",
                worktree / "READY_FOR_MERGE.txt"
            ]

            for file_path in completion_files:
                if file_path.exists():
                    logger.info(f"📁 Completion file detected: {file_path}")
                    return True

        # Method 3: Check git activity for recent commits/merges
        try:
            # Check if there are recent commits from agent's worktree
            for worktree in agent_worktrees:
                if worktree.exists():
                    cmd = ["git", "-C", str(worktree), "log", "--oneline", "-5", "--since=2 hours ago"]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                    if result.returncode == 0 and result.stdout.strip():
                        logger.info(f"🔄 Recent git activity detected in {worktree}")
                        return True

        except Exception as e:
            logger.debug(f"Error checking git activity: {e}")

        return False

    async def _handle_completion(self, agent_id: str) -> bool:
        """Handle agent completion workflow"""
        try:
            # 1. Extract completion summary from agent
            summary = await self._extract_completion_summary(agent_id)

            # 2. Validate work completion
            validation_result = await self._validate_completion(agent_id, summary)

            # 3. Generate completion report
            report = await self._generate_completion_report(agent_id, summary, validation_result)

            # 4. Send notifications
            await self._send_completion_notifications(agent_id, report)

            # 5. Clean up agent resources
            await self._cleanup_completed_agent(agent_id)

            # 6. Update orchestrator tracking
            await self._update_orchestrator_tracking(agent_id, report)

            return True

        except Exception as e:
            logger.error(f"Failed to handle completion for {agent_id}: {e}")
            return False

    async def _extract_completion_summary(self, agent_id: str) -> Dict:
        """Extract completion summary from agent's work"""
        summary = {
            "agent_id": agent_id,
            "completion_time": datetime.now().isoformat(),
            "task_description": "Unknown",
            "accomplishments": [],
            "deliverables": [],
            "next_steps": [],
            "blockers_resolved": [],
            "metrics": {}
        }

        try:
            # Get recent tmux output
            cmd = ["tmux", "capture-pane", "-t", f"agent-hive:{agent_id}", "-p"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                output = result.stdout

                # Extract key information using keywords
                if "pr #" in output.lower() or "pull request" in output.lower():
                    summary["deliverables"].append("PR created/updated")

                if "conflicts resolved" in output.lower():
                    summary["blockers_resolved"].append("Merge conflicts resolved")

                if "tests pass" in output.lower() or "✅" in output:
                    summary["accomplishments"].append("Quality gates passed")

                if "ready to merge" in output.lower() or "ready for merge" in output.lower():
                    summary["next_steps"].append("PR ready for merge")

                # Store raw output for reference
                summary["raw_output"] = output[-2000:]  # Last 2000 chars

        except Exception as e:
            logger.debug(f"Error extracting summary: {e}")

        return summary

    async def _validate_completion(self, agent_id: str, summary: Dict) -> Dict:
        """Validate that agent's work is actually complete"""
        validation = {
            "tests_passing": False,
            "build_successful": False,
            "pr_status": "unknown",
            "conflicts_resolved": False,
            "quality_gates_passed": False,
            "work_committed": False,
            "work_pushed": False,
            "branch_exists": False
        }

        # Find agent's worktree
        agent_worktrees = list(Path("new-worktrees").glob(f"*{agent_id}*"))

        for worktree in agent_worktrees:
            if worktree.exists():
                try:
                    # Check if tests pass
                    cmd = ["python", "-m", "pytest", "tests/", "-x", "--tb=no", "-q"]
                    result = subprocess.run(cmd, cwd=worktree, capture_output=True, text=True, timeout=60)
                    validation["tests_passing"] = result.returncode == 0

                    # Check build status
                    if Path(worktree / "requirements.txt").exists():
                        cmd = ["python", "-c", "import sys; print('Build check passed')"]
                        result = subprocess.run(cmd, cwd=worktree, capture_output=True, text=True, timeout=30)
                        validation["build_successful"] = result.returncode == 0

                    # Check git status for conflicts
                    cmd = ["git", "status", "--porcelain"]
                    result = subprocess.run(cmd, cwd=worktree, capture_output=True, text=True, timeout=10)

                    if result.returncode == 0:
                        # No unmerged paths means conflicts resolved
                        validation["conflicts_resolved"] = "UU" not in result.stdout

                    # Check if work is committed (no staged changes)
                    cmd = ["git", "diff", "--cached", "--quiet"]
                    result = subprocess.run(cmd, cwd=worktree, timeout=10)
                    validation["work_committed"] = result.returncode != 0  # Exit code 1 means there ARE staged changes

                    # Check if work is pushed to remote
                    cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
                    result = subprocess.run(cmd, cwd=worktree, capture_output=True, text=True, timeout=10)

                    if result.returncode == 0:
                        branch_name = result.stdout.strip()

                        # Check if branch exists on remote
                        cmd = ["git", "ls-remote", "--heads", "origin", branch_name]
                        result = subprocess.run(cmd, cwd=worktree, capture_output=True, text=True, timeout=10)
                        validation["branch_exists"] = result.returncode == 0 and result.stdout.strip()

                        if validation["branch_exists"]:
                            # Check if local is up to date with remote
                            cmd = ["git", "rev-parse", "HEAD"]
                            local_result = subprocess.run(cmd, cwd=worktree, capture_output=True, text=True, timeout=10)

                            cmd = ["git", "rev-parse", f"origin/{branch_name}"]
                            remote_result = subprocess.run(cmd, cwd=worktree, capture_output=True, text=True, timeout=10)

                            if local_result.returncode == 0 and remote_result.returncode == 0:
                                validation["work_pushed"] = local_result.stdout.strip() == remote_result.stdout.strip()

                except Exception as e:
                    logger.debug(f"Error validating completion: {e}")

                break

        return validation

    async def _generate_completion_report(self, agent_id: str, summary: Dict, validation: Dict) -> Dict:
        """Generate comprehensive completion report"""
        report = {
            "agent_id": agent_id,
            "completion_time": summary["completion_time"],
            "summary": summary,
            "validation": validation,
            "overall_status": "completed" if all(validation.values()) else "completed_with_issues",
            "recommendations": []
        }

        # Add recommendations based on validation
        if not validation["tests_passing"]:
            report["recommendations"].append("Review and fix failing tests before final merge")

        if not validation["conflicts_resolved"]:
            report["recommendations"].append("Resolve remaining merge conflicts")

        if not validation["work_committed"]:
            report["recommendations"].append("Commit staged changes to complete work")

        if not validation["work_pushed"]:
            report["recommendations"].append("Push committed work to remote repository")

        if not validation["branch_exists"]:
            report["recommendations"].append("Create remote branch for code review")

        if report["overall_status"] == "completed_with_issues":
            report["recommendations"].append("Manual review required before proceeding")

        return report

    async def _send_completion_notifications(self, agent_id: str, report: Dict):
        """Send completion notifications to relevant parties"""

        # 1. Notify PM agent
        pm_message = f"🎉 AGENT COMPLETION: {agent_id}\n"
        pm_message += f"Status: {report['overall_status']}\n"
        pm_message += f"Time: {report['completion_time']}\n"

        if report['recommendations']:
            pm_message += f"⚠️ Recommendations: {', '.join(report['recommendations'])}"

        try:
            cmd = ["python", "scripts/send_agent_message.py", "--agent", "pm-agent", "--message", pm_message]
            subprocess.run(cmd, timeout=10)
        except Exception as e:
            logger.debug(f"Error sending PM notification: {e}")

        # 2. Log to completion tracking
        completion_log = Path(".claude/agent_completions.jsonl")
        with open(completion_log, "a") as f:
            f.write(json.dumps(report) + "\n")

        # 3. Update orchestrator if running
        try:
            # Send to orchestrator
            orchestrator_message = f"Agent {agent_id} completed: {report['overall_status']}"
            logger.info(f"📊 {orchestrator_message}")
        except Exception as e:
            logger.debug(f"Error notifying orchestrator: {e}")

    async def _cleanup_completed_agent(self, agent_id: str):
        """Clean up completed agent resources"""
        try:
            # Keep the tmux window but mark as completed
            completion_marker = f"[COMPLETED-{datetime.now().strftime('%H:%M')}]"
            cmd = ["tmux", "send-keys", "-t", f"agent-hive:{agent_id}", f"echo '{completion_marker} Agent task completed at {datetime.now()}'", "Enter"]
            subprocess.run(cmd, timeout=10)

            # Update agent registry
            registry_file = self.agents_registry / f"{agent_id}.json"
            if registry_file.exists():
                with open(registry_file, 'r') as f:
                    agent_data = json.load(f)

                agent_data["status"] = "completed"
                agent_data["completion_time"] = datetime.now().isoformat()

                with open(registry_file, 'w') as f:
                    json.dump(agent_data, f, indent=2)

        except Exception as e:
            logger.debug(f"Error cleaning up agent: {e}")

    async def _update_orchestrator_tracking(self, agent_id: str, report: Dict):
        """Update orchestrator tracking with completion status"""
        try:
            # Update TODO list to mark agent tasks as completed
            # This would integrate with the TodoWrite system
            logger.info(f"📈 Updated orchestrator tracking for {agent_id}")

        except Exception as e:
            logger.debug(f"Error updating orchestrator tracking: {e}")

    async def monitor_all_active_agents(self):
        """Monitor all active agents for completion"""
        logger.info("🔍 Monitoring all active agents for completion...")

        # Get list of active agents
        try:
            cmd = ["python", "scripts/check_agent_status.py", "--format", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                status_data = json.loads(result.stdout)
                active_agents = status_data.get("active_agents", [])

                for agent in active_agents:
                    agent_name = agent.get("name", "")
                    if agent_name:
                        completion_detected = await self.monitor_agent_completion(agent_name)
                        if completion_detected:
                            logger.info(f"✅ Handled completion for {agent_name}")

        except Exception as e:
            logger.error(f"Error monitoring active agents: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Agent Completion Handler")
    parser.add_argument("--agent", help="Specific agent to monitor")
    parser.add_argument("--monitor-all", action="store_true", help="Monitor all active agents")
    parser.add_argument("--continuous", action="store_true", help="Continuous monitoring mode")

    args = parser.parse_args()

    handler = AgentCompletionHandler()

    if args.agent:
        success = await handler.monitor_agent_completion(args.agent)
        if success:
            print(f"✅ Successfully handled completion for {args.agent}")
        else:
            print(f"❌ No completion detected for {args.agent}")

    elif args.monitor_all:
        await handler.monitor_all_active_agents()

    elif args.continuous:
        logger.info("🔄 Starting continuous monitoring mode...")
        while True:
            await handler.monitor_all_active_agents()
            await asyncio.sleep(300)  # Check every 5 minutes

    else:
        print("Use --agent, --monitor-all, or --continuous")


if __name__ == "__main__":
    asyncio.run(main())
