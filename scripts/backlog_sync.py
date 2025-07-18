#!/usr/bin/env python3
"""
Backlog Sync Tool - Single Source of Truth Maintenance

Keeps BACKLOG.md synchronized with GitHub Issues to maintain
a single source of truth for project priorities.
"""

import re
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import argparse


class BacklogSyncManager:
    """Manages synchronization between BACKLOG.md and GitHub Issues."""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.backlog_path = self.repo_path / "BACKLOG.md"
        self.sync_log = []
        
    def parse_backlog_items(self) -> List[Dict]:
        """Extract actionable items from BACKLOG.md."""
        if not self.backlog_path.exists():
            print("❌ BACKLOG.md not found")
            return []
            
        with open(self.backlog_path, 'r') as f:
            content = f.read()
        
        items = []
        current_priority = None
        
        # Parse priority sections and extract tasks
        priority_pattern = r'^## 🔥 (P\d+).*$'
        task_pattern = r'^- \[ \] \*\*(.*?)\*\* - (.*?) \(Est: (.*?)\)'
        
        lines = content.split('\n')
        for line in lines:
            # Check for priority section
            priority_match = re.match(priority_pattern, line)
            if priority_match:
                current_priority = priority_match.group(1)
                continue
                
            # Check for task items
            task_match = re.match(task_pattern, line)
            if task_match and current_priority:
                title = task_match.group(1)
                description = task_match.group(2)
                estimate = task_match.group(3)
                
                # Extract GitHub issue reference if present
                github_issue = None
                github_match = re.search(r'\(GitHub #(\d+)\)', line)
                if github_match:
                    github_issue = int(github_match.group(1))
                
                items.append({
                    'title': title,
                    'description': description,
                    'estimate': estimate,
                    'priority': current_priority,
                    'github_issue': github_issue,
                    'raw_line': line
                })
        
        return items
    
    def get_github_issues(self) -> List[Dict]:
        """Fetch current GitHub issues."""
        try:
            result = subprocess.run([
                'gh', 'issue', 'list', '--json', 
                'number,title,body,labels,state,milestone'
            ], capture_output=True, text=True, check=True)
            
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to fetch GitHub issues: {e}")
            return []
    
    def sync_backlog_to_github(self, dry_run: bool = True) -> None:
        """Sync BACKLOG.md items to GitHub Issues."""
        print(f"🔄 Syncing BACKLOG.md → GitHub Issues (dry_run={dry_run})")
        
        backlog_items = self.parse_backlog_items()
        github_issues = {issue['number']: issue for issue in self.get_github_issues()}
        
        sync_actions = []
        
        for item in backlog_items:
            if item['github_issue']:
                # Update existing issue
                issue_num = item['github_issue']
                if issue_num in github_issues:
                    existing = github_issues[issue_num]
                    if existing['title'] != item['title']:
                        sync_actions.append({
                            'action': 'update_title',
                            'issue': issue_num,
                            'old_title': existing['title'],
                            'new_title': item['title']
                        })
                else:
                    sync_actions.append({
                        'action': 'issue_not_found',
                        'issue': issue_num,
                        'title': item['title']
                    })
            else:
                # Create new issue for high-priority items
                if item['priority'] in ['P0', 'P1']:
                    sync_actions.append({
                        'action': 'create_issue',
                        'title': item['title'],
                        'description': item['description'],
                        'priority': item['priority'],
                        'estimate': item['estimate']
                    })
        
        # Execute sync actions
        for action in sync_actions:
            if dry_run:
                print(f"  📋 WOULD {action['action']}: {action.get('title', action.get('issue'))}")
            else:
                self._execute_sync_action(action)
        
        print(f"✅ Sync complete: {len(sync_actions)} actions")
        return sync_actions
    
    def _execute_sync_action(self, action: Dict) -> bool:
        """Execute a single sync action."""
        try:
            if action['action'] == 'create_issue':
                # Create new GitHub issue
                title = action['title']
                body = f"{action['description']}\n\n**Priority**: {action['priority']}\n**Estimate**: {action['estimate']}\n\n*Synced from BACKLOG.md*"
                labels = f"priority-{action['priority'].lower()},backlog-item"
                
                result = subprocess.run([
                    'gh', 'issue', 'create',
                    '--title', title,
                    '--body', body,
                    '--label', labels
                ], capture_output=True, text=True, check=True)
                
                print(f"  ✅ Created issue: {title}")
                self.sync_log.append(f"Created issue: {title}")
                return True
                
            elif action['action'] == 'update_title':
                # Update issue title
                result = subprocess.run([
                    'gh', 'issue', 'edit', str(action['issue']),
                    '--title', action['new_title']
                ], capture_output=True, text=True, check=True)
                
                print(f"  ✅ Updated issue #{action['issue']}: {action['new_title']}")
                self.sync_log.append(f"Updated issue #{action['issue']}: {action['new_title']}")
                return True
                
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to execute {action['action']}: {e}")
            self.sync_log.append(f"FAILED {action['action']}: {e}")
            return False
        
        return False
    
    def consolidate_duplicate_issues(self, dry_run: bool = True) -> None:
        """Identify and consolidate duplicate GitHub issues."""
        print(f"🔍 Checking for duplicate issues (dry_run={dry_run})")
        
        github_issues = self.get_github_issues()
        
        # Known duplicates from backlog analysis
        duplicates = [
            {'primary': 75, 'duplicate': 77, 'reason': 'Same Foundation Epic Phase 2 Sprint 1'}
        ]
        
        for dup in duplicates:
            if dry_run:
                print(f"  📋 WOULD consolidate: #{dup['duplicate']} → #{dup['primary']} ({dup['reason']})")
            else:
                # Close duplicate and reference primary
                try:
                    subprocess.run([
                        'gh', 'issue', 'close', str(dup['duplicate']),
                        '--comment', f"Closing as duplicate of #{dup['primary']}. {dup['reason']}"
                    ], check=True)
                    print(f"  ✅ Closed duplicate issue #{dup['duplicate']}")
                except subprocess.CalledProcessError as e:
                    print(f"  ❌ Failed to close duplicate: {e}")
    
    def generate_sync_report(self) -> str:
        """Generate a sync status report."""
        timestamp = datetime.now().isoformat()
        backlog_items = self.parse_backlog_items()
        github_issues = self.get_github_issues()
        
        report = f"""# Backlog Sync Report
        
**Generated**: {timestamp}
**Backlog Items**: {len(backlog_items)}
**GitHub Issues**: {len(github_issues)}

## Priority Distribution
"""
        
        # Count items by priority
        priority_counts = {}
        for item in backlog_items:
            priority = item['priority']
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        for priority, count in sorted(priority_counts.items()):
            report += f"- **{priority}**: {count} items\n"
        
        report += f"\n## Sync Log\n"
        for log_entry in self.sync_log:
            report += f"- {log_entry}\n"
        
        return report


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Backlog Sync Tool")
    parser.add_argument('--action', choices=['sync', 'report', 'consolidate'], 
                       default='sync', help='Action to perform')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without executing')
    parser.add_argument('--repo-path', default='.', 
                       help='Path to repository root')
    
    args = parser.parse_args()
    
    manager = BacklogSyncManager(args.repo_path)
    
    if args.action == 'sync':
        manager.sync_backlog_to_github(dry_run=args.dry_run)
        
    elif args.action == 'consolidate':
        manager.consolidate_duplicate_issues(dry_run=args.dry_run)
        
    elif args.action == 'report':
        report = manager.generate_sync_report()
        print(report)
        
        # Save report to file
        report_file = Path(args.repo_path) / "backlog_sync_report.md"
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"\n📝 Report saved to: {report_file}")


if __name__ == "__main__":
    main()