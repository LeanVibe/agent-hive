#!/usr/bin/env python3
"""
Enhanced Agent Communication with Webhook Integration
Handles agent communication with webhook triggers for automated task assignment
"""

import subprocess
import time
import sys
import argparse
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime


class WebhookAgentCommunicator:
    """
    Enhanced agent communication with webhook integration for automated task assignment.
    """

    def __init__(self, webhook_url: str = "http://localhost:8001/webhooks",
                 api_url: str = "http://localhost:8000/api"):
        """
        Initialize webhook-enabled agent communicator.

        Args:
            webhook_url: Base URL for webhook endpoints
            api_url: Base URL for API endpoints
        """
        self.webhook_url = webhook_url
        self.api_url = api_url
        self.active_agents = [
            "integration-specialist-Jul-16-1220",
            "service-mesh-Jul-16-1221",
            "frontend-Jul-16-1222",
            "pm-agent-new"
        ]
        self.confidence_thresholds = {
            "low": 0.6,
            "medium": 0.75,
            "high": 0.9
        }

    async def send_webhook_notification(self, event_type: str, data: Dict[str, Any],
                                      priority: str = "medium") -> bool:
        """
        Send webhook notification for automated task assignment.

        Args:
            event_type: Type of webhook event
            data: Event data payload
            priority: Event priority level

        Returns:
            bool: Success status
        """
        try:
            payload = {
                "type": event_type,
                "data": data,
                "priority": priority,
                "source": "agent_communication_system",
                "timestamp": datetime.now().isoformat()
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.webhook_url}/{event_type}",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        print(f"✅ Webhook sent successfully: {event_type}")
                        return True
                    else:
                        print(f"❌ Webhook failed: {response.status}")
                        return False

        except Exception as e:
            print(f"❌ Webhook error: {e}")
            return False

    async def trigger_automated_task_assignment(self, task_description: str,
                                              required_skills: List[str],
                                              confidence_threshold: float = 0.75) -> Dict[str, Any]:
        """
        Trigger automated task assignment via webhook system.

        Args:
            task_description: Description of the task
            required_skills: Required skills for the task
            confidence_threshold: Minimum confidence threshold

        Returns:
            Assignment result
        """
        task_data = {
            "task_id": f"task_{int(time.time())}",
            "description": task_description,
            "required_skills": required_skills,
            "confidence_threshold": confidence_threshold,
            "created_at": datetime.now().isoformat(),
            "available_agents": self.active_agents
        }

        # Send task creation webhook
        webhook_success = await self.send_webhook_notification(
            "task_created",
            task_data,
            "high" if confidence_threshold > 0.85 else "medium"
        )

        if webhook_success:
            print(f"📋 Task created and broadcasted: {task_data['task_id']}")

            # Wait for agent responses
            await asyncio.sleep(2)

            # Check assignment status
            assignment_result = await self._check_task_assignment(task_data["task_id"])
            return assignment_result
        else:
            return {"status": "failed", "message": "Webhook delivery failed"}

    async def _check_task_assignment(self, task_id: str) -> Dict[str, Any]:
        """Check task assignment status via API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/tasks/{task_id}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"status": "unknown", "task_id": task_id}
        except Exception as e:
            print(f"⚠️ Could not check assignment status: {e}")
            return {"status": "unknown", "task_id": task_id}

    async def notify_agent_status_change(self, agent_name: str, status: str,
                                       current_task: Optional[str] = None) -> bool:
        """
        Notify system of agent status change.

        Args:
            agent_name: Name of the agent
            status: New agent status
            current_task: Current task ID if any

        Returns:
            bool: Success status
        """
        status_data = {
            "agent_name": agent_name,
            "status": status,
            "current_task": current_task,
            "timestamp": datetime.now().isoformat()
        }

        return await self.send_webhook_notification("agent_status", status_data)

    async def optimize_confidence_thresholds(self) -> Dict[str, float]:
        """
        Optimize confidence thresholds based on PM workload reduction goals.

        Returns:
            Updated confidence thresholds
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/analytics/pm_workload",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        current_reduction = data.get("workload_reduction", 0)

                        # Adjust thresholds to reach 80% reduction goal
                        if current_reduction < 0.8:
                            # Lower thresholds to increase automation
                            self.confidence_thresholds["low"] = max(0.5, self.confidence_thresholds["low"] - 0.05)
                            self.confidence_thresholds["medium"] = max(0.65, self.confidence_thresholds["medium"] - 0.05)
                            self.confidence_thresholds["high"] = max(0.8, self.confidence_thresholds["high"] - 0.05)

                        print(f"📊 Confidence thresholds optimized for {current_reduction:.1%} PM workload reduction")
                        return self.confidence_thresholds

        except Exception as e:
            print(f"⚠️ Could not optimize thresholds: {e}")

        return self.confidence_thresholds


def send_message_to_agent_fixed(agent_name: str, message: str, auto_submit: bool = True) -> bool:
    """
    Send a message to an agent with automatic submission, handling both naming conventions.

    Args:
        agent_name: Target agent name (without agent- prefix)
        message: Message to send
        auto_submit: Whether to automatically submit with Enter

    Returns:
        bool: Success status
    """

    session_name = "agent-hive"

    # Try both naming conventions
    window_names_to_try = [
        f"agent-{agent_name}",  # New convention
        agent_name              # Current convention
    ]

    for window_name in window_names_to_try:
        try:
            print(f"📡 Trying to send message to {window_name}...")

            # Test if window exists first
            test_cmd = ["tmux", "list-windows", "-t", session_name, "-F", "#{window_name}"]
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)

            if window_name not in result.stdout:
                print(f"⚠️ Window {window_name} not found, trying next...")
                continue

            # Set the message in tmux buffer
            result = subprocess.run([
                "tmux", "set-buffer", message
            ], capture_output=True, text=True)

            if result.returncode != 0:
                print(f"❌ Failed to set buffer: {result.stderr}")
                continue

            # Clear any existing input first
            subprocess.run([
                "tmux", "send-keys", "-t", f"{session_name}:{window_name}", "C-c"
            ], capture_output=True)

            time.sleep(0.5)  # Brief pause to ensure clear

            # Paste the buffer content
            result = subprocess.run([
                "tmux", "paste-buffer", "-t", f"{session_name}:{window_name}"
            ], capture_output=True, text=True)

            if result.returncode != 0:
                print(f"❌ Failed to paste buffer: {result.stderr}")
                continue

            # Auto-submit if requested
            if auto_submit:
                time.sleep(0.2)  # Brief pause before Enter
                subprocess.run([
                    "tmux", "send-keys", "-t", f"{session_name}:{window_name}", "Enter"
                ], capture_output=True)

            print(f"✅ Message sent successfully to {agent_name} (window: {window_name})")
            return True

        except Exception as e:
            print(f"❌ Error with window {window_name}: {e}")
            continue

    print(f"❌ Failed to send message to {agent_name} - no working window found")
    return False

async def test_webhook_system():
    """Test webhook system with all 4 active agents."""
    print("🚀 Testing webhook system with active agents...")

    communicator = WebhookAgentCommunicator()

    # Test automated task assignment
    test_tasks = [
        {
            "description": "Fix API Gateway integration tests",
            "skills": ["python", "testing", "fastapi"],
            "threshold": 0.8
        },
        {
            "description": "Optimize service discovery performance",
            "skills": ["microservices", "performance", "kubernetes"],
            "threshold": 0.75
        },
        {
            "description": "Update frontend dashboard components",
            "skills": ["react", "frontend", "ui/ux"],
            "threshold": 0.7
        }
    ]

    results = []
    for i, task in enumerate(test_tasks):
        print(f"\n📋 Testing task assignment {i+1}/3: {task['description'][:50]}...")

        result = await communicator.trigger_automated_task_assignment(
            task["description"],
            task["skills"],
            task["threshold"]
        )
        results.append(result)

        # Brief pause between tasks
        await asyncio.sleep(1)

    # Test agent status notifications
    print("\n📡 Testing agent status notifications...")
    for agent in communicator.active_agents:
        await communicator.notify_agent_status_change(agent, "active")
        await asyncio.sleep(0.5)

    # Test confidence threshold optimization
    print("\n🎯 Testing confidence threshold optimization...")
    optimized_thresholds = await communicator.optimize_confidence_thresholds()

    print(f"\n✅ Webhook system test completed!")
    print(f"Tasks tested: {len(test_tasks)}")
    print(f"Agents notified: {len(communicator.active_agents)}")
    print(f"Optimized thresholds: {optimized_thresholds}")

    return results


def main():
    """Enhanced CLI interface with webhook support"""

    parser = argparse.ArgumentParser(description="Enhanced agent communication with webhook integration")

    # Traditional message sending
    parser.add_argument("--agent", help="Agent name to send message to")
    parser.add_argument("--message", help="Message to send")
    parser.add_argument("--no-auto-submit", action="store_true", help="Don't automatically submit with Enter")

    # Webhook functionality
    parser.add_argument("--webhook-test", action="store_true", help="Test webhook system with all agents")
    parser.add_argument("--task-assign", help="Trigger automated task assignment")
    parser.add_argument("--skills", nargs="+", help="Required skills for task assignment")
    parser.add_argument("--confidence", type=float, default=0.75, help="Confidence threshold (0.0-1.0)")
    parser.add_argument("--optimize-thresholds", action="store_true", help="Optimize confidence thresholds")
    parser.add_argument("--agent-status", nargs=2, metavar=("AGENT", "STATUS"), help="Update agent status")

    args = parser.parse_args()

    # Handle webhook testing
    if args.webhook_test:
        print("🔥 Starting webhook system integration test...")
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(test_webhook_system())

        success = all(r.get("status") != "failed" for r in results)
        print(f"\n{'✅ All tests passed!' if success else '❌ Some tests failed'}")
        sys.exit(0 if success else 1)

    # Handle automated task assignment
    if args.task_assign:
        if not args.skills:
            print("❌ --skills required for task assignment")
            sys.exit(1)

        async def assign_task():
            communicator = WebhookAgentCommunicator()
            result = await communicator.trigger_automated_task_assignment(
                args.task_assign, args.skills, args.confidence
            )
            print(f"📋 Task assignment result: {result}")
            return result.get("status") != "failed"

        loop = asyncio.get_event_loop()
        success = loop.run_until_complete(assign_task())
        sys.exit(0 if success else 1)

    # Handle threshold optimization
    if args.optimize_thresholds:
        async def optimize():
            communicator = WebhookAgentCommunicator()
            thresholds = await communicator.optimize_confidence_thresholds()
            print(f"🎯 Optimized thresholds: {thresholds}")
            return True

        loop = asyncio.get_event_loop()
        loop.run_until_complete(optimize())
        sys.exit(0)

    # Handle agent status update
    if args.agent_status:
        agent_name, status = args.agent_status

        async def update_status():
            communicator = WebhookAgentCommunicator()
            success = await communicator.notify_agent_status_change(agent_name, status)
            print(f"📡 Agent status update: {'✅ Success' if success else '❌ Failed'}")
            return success

        loop = asyncio.get_event_loop()
        success = loop.run_until_complete(update_status())
        sys.exit(0 if success else 1)

    # Traditional message sending (backwards compatibility)
    if args.agent and args.message:
        auto_submit = not args.no_auto_submit
        success = send_message_to_agent_fixed(args.agent, args.message, auto_submit)
        sys.exit(0 if success else 1)

    # Show help if no arguments provided
    parser.print_help()
    sys.exit(1)

if __name__ == "__main__":
    main()
