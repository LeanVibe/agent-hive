#!/bin/bash

WORKTREES=(
"infrastructure-Jul-16-1300"
"infrastructure-Jul-17-0822"
"infrastructure-Jul-17-0945"
"infrastructure-Jul-17-0946"
"integration-specialist-Jul-16-1220"
"integration-specialist-Jul-16-1247"
"integration-specialist-Jul-17-0156"
"integration-specialist-Jul-17-0824"
"integration-specialist-Jul-17-0946"
"monitoring-Jul-17-0824"
"monitoring-Jul-17-0946"
"performance-Jul-16-1301"
"performance-Jul-17-0823"
"pm-agent-new"
"security-Jul-17-0944"
"service-mesh-Jul-16-1221"
)

for wt in "${WORKTREES[@]}"; do
    branch=$(git worktree list | grep "$wt" | awk '{print $NF}' | tr -d '[]')
    if [ -n "$branch" ]; then
        echo "=================================================="
        echo "Worktree: $wt"
        echo "Branch: $branch"
        echo "--------------------------------------------------"
        echo "Commit History (top 5):"
        git log --oneline "$branch" | head -n 5
        echo "--------------------------------------------------"
        latest_commit=$(git log --oneline "$branch" | head -n 1 | awk '{print $1}')
        if [ -n "$latest_commit" ]; then
            echo "File Changes (latest commit):"
            git diff --stat "${latest_commit}^" "$latest_commit"
        fi
        echo "=================================================="
        echo ""
    fi
done 