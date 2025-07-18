#!/usr/bin/env python3
"""
Ping all agents to resume work with clear instructions
"""

import subprocess
import time

def ping_agent(agent_name: str, window_name: str):
    """Send resume message to specific agent"""

    resume_message = f"""🚨 URGENT: RESUME WORK IMMEDIATELY

Hello {agent_name}! You need to resume work immediately. Here are your instructions:

1. **NEVER STOP WORKING** unless you are:
   - Waiting for human feedback/approval
   - Blocked by missing dependencies
   - Need something prepared by another agent

2. **WORK CONTINUOUSLY** on your assigned tasks from your CLAUDE.md file

3. **PUSH AFTER EVERY COMMIT**:
   - After each task completion, commit your changes
   - Immediately push your feature branch: `git push origin <your-feature-branch>`
   - This ensures your work is visible and backed up

4. **REPORT PROGRESS** every 2 hours in your GitHub issue

5. **COORDINATE** with other agents as needed

6. **CURRENT STATUS**: Resume your work on your current task immediately

START WORKING NOW! Do not wait for further instructions. Begin with your next task and maintain continuous progress."""

    print(f"📡 Pinging {agent_name}...")

    # Log the prompt
    try:
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent))
        from dashboard.prompt_logger import prompt_logger
        prompt_logger.log_prompt(agent_name, resume_message, "Resume work ping sent", True)
    except ImportError:
        pass  # Continue without logging if dashboard not available

    # Send message to agent using improved buffer method for reliability
    try:
        # Method 1: Use tmux buffer for reliable message handling
        # Set the message in tmux buffer
        result = subprocess.run([
            "tmux", "set-buffer", resume_message
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Failed to set buffer for {agent_name}: {result.stderr}")
            return

        # Clear any existing input first
        subprocess.run([
            "tmux", "send-keys", "-t", f"agent-hive:{window_name}", "C-c"
        ], capture_output=True)

        time.sleep(0.3)  # Brief pause to ensure clear

        # Paste the buffer content
        result = subprocess.run([
            "tmux", "paste-buffer", "-t", f"agent-hive:{window_name}"
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Failed to paste buffer for {agent_name}: {result.stderr}")
            return

        # Auto-submit with Enter
        time.sleep(0.2)  # Brief pause before Enter
        subprocess.run([
            "tmux", "send-keys", "-t", f"agent-hive:{window_name}", "Enter"
        ], capture_output=True)

        print(f"✅ Message sent to {agent_name}")

    except Exception as e:
        print(f"❌ Failed to send message to {agent_name}: {e}")

def main():
    """Ping all agents to resume work"""

    agents = [
        ("documentation-agent", "agent-documentation-agent"),
        ("orchestration-agent", "agent-orchestration-agent"),
        ("pm-agent", "agent-pm-agent"),
        ("intelligence-agent", "agent-intelligence-agent"),
        ("integration-agent", "agent-integration-agent"),
        ("quality-agent", "agent-quality-agent")
    ]

    print("🚨 PINGING ALL AGENTS TO RESUME WORK")
    print("=" * 50)

    for agent_name, window_name in agents:
        ping_agent(agent_name, window_name)
        time.sleep(1)  # Brief pause between agents

    print("\n📊 PING COMPLETE")
    print("✅ All agents have been instructed to resume work")
    print("✅ Agents told to push feature branches after each commit")
    print("✅ Clear instructions provided about when to stop")

    print("\n🔍 Monitor agent activity:")
    print("  python scripts/agent_manager.py --status")
    print("  tmux attach-session -t agent-hive")

if __name__ == "__main__":
    main()
