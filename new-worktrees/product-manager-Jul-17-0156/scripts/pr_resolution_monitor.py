#!/usr/bin/env python3
"""
PR Resolution Monitor

Monitors PR conflict resolution progress and automatically coordinates
sequential agent rebases and merges.
"""

import subprocess
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Optional

class PRResolutionMonitor:
    """Monitors and coordinates PR conflict resolution"""
    
    def __init__(self):
        self.target_prs = [
            {"number": 29, "agent": "documentation-agent", "title": "Documentation ecosystem"},
            {"number": 30, "agent": "intelligence-agent", "title": "Intelligence framework"},
            {"number": 31, "agent": "integration-agent", "title": "Auth middleware"},
            {"number": 35, "agent": "unknown", "title": "API Gateway"},
            {"number": 36, "agent": "unknown", "title": "Service Discovery"},
            {"number": 38, "agent": "unknown", "title": "Monitoring System"}
        ]
        
        self.current_pr_index = 0
        self.merged_prs = []
        self.failed_prs = []
        
    def get_pr_status(self) -> List[Dict]:
        """Get current PR status"""
        try:
            result = subprocess.run([
                "gh", "pr", "list", "--json", 
                "number,title,mergeable,reviewDecision,headRefName,additions"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                print(f"❌ Error getting PR status: {result.stderr}")
                return []
                
        except Exception as e:
            print(f"❌ Exception getting PR status: {e}")
            return []
    
    def check_pr_mergeable(self, pr_number: int) -> bool:
        """Check if specific PR is mergeable"""
        prs = self.get_pr_status()
        for pr in prs:
            if pr["number"] == pr_number:
                return pr["mergeable"] == "MERGEABLE"
        return False
    
    def merge_pr(self, pr_number: int) -> bool:
        """Merge a specific PR"""
        try:
            print(f"🚀 Attempting to merge PR #{pr_number}...")
            
            result = subprocess.run([
                "gh", "pr", "merge", str(pr_number), "--squash"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Successfully merged PR #{pr_number}")
                return True
            else:
                print(f"❌ Failed to merge PR #{pr_number}: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Exception merging PR #{pr_number}: {e}")
            return False
    
    def signal_next_agent(self, pr_info: Dict):
        """Signal the next agent to start rebase"""
        agent_name = pr_info["agent"]
        pr_number = pr_info["number"]
        
        if agent_name == "unknown":
            print(f"⚠️  Unknown agent for PR #{pr_number}, skipping auto-signal")
            return
        
        message = f"""🚨 YOUR TURN: START REBASE FOR PR #{pr_number}

The previous PR has been resolved. Time to resolve your conflicts!

📊 YOUR PR:
- PR #{pr_number}: {pr_info['title']}
- Status: Your turn to resolve conflicts

🔧 START REBASE NOW:
1. cd worktrees/{agent_name} (or your current worktree)
2. git checkout {self.get_branch_name(pr_number)}
3. git pull origin main
4. git rebase main
5. Resolve any conflicts that appear
6. git push --force-with-lease origin {self.get_branch_name(pr_number)}

⚡ PRIORITY: HIGH - You are next in the merge queue!

🎯 CONFLICT RESOLUTION TIPS:
- Focus on keeping your changes for your component
- Accept main branch changes for shared/infrastructure files
- Don't add new features during rebase - just resolve conflicts
- If stuck, ask for help immediately

💡 AFTER REBASE:
- PR will automatically become mergeable
- It will be auto-merged immediately
- Your worktree will be cleaned up
- You'll be despawned after successful merge

Please start immediately and report progress!"""
        
        try:
            subprocess.run([
                "python", "scripts/send_agent_message.py",
                "--agent", agent_name, "--message", message
            ], check=True)
            
            print(f"✅ Signaled {agent_name} to start rebase for PR #{pr_number}")
            
        except Exception as e:
            print(f"❌ Failed to signal {agent_name}: {e}")
    
    def get_branch_name(self, pr_number: int) -> str:
        """Get branch name for PR"""
        branch_mapping = {
            29: "feature/documentation-ecosystem",
            30: "feature/intelligence-framework-implementation", 
            31: "feature/auth-middleware-component",
            35: "feature/api-gateway-component",
            36: "feature/service-discovery-component",
            38: "feature/monitoring-system-component"
        }
        return branch_mapping.get(pr_number, "unknown")
    
    def cleanup_merged_pr(self, pr_info: Dict):
        """Clean up worktree and despawn agent after successful merge"""
        agent_name = pr_info["agent"]
        pr_number = pr_info["number"]
        
        if agent_name == "unknown":
            print(f"⚠️  Unknown agent for PR #{pr_number}, skipping cleanup")
            return
        
        worktree_path = f"worktrees/{agent_name}"
        
        try:
            # Remove worktree
            subprocess.run([
                "git", "worktree", "remove", worktree_path, "--force"
            ], capture_output=True)
            
            # Kill tmux session
            subprocess.run([
                "tmux", "kill-window", "-t", f"agent-hive:{agent_name}"
            ], capture_output=True)
            
            print(f"🧹 Cleaned up {agent_name} worktree and despawned agent")
            
        except Exception as e:
            print(f"⚠️  Error cleaning up {agent_name}: {e}")
    
    def run_monitoring(self):
        """Run the monitoring loop"""
        print("🔍 Starting PR Resolution Monitor...")
        print(f"📋 Monitoring {len(self.target_prs)} PRs for resolution")
        print("=" * 60)
        
        while self.current_pr_index < len(self.target_prs):
            current_pr = self.target_prs[self.current_pr_index]
            pr_number = current_pr["number"]
            
            print(f"\\n🔄 Checking PR #{pr_number} ({current_pr['title']})")
            
            # Check if current PR is mergeable
            if self.check_pr_mergeable(pr_number):
                print(f"✅ PR #{pr_number} is now mergeable!")
                
                # Attempt to merge
                if self.merge_pr(pr_number):
                    print(f"🎉 Successfully merged PR #{pr_number}")
                    
                    # Add to merged list
                    self.merged_prs.append(current_pr)
                    
                    # Clean up
                    self.cleanup_merged_pr(current_pr)
                    
                    # Move to next PR
                    self.current_pr_index += 1
                    
                    # Signal next agent if there is one
                    if self.current_pr_index < len(self.target_prs):
                        next_pr = self.target_prs[self.current_pr_index]
                        self.signal_next_agent(next_pr)
                        
                else:
                    print(f"❌ Failed to merge PR #{pr_number}")
                    self.failed_prs.append(current_pr)
                    self.current_pr_index += 1
                    
            else:
                print(f"⏳ PR #{pr_number} still has conflicts, waiting...")
            
            # Wait before next check
            time.sleep(30)  # Check every 30 seconds
        
        # Final summary
        print("\\n" + "=" * 60)
        print("📊 PR RESOLUTION SUMMARY")
        print("=" * 60)
        print(f"✅ Successfully merged: {len(self.merged_prs)} PRs")
        for pr in self.merged_prs:
            print(f"   - PR #{pr['number']}: {pr['title']}")
        
        print(f"❌ Failed to merge: {len(self.failed_prs)} PRs")
        for pr in self.failed_prs:
            print(f"   - PR #{pr['number']}: {pr['title']}")
        
        remaining = len(self.target_prs) - len(self.merged_prs) - len(self.failed_prs)
        print(f"⏳ Remaining: {remaining} PRs")
        
        if len(self.merged_prs) == len(self.target_prs):
            print("🎉 ALL PRS SUCCESSFULLY MERGED!")
        else:
            print("⚠️  Some PRs still need attention")

if __name__ == "__main__":
    monitor = PRResolutionMonitor()
    monitor.run_monitoring()