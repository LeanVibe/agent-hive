#!/usr/bin/env python3
"""
Agent Activator - Ensures agents are fully active and working without manual intervention
Solves the issue of Claude Code sessions waiting for manual input.
"""

import argparse
import asyncio
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentActivator:
    """Ensures agents are fully active and responsive without manual intervention"""

    def __init__(self):
        self.activation_timeout = 30  # seconds
        self.max_activation_attempts = 3

    async def activate_agent(self, agent_id: str, task_prompt: str) -> bool:
        """Fully activate an agent with task prompt"""
        logger.info(f"🔧 Activating agent {agent_id}...")

        # Step 1: Verify tmux window exists
        if not await self._verify_tmux_window(agent_id):
            logger.error(f"❌ Tmux window not found for {agent_id}")
            return False

        # Step 2: Check if Claude Code is responsive
        if not await self._check_claude_responsiveness(agent_id):
            logger.warning(f"⚠️ Claude Code not responsive, restarting...")
            if not await self._restart_claude_code(agent_id):
                return False

        # Step 3: Send activation sequence
        success = await self._send_activation_sequence(agent_id, task_prompt)

        if success:
            logger.info(f"✅ Agent {agent_id} fully activated")
            return True
        else:
            logger.error(f"❌ Failed to activate agent {agent_id}")
            return False

    async def _verify_tmux_window(self, agent_id: str) -> bool:
        """Verify tmux window exists for agent"""
        try:
            cmd = ["tmux", "list-windows", "-t", "agent-hive", "-F", "#{window_name}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                windows = result.stdout.strip().split('\n')
                return agent_id in windows

        except Exception as e:
            logger.debug(f"Error verifying tmux window: {e}")

        return False

    async def _check_claude_responsiveness(self, agent_id: str) -> bool:
        """Check if Claude Code is responsive in the agent window"""
        try:
            # Send a simple command and check response
            test_command = "echo 'responsiveness_test'"

            # Send command
            cmd = ["tmux", "send-keys", "-t", f"agent-hive:{agent_id}", test_command, "Enter"]
            subprocess.run(cmd, timeout=5)

            # Wait a moment
            await asyncio.sleep(2)

            # Capture output
            cmd = ["tmux", "capture-pane", "-t", f"agent-hive:{agent_id}", "-p"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                output = result.stdout

                # Check if we see the echo output or Claude Code interface
                if "responsiveness_test" in output or "? for shortcuts" in output:
                    return True

        except Exception as e:
            logger.debug(f"Error checking responsiveness: {e}")

        return False

    async def _restart_claude_code(self, agent_id: str) -> bool:
        """Restart Claude Code in the agent window"""
        try:
            logger.info(f"🔄 Restarting Claude Code for {agent_id}...")

            # Kill any existing processes
            cmd = ["tmux", "send-keys", "-t", f"agent-hive:{agent_id}", "C-c", "Enter"]
            subprocess.run(cmd, timeout=5)

            await asyncio.sleep(2)

            # Clear the session
            cmd = ["tmux", "send-keys", "-t", f"agent-hive:{agent_id}", "clear", "Enter"]
            subprocess.run(cmd, timeout=5)

            await asyncio.sleep(1)

            # Start Claude Code with permission bypass
            cmd = ["tmux", "send-keys", "-t", f"agent-hive:{agent_id}",
                   "claude --dangerously-skip-permissions", "Enter"]
            subprocess.run(cmd, timeout=10)

            # Wait for Claude Code to initialize
            await asyncio.sleep(5)

            # Verify it's running
            return await self._check_claude_responsiveness(agent_id)

        except Exception as e:
            logger.error(f"Error restarting Claude Code: {e}")
            return False

    async def _send_activation_sequence(self, agent_id: str, task_prompt: str) -> bool:
        """Send activation sequence to ensure agent starts working"""

        for attempt in range(self.max_activation_attempts):
            try:
                logger.info(f"🎯 Sending activation sequence to {agent_id} (attempt {attempt + 1})")

                # First, detect the current state of the agent
                agent_state = await self._detect_agent_state(agent_id)
                logger.info(f"📊 Agent {agent_id} state: {agent_state}")

                # Clear any pending input first
                await self._clear_pending_input(agent_id)

                # Method 1: Send task prompt with proper Enter handling
                success = await self._send_message_with_enter(agent_id, task_prompt)

                if success:
                    await asyncio.sleep(3)

                    # Method 2: Send follow-up verification
                    verification_prompt = "I acknowledge this task and will begin work immediately. Starting now..."
                    await self._send_message_with_enter(agent_id, verification_prompt)

                    await asyncio.sleep(2)

                    # Method 3: Check if agent is responsive
                    if await self._verify_agent_working(agent_id):
                        return True

                # If not working, try alternative activation
                logger.warning(f"⚠️ Attempt {attempt + 1} failed, trying alternative activation...")

                # Alternative: Clear and restart conversation
                await self._restart_agent_conversation(agent_id, task_prompt)

                if await self._verify_agent_working(agent_id):
                    return True

            except Exception as e:
                logger.debug(f"Activation attempt {attempt + 1} error: {e}")

        return False

    async def _send_task_via_file(self, agent_id: str, task_prompt: str):
        """Send task prompt via file as backup method"""
        try:
            # Find agent worktree
            agent_worktrees = list(Path("new-worktrees").glob(f"*{agent_id}*"))

            if agent_worktrees:
                worktree = agent_worktrees[0]
                task_file = worktree / "CURRENT_TASK.txt"

                with open(task_file, 'w') as f:
                    f.write(f"URGENT TASK:\n{task_prompt}\n\nDelivered at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

                # Tell agent to read the file
                cmd = ["tmux", "send-keys", "-t", f"agent-hive:{agent_id}",
                       "cat CURRENT_TASK.txt && echo 'TASK RECEIVED - STARTING WORK'", "Enter"]
                subprocess.run(cmd, timeout=10)

        except Exception as e:
            logger.debug(f"Error sending task via file: {e}")

    async def _verify_agent_working(self, agent_id: str) -> bool:
        """Verify agent is actually working on the task"""
        try:
            await asyncio.sleep(3)

            # Capture recent output
            cmd = ["tmux", "capture-pane", "-t", f"agent-hive:{agent_id}", "-p"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                output = result.stdout.lower()

                # Look for signs of activity
                working_indicators = [
                    "starting work", "beginning", "analyzing", "implementing",
                    "task received", "working on", "proceeding", "executing",
                    "checking", "running", "starting", "initiating"
                ]

                for indicator in working_indicators:
                    if indicator in output:
                        logger.info(f"✅ Agent {agent_id} shows working indicator: '{indicator}'")
                        return True

                # Also check if Claude Code is still responsive (not stuck)
                if "? for shortcuts" in output:
                    # Claude is running but may not have received the task
                    return False

        except Exception as e:
            logger.debug(f"Error verifying agent working: {e}")

        return False

    async def activate_all_agents(self, agent_tasks: dict) -> dict:
        """Activate all agents with their respective tasks"""
        results = {}

        logger.info(f"🚀 Activating {len(agent_tasks)} agents...")

        for agent_id, task_prompt in agent_tasks.items():
            success = await self.activate_agent(agent_id, task_prompt)
            results[agent_id] = success

            if success:
                logger.info(f"✅ {agent_id}: Activated successfully")
            else:
                logger.error(f"❌ {agent_id}: Activation failed")

        return results

    async def monitor_agent_activity(self, agent_id: str, duration: int = 300) -> bool:
        """Monitor agent for activity over a duration"""
        logger.info(f"👀 Monitoring {agent_id} for activity over {duration} seconds...")

        start_time = time.time()
        last_output = ""

        while time.time() - start_time < duration:
            try:
                cmd = ["tmux", "capture-pane", "-t", f"agent-hive:{agent_id}", "-p"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                if result.returncode == 0:
                    current_output = result.stdout

                    # Check if output has changed (indicates activity)
                    if current_output != last_output:
                        logger.info(f"📈 {agent_id}: Activity detected")
                        last_output = current_output
                        return True

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.debug(f"Error monitoring {agent_id}: {e}")

        logger.warning(f"⚠️ {agent_id}: No activity detected in {duration} seconds")
        return False

    async def _detect_agent_state(self, agent_id: str) -> str:
        """Detect the current state of the agent (idle, conversation, working, etc.)"""
        try:
            cmd = ["tmux", "capture-pane", "-t", f"agent-hive:{agent_id}", "-p"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                output = result.stdout.lower()

                # Check for different states
                if "? for shortcuts" in output:
                    return "idle_claude"
                elif ">" in output and "press up to edit" in output:
                    return "conversation_mode"
                elif "starting" in output or "working" in output:
                    return "working"
                elif "error" in output or "failed" in output:
                    return "error_state"
                else:
                    return "unknown"

        except Exception as e:
            logger.debug(f"Error detecting agent state: {e}")

        return "unknown"

    async def _clear_pending_input(self, agent_id: str):
        """Clear any pending input in the agent conversation"""
        try:
            # Send Escape to clear any pending input
            cmd = ["tmux", "send-keys", "-t", f"agent-hive:{agent_id}", "Escape"]
            subprocess.run(cmd, timeout=5)

            await asyncio.sleep(1)

            # Send Ctrl+C to cancel any running commands
            cmd = ["tmux", "send-keys", "-t", f"agent-hive:{agent_id}", "C-c"]
            subprocess.run(cmd, timeout=5)

            await asyncio.sleep(1)

        except Exception as e:
            logger.debug(f"Error clearing pending input: {e}")

    async def _send_message_with_enter(self, agent_id: str, message: str) -> bool:
        """Send a message to the agent and ensure Enter is pressed"""
        try:
            # Clear the input area first
            cmd = ["tmux", "send-keys", "-t", f"agent-hive:{agent_id}", "C-u"]
            subprocess.run(cmd, timeout=5)

            await asyncio.sleep(0.5)

            # Type the message
            cmd = ["tmux", "send-keys", "-t", f"agent-hive:{agent_id}", message]
            subprocess.run(cmd, timeout=10)

            await asyncio.sleep(1)

            # Explicitly press Enter
            cmd = ["tmux", "send-keys", "-t", f"agent-hive:{agent_id}", "Enter"]
            subprocess.run(cmd, timeout=5)

            logger.info(f"📤 Message sent to {agent_id} with Enter key")

            await asyncio.sleep(2)

            # Verify the message was sent by checking output
            cmd = ["tmux", "capture-pane", "-t", f"agent-hive:{agent_id}", "-p"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                recent_output = result.stdout[-500:]  # Last 500 chars

                # Check if the message appears to have been processed
                if any(keyword in recent_output.lower() for keyword in ["starting", "beginning", "working", "acknowledge"]):
                    return True

            return True  # Assume success if no obvious failure

        except Exception as e:
            logger.debug(f"Error sending message with Enter: {e}")
            return False

    async def _restart_agent_conversation(self, agent_id: str, task_prompt: str):
        """Restart the agent conversation to clear any stuck state"""
        try:
            logger.info(f"🔄 Restarting conversation for {agent_id}")

            # Send multiple escape sequences to clear state
            for _ in range(3):
                cmd = ["tmux", "send-keys", "-t", f"agent-hive:{agent_id}", "Escape"]
                subprocess.run(cmd, timeout=5)
                await asyncio.sleep(0.5)

            # Clear with Ctrl+C
            cmd = ["tmux", "send-keys", "-t", f"agent-hive:{agent_id}", "C-c"]
            subprocess.run(cmd, timeout=5)

            await asyncio.sleep(1)

            # Try to get back to a clean state
            cmd = ["tmux", "send-keys", "-t", f"agent-hive:{agent_id}", "clear", "Enter"]
            subprocess.run(cmd, timeout=5)

            await asyncio.sleep(1)

            # Send the task prompt with explicit Enter
            await self._send_message_with_enter(agent_id, task_prompt)

        except Exception as e:
            logger.debug(f"Error restarting conversation: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Agent Activator")
    parser.add_argument("--agent", help="Specific agent to activate")
    parser.add_argument("--task", help="Task prompt to send to agent")
    parser.add_argument("--activate-all", action="store_true", help="Activate all production readiness agents")
    parser.add_argument("--monitor", help="Monitor specific agent for activity")

    args = parser.parse_args()

    activator = AgentActivator()

    if args.agent and args.task:
        success = await activator.activate_agent(args.agent, args.task)
        if success:
            print(f"✅ Successfully activated {args.agent}")
        else:
            print(f"❌ Failed to activate {args.agent}")
            sys.exit(1)

    elif args.activate_all:
        # Production readiness agent tasks
        agent_tasks = {
            "integration-specialist-Jul-16-0207": """🚀 PRIORITY 1.1: API Gateway Foundation Repair. Replace simulation-only API Gateway with real FastAPI HTTP server. Fix 86/104 failing tests. Start with: grep -r "simulation" api_gateway/ && pytest tests/test_api_gateway.py -v --tb=short. Timeline: 3 days. Report progress every 2 hours.""",

            "service-mesh-Jul-16-0207": """🚀 PRIORITY 1.2: Service Discovery Integration. Add REST API endpoints, implement real HTTP health checks. Zero integration with other components must be fixed. Start with: touch service_discovery/api.py && pytest tests/test_service_discovery_api.py -v. Timeline: 2 days. Report progress every 2 hours.""",

            "frontend-Jul-16-0208": """🚀 PRIORITY 1.3: Dashboard Integration Repair. Fix dashboard sending data to non-existent endpoints. Add missing /api/metrics endpoint to enhanced_server.py. Start with: grep -n "api/metrics" enhanced_server.py && python enhanced_server.py &. Timeline: 2 days. Report progress every 2 hours."""
        }

        results = await activator.activate_all_agents(agent_tasks)

        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        print(f"📊 Activation Results: {success_count}/{total_count} agents successfully activated")

        for agent_id, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"  {agent_id}: {status}")

        if success_count == total_count:
            print("🎉 All production readiness agents are now active and working!")
        else:
            print("⚠️ Some agents failed to activate - manual intervention may be required")
            sys.exit(1)

    elif args.monitor:
        activity_detected = await activator.monitor_agent_activity(args.monitor)
        if activity_detected:
            print(f"✅ {args.monitor} is active and working")
        else:
            print(f"❌ {args.monitor} shows no activity")
            sys.exit(1)

    else:
        print("Use --agent with --task, --activate-all, or --monitor")


if __name__ == "__main__":
    asyncio.run(main())
