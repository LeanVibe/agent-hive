#!/usr/bin/env python3
"""
Drop-in replacement for tmux-based agent communication scripts.

This script provides the same CLI interface as scripts/agent_communicate.py
but uses the production Redis message bus instead of tmux sessions.

Usage:
    python tmux_replacement.py <target_agent> <message> [from_agent]

Examples:
    python tmux_replacement.py documentation-agent "Please update API docs"
    python tmux_replacement.py pm-agent "Sprint planning needed" quality-agent
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add message_bus to path
sys.path.append(str(Path(__file__).parent.parent))

from message_bus.agent_communicator import SimpleAgentCommunicator


def setup_logging():
    """Setup basic logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


async def main():
    """CLI interface for agent communication via message bus."""

    setup_logging()

    if len(sys.argv) < 3:
        print("Usage: python tmux_replacement.py <target_agent> <message> [from_agent]")
        print("")
        print("Examples:")
        print("  python tmux_replacement.py documentation-agent 'Please update API docs'")
        print("  python tmux_replacement.py pm-agent 'Sprint planning needed' quality-agent")
        print("")
        print("Available agents:")
        print("  - documentation-agent")
        print("  - orchestration-agent")
        print("  - pm-agent")
        print("  - intelligence-agent")
        print("  - integration-agent")
        print("  - quality-agent")
        print("  - frontend-agent")
        sys.exit(1)

    target_agent = sys.argv[1]
    message = sys.argv[2]
    from_agent = sys.argv[3] if len(sys.argv) > 3 else "unknown-agent"

    print(f"📡 Sending message from {from_agent} to {target_agent} via Redis message bus...")

    try:
        success = await SimpleAgentCommunicator.send_message(
            from_agent=from_agent,
            to_agent=target_agent,
            message=message
        )

        if success:
            print(f"✅ Message delivered to {target_agent}")
            sys.exit(0)
        else:
            print(f"❌ Failed to deliver message to {target_agent}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Communication failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
