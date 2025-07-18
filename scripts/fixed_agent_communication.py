#!/usr/bin/env python3
"""
DEPRECATED: Use send_agent_message.py for new workflows. Only use this if window naming is inconsistent.

Fixed Agent Communication - Handles both prefixed and non-prefixed window names
Temporary fix until all agents use consistent naming
"""

import subprocess
import time
import sys
import argparse
from pathlib import Path


def send_message_to_agent_fixed(
    agent_name: str, message: str, auto_submit: bool = True
) -> bool:
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

    # Try multiple naming conventions including current window names
    window_names_to_try = [
        f"agent-{agent_name}",  # New convention
        agent_name,  # Current convention
    ]
    
    # Add current window mappings (including dynamic names)
    agent_window_mapping = {
        'security': ['SEC-Input-⏳', 'SEC-Audit-🚨', 'SEC-Audit-🎯🚨'],
        'performance': ['PERF-Input-⏳', 'PERF-Test-🚨', 'PERF-Test-🎯🚨'],
        'frontend': ['FE-Input-⏳', 'FE-Dashboard-🚨', 'FE-Dashboard-🎯🚨'],
        'pm-agent-new': ['PM-Input-⏳', 'PM-Coordinate-🚨', 'PM-Coordinate-🎯🚨']
    }
    
    if agent_name in agent_window_mapping:
        # Add all possible window names for this agent
        for window_name in agent_window_mapping[agent_name]:
            window_names_to_try.insert(0, window_name)

    for window_name in window_names_to_try:
        try:
            print(f"📡 Trying to send message to {window_name}...")

            # Test if window exists first
            test_cmd = [
                "tmux",
                "list-windows",
                "-t",
                session_name,
                "-F",
                "#{window_name}",
            ]
            result = subprocess.run(
                test_cmd, capture_output=True, text=True, timeout=10
            )

            if window_name not in result.stdout:
                print(f"⚠️ Window {window_name} not found, trying next...")
                continue

            # Set the message in tmux buffer
            result = subprocess.run(
                ["tmux", "set-buffer", message], capture_output=True, text=True
            )

            if result.returncode != 0:
                print(f"❌ Failed to set buffer: {result.stderr}")
                continue

            # Clear any existing input first
            subprocess.run(
                ["tmux", "send-keys", "-t", f"{session_name}:{window_name}", "C-c"],
                capture_output=True,
            )

            time.sleep(0.5)  # Brief pause to ensure clear

            # Paste the buffer content
            result = subprocess.run(
                ["tmux", "paste-buffer", "-t", f"{session_name}:{window_name}"],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                print(f"❌ Failed to paste buffer: {result.stderr}")
                continue

            # Auto-submit if requested
            if auto_submit:
                time.sleep(0.2)  # Brief pause before Enter
                subprocess.run(
                    [
                        "tmux",
                        "send-keys",
                        "-t",
                        f"{session_name}:{window_name}",
                        "Enter",
                    ],
                    capture_output=True,
                )

            print(
                f"✅ Message sent successfully to {agent_name} (window: {window_name})"
            )
            return True

        except Exception as e:
            print(f"❌ Error with window {window_name}: {e}")
            continue

    print(f"❌ Failed to send message to {agent_name} - no working window found")
    return False


def main():
    """Main CLI interface"""

    parser = argparse.ArgumentParser(
        description="Send messages to agents with fixed naming support"
    )
    parser.add_argument("--agent", required=True, help="Agent name to send message to")
    parser.add_argument("--message", required=True, help="Message to send")
    parser.add_argument(
        "--no-auto-submit",
        action="store_true",
        help="Don't automatically submit with Enter",
    )

    args = parser.parse_args()

    auto_submit = not args.no_auto_submit
    success = send_message_to_agent_fixed(args.agent, args.message, auto_submit)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
