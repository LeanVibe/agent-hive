#!/usr/bin/env python3
"""
Check agent progress and push status
"""

import subprocess
import sys
from pathlib import Path

def check_agent_progress():
    """Check progress of all agents"""

    # Get worktree list
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
        cwd="."
    )

    if result.returncode != 0:
        print(f"❌ Failed to get worktree list: {result.stderr}")
        return

    print("🔍 LeanVibe Agent Progress Report")
    print("=" * 50)

    current_worktree = None
    current_branch = None

    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            current_worktree = Path(line.split(" ", 1)[1])
        elif line.startswith("branch "):
            current_branch = line.split(" ", 1)[1]

            if current_worktree and "agent" in current_worktree.name:
                agent_name = current_worktree.name.replace("-worktree", "").replace("worktrees/", "")

                print(f"\n📊 {agent_name}")
                print(f"   📁 Path: {current_worktree}")
                print(f"   🌿 Branch: {current_branch}")

                # Check recent commits
                try:
                    commit_result = subprocess.run(
                        ["git", "log", "--oneline", "-3"],
                        capture_output=True,
                        text=True,
                        cwd=current_worktree
                    )

                    if commit_result.returncode == 0:
                        commits = commit_result.stdout.strip().split('\n')
                        print(f"   📝 Recent commits: {len(commits)}")
                        for commit in commits[:2]:  # Show first 2 commits
                            print(f"      • {commit}")
                    else:
                        print(f"   ❌ Could not get commits: {commit_result.stderr}")

                except Exception as e:
                    print(f"   ❌ Error checking commits: {e}")

                # Check if branch is ahead of remote
                try:
                    status_result = subprocess.run(
                        ["git", "status", "--porcelain=v1", "--branch"],
                        capture_output=True,
                        text=True,
                        cwd=current_worktree
                    )

                    if status_result.returncode == 0:
                        lines = status_result.stdout.strip().split('\n')
                        branch_line = lines[0] if lines else ""

                        if "ahead" in branch_line:
                            print(f"   📤 Status: {branch_line.strip()}")
                        elif "up to date" in branch_line or "origin" in branch_line:
                            print(f"   ✅ Status: Up to date with remote")
                        else:
                            print(f"   📊 Status: {branch_line.strip()}")
                    else:
                        print(f"   ❌ Could not get status: {status_result.stderr}")

                except Exception as e:
                    print(f"   ❌ Error checking status: {e}")

    print(f"\n📊 Summary")
    print("✅ All agents have been pinged to resume work")
    print("📤 Agents instructed to push after each commit")
    print("🔄 Agents told to work continuously unless blocked")

if __name__ == "__main__":
    check_agent_progress()
