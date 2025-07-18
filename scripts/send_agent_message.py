#!/usr/bin/env python3
"""
Inter-Agent Communication Tool

Reliable message sending between agents that automatically submits without manual Enter.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Add dashboard logging
sys.path.append(str(Path(__file__).parent.parent))


def send_message_to_agent(
        agent_name: str,
        message: str,
        auto_submit: bool = True) -> bool:
    """
    Send a message to an agent with automatic submission.

    Args:
        agent_name: Target agent name
        message: Message to send
        auto_submit: Whether to automatically submit with Enter

    Returns:
        bool: Success status
    """

    window_name = f"agent-{agent_name}"
    session_name = "agent-hive"

    # Log the message
    try:
        from dashboard.prompt_logger import prompt_logger
        prompt_logger.log_prompt(
            f"to-{agent_name}", message, "Inter-agent message sent", True)
    except ImportError:
        pass  # Continue without logging if dashboard not available

    try:
        # Method 1: Use tmux paste-buffer for reliable long message handling
        print(f"📡 Sending message to {agent_name}...")

        # Set the message in tmux buffer
        result = subprocess.run([
            "tmux", "set-buffer", message
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Failed to set buffer: {result.stderr}")
            return False

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
            return False

        # Auto-submit if requested
        if auto_submit:
            time.sleep(0.2)  # Brief pause before Enter
            subprocess.run(["tmux",
                            "send-keys",
                            "-t",
                            f"{session_name}:{window_name}",
                            "Enter"],
                           capture_output=True)

        print(f"✅ Message sent to {agent_name}")
        return True

    except Exception as e:
        print(f"❌ Error sending message to {agent_name}: {e}")
        return False


def send_message_chunked(
        agent_name: str,
        message: str,
        chunk_size: int = 200) -> bool:
    """
    Send a long message in smaller chunks to avoid input buffer issues.
    """

    window_name = f"agent-{agent_name}"
    session_name = "agent-hive"

    print(f"📡 Sending chunked message to {agent_name}...")

    try:
        # Clear any existing input
        subprocess.run([
            "tmux", "send-keys", "-t", f"{session_name}:{window_name}", "C-c"
        ], capture_output=True)

        time.sleep(0.5)

        # Send message in chunks
        for i in range(0, len(message), chunk_size):
            chunk = message[i:i + chunk_size]

            # Send chunk without Enter
            result = subprocess.run([
                "tmux", "send-keys", "-t", f"{session_name}:{window_name}", chunk
            ], capture_output=True, text=True)

            if result.returncode != 0:
                print(f"❌ Failed to send chunk: {result.stderr}")
                return False

            time.sleep(0.1)  # Brief pause between chunks

        # Send final Enter
        subprocess.run([
            "tmux", "send-keys", "-t", f"{session_name}:{window_name}", "Enter"
        ], capture_output=True)

        print(f"✅ Chunked message sent to {agent_name}")
        return True

    except Exception as e:
        print(f"❌ Error sending chunked message: {e}")
        return False


def ping_all_agents_improved():
    """Ping all agents with improved message delivery"""

    agents = [
        "documentation-agent",
        "orchestration-agent",
        "pm-agent",
        "intelligence-agent",
        "integration-agent",
        "quality-agent"
    ]

    improved_message = """🚨 RESUME WORK - AUTO SUBMIT FIXED

Hello! The inter-agent communication system has been improved. You should now receive messages automatically without needing to manually press Enter.

INSTRUCTIONS:
1. WORK CONTINUOUSLY on your tasks
2. PUSH after every commit: git push origin <your-branch>
3. COORDINATE with other agents as needed
4. ONLY STOP if blocked by external dependencies

Your message sending should now work automatically. Continue with your current task immediately."""

    print("🚀 IMPROVED AGENT COMMUNICATION TEST")
    print("=" * 50)

    success_count = 0
    for agent_name in agents:
        if send_message_to_agent(agent_name, improved_message):
            success_count += 1
        time.sleep(1)  # Pause between agents

    print(
        f"\n📊 Results: {success_count}/{len(agents)} agents contacted successfully")
    print("✅ All agents should now receive messages automatically")


def test_message_methods(agent_name: str, test_message: str):
    """Test different message sending methods"""

    print(f"🧪 Testing message methods for {agent_name}")
    print("=" * 40)

    # Test Method 1: Buffer paste
    print("1. Testing buffer paste method...")
    success1 = send_message_to_agent(
        agent_name, f"TEST 1 - Buffer: {test_message}")

    time.sleep(2)

    # Test Method 2: Chunked sending
    print("2. Testing chunked method...")
    success2 = send_message_chunked(
        agent_name, f"TEST 2 - Chunked: {test_message}")

    time.sleep(2)

    # Test Method 3: Direct send-keys with escaping
    print("3. Testing direct send-keys...")
    escaped_message = test_message.replace('"', '\\"').replace("'", "\\'")
    try:
        subprocess.run([
            "tmux", "send-keys", "-t", f"agent-hive:agent-{agent_name}",
            f"TEST 3 - Direct: {escaped_message}", "Enter"
        ], check=True)
        success3 = True
        print("✅ Direct method succeeded")
    except Exception as e:
        success3 = False
        print(f"❌ Direct method failed: {e}")

    print(f"\n📊 Test Results for {agent_name}:")
    print(f"  Buffer paste: {'✅' if success1 else '❌'}")
    print(f"  Chunked: {'✅' if success2 else '❌'}")
    print(f"  Direct: {'✅' if success3 else '❌'}")


def main():
    """Main CLI interface"""

    parser = argparse.ArgumentParser(
        description="Send messages to agents reliably")
    parser.add_argument("--agent", help="Agent name to send message to")
    parser.add_argument("--message", help="Message to send")
    parser.add_argument("--ping-all", action="store_true",
                        help="Ping all agents with improved communication")
    parser.add_argument(
        "--test", help="Test different message methods with specified agent")
    parser.add_argument("--no-auto-submit", action="store_true",
                        help="Don't automatically submit with Enter")

    args = parser.parse_args()

    if args.ping_all:
        ping_all_agents_improved()
    elif args.test:
        test_message = "Hello! This is a test message to verify automatic submission works properly."
        test_message_methods(args.test, test_message)
    elif args.agent and args.message:
        auto_submit = not args.no_auto_submit
        success = send_message_to_agent(args.agent, args.message, auto_submit)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        print("\nExamples:")
        print(f"  python {sys.argv[0]} --ping-all")
        print(
            f"  python {
                sys.argv[0]} --agent documentation-agent --message 'Hello!'")
        print(f"  python {sys.argv[0]} --test documentation-agent")


if __name__ == "__main__":
    main()
