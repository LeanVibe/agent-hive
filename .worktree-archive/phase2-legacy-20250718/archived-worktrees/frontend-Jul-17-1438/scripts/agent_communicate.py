#!/usr/bin/env python3
"""
Agent-to-Agent Communication Helper

Simple script that agents can use to send messages to each other automatically.
"""

import subprocess
import time
import sys
from pathlib import Path

def send_to_agent(target_agent: str, message: str, from_agent: str = "unknown") -> bool:
    """
    Send a message from one agent to another with automatic submission.

    Usage from within an agent:
    ```bash
    python ../scripts/agent_communicate.py documentation-agent "Can you update the API docs for the new feature?"
    ```
    """

    window_name = f"agent-{target_agent}"
    session_name = "agent-hive"

    # Format the message with sender info
    formatted_message = f"""🤖 MESSAGE FROM {from_agent.upper()}:

{message}

Please respond when convenient. This message was sent automatically."""

    print(f"📡 Sending message from {from_agent} to {target_agent}...")

    # Log the communication
    try:
        sys.path.append(str(Path(__file__).parent.parent))
        from dashboard.prompt_logger import prompt_logger
        prompt_logger.log_prompt(
            f"{from_agent}-to-{target_agent}",
            formatted_message,
            "Agent-to-agent communication sent",
            True
        )
    except ImportError:
        pass  # Continue without logging

    try:
        # Use tmux buffer method for reliability
        result = subprocess.run([
            "tmux", "set-buffer", formatted_message
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Failed to set buffer: {result.stderr}")
            return False

        # Clear existing input
        subprocess.run([
            "tmux", "send-keys", "-t", f"{session_name}:{window_name}", "C-c"
        ], capture_output=True)

        time.sleep(0.3)

        # Paste message
        result = subprocess.run([
            "tmux", "paste-buffer", "-t", f"{session_name}:{window_name}"
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Failed to paste buffer: {result.stderr}")
            return False

        # Auto-submit
        time.sleep(0.2)
        subprocess.run([
            "tmux", "send-keys", "-t", f"{session_name}:{window_name}", "Enter"
        ], capture_output=True)

        print(f"✅ Message delivered to {target_agent}")
        return True

    except Exception as e:
        print(f"❌ Communication failed: {e}")
        return False

def main():
    """CLI interface for agent communication"""

    if len(sys.argv) < 3:
        print("Usage: python agent_communicate.py <target_agent> <message> [from_agent]")
        print("")
        print("Examples:")
        print("  python agent_communicate.py documentation-agent 'Please update API docs'")
        print("  python agent_communicate.py pm-agent 'Sprint planning needed' quality-agent")
        print("")
        print("Available agents:")
        print("  - documentation-agent")
        print("  - orchestration-agent")
        print("  - pm-agent")
        print("  - intelligence-agent")
        print("  - integration-agent")
        print("  - quality-agent")
        sys.exit(1)

    target_agent = sys.argv[1]
    message = sys.argv[2]
    from_agent = sys.argv[3] if len(sys.argv) > 3 else "unknown-agent"

    success = send_to_agent(target_agent, message, from_agent)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
