#!/bin/bash
set -euo pipefail

# Install prerequisites (stub; assume installed
mkdir -p .claude/logs scripts personas commands hooks docs rules

# Create worktrees
git worktree add ../wt-backend main || true
git worktree add ../wt-frontend main || true
git worktree add ../wt-ios main || true
git worktree add ../wt-infra main || true

# Init DB
python scripts/state_manager.py

# Set hooks
git config core.hooksPath .claude/hooks

# Copy templates
for agent in backend frontend ios infra; do
  cd ../wt-$agent
  sed "s/{persona}/$agent/g' " ../.claude/agent_CLAUDE_template.md > .claude/CLAUDE.md
  cd -
done

echo "Setup complete. Run test_system.sh"
