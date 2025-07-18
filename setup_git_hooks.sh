#!/bin/bash
# LeanVibe Git Hooks Setup Script
# Sets up prevention-first quality gates

set -e

echo "🔧 LeanVibe Git Hooks Setup"
echo "=========================="
echo ""

# Check if we're in a git repository (supports both regular repos and worktrees)
if [ ! -d ".git" ] && [ ! -f ".git" ]; then
    echo "❌ Error: Not in a git repository"
    echo "💡 Run this script from the root of your git repository"
    exit 1
fi

# Create .githooks directory if it doesn't exist
if [ ! -d ".githooks" ]; then
    echo "📁 Creating .githooks directory..."
    mkdir -p .githooks
fi

# Configure git to use our hooks directory
echo "⚙️  Configuring git to use .githooks directory..."
git config core.hooksPath .githooks

# Make hooks executable
echo "🔒 Setting execute permissions on hooks..."
chmod +x .githooks/pre-commit 2>/dev/null || echo "⚠️  pre-commit hook not found"
chmod +x .githooks/post-commit 2>/dev/null || echo "⚠️  post-commit hook not found"

# Test the setup
echo "🧪 Testing hook setup..."
HOOKS_PATH=$(git config core.hooksPath)
if [ "$HOOKS_PATH" = ".githooks" ]; then
    echo "✅ Git hooks configured successfully"
else
    echo "❌ Git hooks configuration failed"
    exit 1
fi

# List available hooks
echo ""
echo "📋 Available hooks:"
for hook in .githooks/*; do
    if [ -f "$hook" ] && [ -x "$hook" ]; then
        hook_name=$(basename "$hook")
        echo "  ✅ $hook_name"
    fi
done

echo ""
echo "🎉 Git hooks setup complete!"
echo ""
echo "🔍 What this provides:"
echo "  • Pre-commit: PR size validation, syntax checks, quality gates"
echo "  • Post-commit: Success reporting and next steps guidance"
echo ""
echo "💡 To disable hooks temporarily:"
echo "  git commit --no-verify"
echo ""
echo "💡 To check current hooks configuration:"
echo "  git config core.hooksPath"