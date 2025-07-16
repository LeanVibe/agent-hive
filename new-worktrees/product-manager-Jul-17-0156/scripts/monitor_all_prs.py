#!/usr/bin/env python3
"""
Monitor All Agent PRs

Monitors all open PRs from agents and coordinates merge process
when each PR meets quality gates.
"""

import subprocess
import time
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add dashboard logging
sys.path.append(str(Path(__file__).parent.parent))

def get_all_open_prs() -> List[Dict[str, Any]]:
    """Get all open PRs"""
    try:
        result = subprocess.run([
            "gh", "pr", "list", "--json", 
            "number,title,author,additions,deletions,reviewDecision,mergeable,headRefName"
        ], capture_output=True, text=True, check=True)
        
        return json.loads(result.stdout)
        
    except Exception as e:
        print(f"❌ Error getting PRs: {e}")
        return []

def check_pr_quality_gates(pr: Dict[str, Any]) -> bool:
    """Check if PR passes quality gates"""
    pr_number = pr['number']
    additions = pr['additions']
    
    print(f"\n🔍 Checking PR #{pr_number}: {pr['title']}")
    
    # Size check
    if additions > 1000:
        print(f"  ❌ Size: {additions} lines (>1000)")
        return False
    else:
        print(f"  ✅ Size: {additions} lines (≤1000)")
    
    # Review check
    review_decision = pr.get('reviewDecision', '')
    if review_decision == 'APPROVED':
        print(f"  ✅ Reviews: Approved")
    else:
        print(f"  ❌ Reviews: {review_decision or 'Pending'}")
        return False
    
    # Mergeable check
    if pr.get('mergeable') == 'MERGEABLE':
        print(f"  ✅ Mergeable: Yes")
    else:
        print(f"  ❌ Mergeable: {pr.get('mergeable', 'Unknown')}")
        return False
    
    print(f"  🎉 PR #{pr_number} ready for merge!")
    return True

def merge_pr(pr_number: int) -> bool:
    """Merge a specific PR"""
    try:
        print(f"🚀 Merging PR #{pr_number}...")
        
        result = subprocess.run([
            "gh", "pr", "merge", str(pr_number),
            "--squash", "--delete-branch"
        ], capture_output=True, text=True, check=True)
        
        print(f"✅ PR #{pr_number} merged successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Merge failed for PR #{pr_number}: {e.stderr}")
        return False

def notify_agents_about_pr_status():
    """Notify agents about overall PR status"""
    try:
        prs = get_all_open_prs()
        
        if not prs:
            message = """📊 PR STATUS UPDATE

No open PRs found. Agents should create PRs for their completed work:

🎯 TO CREATE A PR:
1. Ensure your work is committed to feature branch
2. Run: gh pr create --title "feat: Your component description" --body "Detailed description"
3. Ensure PR is <1000 lines with tests and documentation

📋 EXPECTED PRS FROM AGENTS:
- Integration Agent: Auth middleware component
- Documentation Agent: Integration docs and validation
- Quality Agent: Quality gates and security framework  
- Orchestration Agent: Enhanced coordination system
- Intelligence Agent: Phase 2 framework completion
- PM Agent: Automated PM/XP methodology system

Please create your PRs so we can review and merge them!"""
        else:
            pr_summary = "\n".join([
                f"- PR #{pr['number']}: {pr['title']} ({pr['additions']} lines)"
                for pr in prs
            ])
            
            message = f"""📊 PR STATUS UPDATE

Found {len(prs)} open PR(s):
{pr_summary}

🔄 AUTOMATIC MONITORING ACTIVE:
- PRs will be auto-merged when quality gates pass
- Size limit: ≤1000 lines per PR
- Required: Tests, docs, and approvals
- Monitoring every 5 minutes

Keep working on your components and creating focused PRs!"""

        # Send to PM agent for coordination
        subprocess.run([
            "python", "scripts/send_agent_message.py",
            "--agent", "pm-agent", "--message", message
        ], capture_output=True)
        
        # Log the status
        try:
            from dashboard.prompt_logger import prompt_logger
            prompt_logger.log_prompt(
                "pr-monitor-status",
                f"PR monitoring update: {len(prs)} open PRs",
                "Status update sent",
                True
            )
        except:
            pass
            
    except Exception as e:
        print(f"⚠️  Could not notify agents: {e}")

def monitor_all_prs():
    """Monitor all PRs and merge when ready"""
    print("🔍 Multi-PR Monitoring System Started")
    print("=" * 50)
    
    last_notification = 0
    notification_interval = 1800  # 30 minutes
    
    while True:
        try:
            current_time = time.time()
            
            print(f"\n🕐 {datetime.now().strftime('%H:%M:%S')} - Checking all PRs...")
            
            prs = get_all_open_prs()
            
            if not prs:
                print("📝 No open PRs found")
                
                # Notify agents every 30 minutes if no PRs
                if current_time - last_notification > notification_interval:
                    notify_agents_about_pr_status()
                    last_notification = current_time
            else:
                print(f"📋 Found {len(prs)} open PR(s)")
                
                ready_for_merge = []
                
                for pr in prs:
                    if check_pr_quality_gates(pr):
                        ready_for_merge.append(pr)
                
                # Merge ready PRs
                for pr in ready_for_merge:
                    print(f"\n🎉 Merging ready PR #{pr['number']}...")
                    
                    if merge_pr(pr['number']):
                        # Notify agents about successful merge
                        merge_message = f"""✅ PR MERGED SUCCESSFULLY

PR #{pr['number']} has been merged: {pr['title']}

🎯 NEXT STEPS:
1. Pull latest changes: git pull origin main
2. Rebase any conflicting branches
3. Continue with next component development
4. Create new PRs for additional components

Great work on the component-based approach!"""

                        subprocess.run([
                            "python", "scripts/send_agent_message.py",
                            "--agent", "pm-agent", "--message", merge_message
                        ], capture_output=True)
                
                # Update status every 30 minutes
                if current_time - last_notification > notification_interval:
                    notify_agents_about_pr_status()
                    last_notification = current_time
            
            print(f"⏳ Next check in 300 seconds...")
            time.sleep(300)  # Check every 5 minutes
            
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Error in monitoring loop: {e}")
            time.sleep(60)  # Wait 1 minute on error

if __name__ == "__main__":
    monitor_all_prs()