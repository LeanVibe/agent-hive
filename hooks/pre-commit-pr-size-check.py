#!/usr/bin/env python3
"""
Pre-commit hook for PR size validation
Prevents commits that would create oversized PRs
"""

import subprocess
import sys

def get_staged_changes():
    """Get number of staged changes"""
    try:
        # Get diff stats for staged files
        result = subprocess.run(
            ["git", "diff", "--cached", "--numstat"],
            capture_output=True, text=True, check=True
        )
        
        lines = result.stdout.strip().split('\n')
        if not lines or lines == ['']:
            return 0, 0
        
        total_additions = 0
        total_deletions = 0
        
        for line in lines:
            if line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    additions = int(parts[0]) if parts[0] != '-' else 0
                    deletions = int(parts[1]) if parts[1] != '-' else 0
                    total_additions += additions
                    total_deletions += deletions
        
        return total_additions, total_deletions
        
    except subprocess.CalledProcessError:
        return 0, 0

def check_pr_size_limit(max_lines=500):
    """Check if staged changes exceed PR size limit"""
    additions, deletions = get_staged_changes()
    total_changes = additions + deletions
    
    if total_changes > max_lines:
        return False, {
            "additions": additions,
            "deletions": deletions,
            "total_changes": total_changes,
            "max_allowed": max_lines,
            "violation_factor": round(total_changes / max_lines, 1)
        }
    
    return True, {
        "additions": additions,
        "deletions": deletions,
        "total_changes": total_changes,
        "max_allowed": max_lines
    }

def main():
    """Main pre-commit check"""
    MAX_PR_SIZE = 500
    
    is_compliant, stats = check_pr_size_limit(MAX_PR_SIZE)
    
    if not is_compliant:
        print(f"""
🚨 COMMIT REJECTED - PR SIZE LIMIT VIOLATION

**STAGED CHANGES EXCEED LIMIT:**
- Additions: {stats['additions']} lines
- Deletions: {stats['deletions']} lines
- Total Changes: {stats['total_changes']} lines
- Limit: {stats['max_allowed']} lines maximum
- Violation Factor: {stats['violation_factor']}x over limit

**REQUIRED ACTION:**
1. Unstage some files: git reset HEAD <file>
2. Commit changes incrementally in smaller batches
3. Follow <500 line PR limits (Week 2 Strategic Plan)
4. Break down large features into multiple PRs

**WORKFLOW DISCIPLINE:**
Large PRs cause integration failures and review bottlenecks.
Submit manageable, reviewable changes.

Commit rejected. Please reduce staged changes and try again.
""")
        sys.exit(1)
    
    print(f"✅ Pre-commit check passed: {stats['total_changes']} lines (within {MAX_PR_SIZE} limit)")
    sys.exit(0)

if __name__ == "__main__":
    main()