#!/bin/bash
echo "🛡️ LeanVibe Prevention Systems Status"
echo "===================================="
echo ""

# Check Git Hooks
echo "🔧 Git Hooks:"
if [ -f ".githooks/pre-commit" ] && [ -x ".githooks/pre-commit" ]; then
    echo "  ✅ Pre-commit hook: Active"
else
    echo "  ❌ Pre-commit hook: Missing or not executable"
fi

if [ -f ".githooks/post-commit" ] && [ -x ".githooks/post-commit" ]; then
    echo "  ✅ Post-commit hook: Active"
else
    echo "  ❌ Post-commit hook: Missing or not executable"
fi

HOOKS_PATH=$(git config core.hooksPath)
if [ "$HOOKS_PATH" = ".githooks" ]; then
    echo "  ✅ Git hooks path: Configured"
else
    echo "  ❌ Git hooks path: Not configured"
fi

echo ""

# Check PM Monitor
echo "📊 PM Monitor:"
if [ -f "scripts/pm_monitor.py" ]; then
    echo "  ✅ PM Monitor script: Found"
    if python scripts/pm_monitor.py --status > /dev/null 2>&1; then
        echo "  ✅ PM Monitor: Working"
    else
        echo "  ⚠️ PM Monitor: May need dependencies"
    fi
else
    echo "  ❌ PM Monitor script: Not found"
fi

echo ""

# Check GitHub Actions
echo "🚀 GitHub Actions:"
if [ -f ".github/workflows/pr-validation.yml" ]; then
    echo "  ✅ PR Validation workflow: Configured"
else
    echo "  ❌ PR Validation workflow: Not found"
fi

echo ""

# Check Configuration
echo "⚙️ Configuration:"
if [ -f "prevention_config.json" ]; then
    echo "  ✅ Prevention config: Found"
else
    echo "  ❌ Prevention config: Not found"
fi

echo ""
echo "🎯 Prevention-First Status: $([ -f ".githooks/pre-commit" ] && [ -f "scripts/pm_monitor.py" ] && [ -f ".github/workflows/pr-validation.yml" ] && echo "✅ Active" || echo "❌ Incomplete")"
