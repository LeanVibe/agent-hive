#!/usr/bin/env python3
"""
Fixed Agent Communication - Handles both prefixed and non-prefixed window names
Temporary fix until all agents use consistent naming
"""

import subprocess
import time
import sys
import argparse
from pathlib import Path

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
<<<<<<< HEAD
<<<<<<< HEAD

    # Try both naming conventions
||||||| 48e9100
    
||||||| 48e9100
    
=======

>>>>>>> new-work/performance-Jul-17-0823
    # Try both naming conventions
=======

    # Try multiple naming conventions
>>>>>>> new-work/frontend-Jul-17-0824
    window_names_to_try = [
        f"agent-{agent_name}",  # New convention
        agent_name,             # Current convention
        f"{agent_name.upper()}-Input-⏳",  # Status pattern (PM-Input-⏳)
        f"{agent_name.upper()}-Input-⏳-",  # Status pattern variant
        f"{agent_name.upper()}-Input-⏳*"   # Active status pattern
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

def main():
    """Main CLI interface"""

    parser = argparse.ArgumentParser(description="Send messages to agents with fixed naming support")
    parser.add_argument("--agent", required=True, help="Agent name to send message to")
    parser.add_argument("--message", required=True, help="Message to send")
    parser.add_argument("--no-auto-submit", action="store_true", help="Don't automatically submit with Enter")

    args = parser.parse_args()

    auto_submit = not args.no_auto_submit
    success = send_message_to_agent_fixed(args.agent, args.message, auto_submit)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
