#!/bin/bash
#
# Daily Sync: main → agent-integration
# Keeps agent integration branch up-to-date with main branch changes
# 
# Usage: ./scripts/daily_sync.sh
# Cron: 0 9 * * * cd /path/to/agent-hive && ./scripts/daily_sync.sh

set -e

echo "🔄 Daily Sync: main → agent-integration"
echo "======================================"

# Ensure we're in the right directory
if [ ! -f "scripts/cli.py" ] || [ ! -d "advanced_orchestration" ]; then
    echo "❌ Error: Not in LeanVibe Agent Hive project root"
    echo "💡 Run from the project root directory"
    exit 1
fi

# Fetch latest changes
echo "📡 Fetching latest changes..."
git fetch origin

# Switch to agent-integration branch
echo "🌿 Switching to agent-integration branch..."
git checkout agent-integration

# Pull latest agent-integration changes
echo "⬇️ Pulling latest agent-integration..."
git pull origin agent-integration

# Merge main into agent-integration (preserve history)
echo "🔀 Merging main → agent-integration..."
if git merge origin/main --no-ff -m "Daily sync: main → agent-integration ($(date '+%Y-%m-%d'))"; then
    echo "✅ Merge successful"
else
    echo "❌ Merge failed - manual intervention required"
    echo "💡 Check for conflicts and resolve manually"
    exit 1
fi

# Push updated agent-integration
echo "⬆️ Pushing updated agent-integration..."
git push origin agent-integration

echo ""
echo "🎉 Daily sync complete!"
echo "✅ agent-integration branch is now up-to-date with main"
echo "🚀 Agents can now work from latest integration branch"