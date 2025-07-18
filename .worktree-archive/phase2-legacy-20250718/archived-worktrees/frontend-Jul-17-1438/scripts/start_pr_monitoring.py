#!/usr/bin/env python3
"""
Start PR Monitoring Service

Starts background monitoring for PR #28 and coordinates merge process
once all feedback is implemented.
"""

import subprocess
import sys

def start_pr_monitoring():
    """Start PR monitoring in background"""

    print("🔍 Starting PR #28 Monitoring Service")
    print("=" * 50)

    # Check if PR exists and is open
    try:
        result = subprocess.run([
            "gh", "pr", "view", "28", "--json", "state,title"
        ], capture_output=True, text=True, check=True)

        import json
        pr_info = json.loads(result.stdout)

        if pr_info['state'] != 'OPEN':
            print(f"❌ PR #28 is {pr_info['state']}, cannot monitor")
            return False

        print(f"✅ Found PR #28: {pr_info['title']}")

    except Exception as e:
        print(f"❌ Could not find PR #28: {e}")
        return False

    # Notify agents about monitoring start
    try:
        from dashboard.prompt_logger import prompt_logger

        agents = [
            "integration-agent", "pm-agent", "quality-agent",
            "documentation-agent", "orchestration-agent", "intelligence-agent"
        ]

        monitoring_message = """🔍 PR MERGE MONITORING ACTIVATED

PR #28 monitoring has started with the following automated process:

✅ AUTOMATIC MERGE CONDITIONS:
1. PR size ≤1000 lines (component-based)
2. Test coverage present in changes
3. Documentation included
4. Security review passed
5. Required approvals received

🤖 AUTOMATED ACTIONS:
- Check PR status every 5 minutes
- Notify all agents when merge-ready
- Automatically merge when all gates pass
- Update GitHub issues after merge
- Clean up feature branch

📋 WHAT YOU NEED TO DO:
Integration Agent: Implement feedback and create smaller PRs
PM Agent: Monitor progress and coordinate reviews
Quality Agent: Ensure tests are comprehensive
Documentation Agent: Verify docs are complete

The system will automatically proceed with merge once feedback is implemented. No manual intervention required."""

        print("📡 Notifying all agents about monitoring activation...")

        for agent in agents:
            subprocess.run([
                "python", "scripts/send_agent_message.py",
                "--agent", agent, "--message", monitoring_message
            ], capture_output=True)

            # Log the notification
            try:
                prompt_logger.log_prompt(
                    f"pr-monitor-to-{agent}",
                    monitoring_message,
                    "PR monitoring notification sent",
                    True
                )
            except:
                pass

        print("✅ All agents notified about PR monitoring")

    except Exception as e:
        print(f"⚠️  Could not notify agents: {e}")

    # Start monitoring process in background
    print("\n🚀 Starting background monitoring process...")

    try:
        # Start monitoring with 5-minute intervals
        subprocess.Popen([
            "python", "scripts/pr_merge_coordinator.py", "28",
            "--check-interval", "300"  # 5 minutes
        ])

        print("✅ PR monitoring started successfully!")
        print("\n📊 Monitoring Details:")
        print("  - PR Number: #28")
        print("  - Check Interval: 5 minutes")
        print("  - Auto-merge: Enabled when quality gates pass")
        print("  - Agent Notifications: Enabled")
        print("  - Issue Updates: Enabled")

        print("\n🔍 Monitor Status:")
        print("  - Dashboard: http://localhost:8000")
        print("  - Check manually: python scripts/pr_merge_coordinator.py 28 --check-once")
        print("  - Force merge: python scripts/pr_merge_coordinator.py 28 --force-merge")

        return True

    except Exception as e:
        print(f"❌ Failed to start monitoring: {e}")
        return False

def check_monitoring_status():
    """Check if monitoring is already running"""
    try:
        result = subprocess.run([
            "pgrep", "-f", "pr_merge_coordinator.py"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ PR monitoring is already running")
            print(f"📋 Process ID: {result.stdout.strip()}")
            return True
        else:
            print("❌ PR monitoring is not running")
            return False

    except Exception:
        return False

def main():
    """Main function"""
    print("🤖 LeanVibe PR Merge Automation")
    print("=" * 40)

    # Check if already running
    if check_monitoring_status():
        print("\n💡 Monitoring is already active. Use these commands:")
        print("  - Check status: python scripts/pr_merge_coordinator.py 28 --check-once")
        print("  - Dashboard: http://localhost:8000")
        return

    # Start monitoring
    if start_pr_monitoring():
        print("\n🎉 PR monitoring successfully activated!")
        print("📱 You will be notified when merge conditions are met")
        print("🔄 The system will automatically proceed with merge")
    else:
        print("\n❌ Failed to start PR monitoring")
        sys.exit(1)

if __name__ == "__main__":
    main()
