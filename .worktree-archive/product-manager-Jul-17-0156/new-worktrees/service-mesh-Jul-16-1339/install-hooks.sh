#!/bin/bash
#
# LeanVibe Agent Hive - Git Hooks Installation Script
#
# This script installs the LeanVibe git hooks to ensure code quality
# and proper development workflow.
#

set -e

echo "🔧 LeanVibe Agent Hive - Git Hooks Installation"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Error: Not in a git repository${NC}"
    echo "💡 Run this script from the root of the LeanVibe Agent Hive project"
    exit 1
fi

# Check if hooks directory exists
if [ ! -d "hooks" ]; then
    echo -e "${RED}❌ Error: hooks directory not found${NC}"
    echo "💡 Make sure you're in the LeanVibe Agent Hive project root"
    exit 1
fi

echo -e "${BLUE}📁 Project root: $(pwd)${NC}"
echo -e "${BLUE}🎯 Installing LeanVibe git hooks...${NC}"
echo ""

# Function to install a hook
install_hook() {
    local hook_name="$1"
    local hook_source="hooks/$hook_name"
    local hook_dest=".git/hooks/$hook_name"
    
    if [ ! -f "$hook_source" ]; then
        echo -e "${RED}❌ Hook source not found: $hook_source${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}🔄 Installing $hook_name...${NC}"
    
    # Backup existing hook if it exists
    if [ -f "$hook_dest" ] && [ ! -L "$hook_dest" ]; then
        backup_file="$hook_dest.backup.$(date +%Y%m%d_%H%M%S)"
        echo -e "${YELLOW}💾 Backing up existing hook to: $backup_file${NC}"
        mv "$hook_dest" "$backup_file"
    fi
    
    # Copy the hook
    cp "$hook_source" "$hook_dest"
    
    # Make it executable
    chmod +x "$hook_dest"
    
    echo -e "${GREEN}✅ Installed: $hook_name${NC}"
    return 0
}

# Install all hooks
hooks_to_install=("pre-commit" "pre-push" "post-commit")
installed_count=0
failed_count=0

for hook in "${hooks_to_install[@]}"; do
    if install_hook "$hook"; then
        ((installed_count++))
    else
        ((failed_count++))
    fi
done

echo ""
echo "📊 Installation Summary:"
echo -e "${GREEN}✅ Installed: $installed_count hooks${NC}"

if [ $failed_count -gt 0 ]; then
    echo -e "${RED}❌ Failed: $failed_count hooks${NC}"
fi

echo ""

# Test the hooks
echo -e "${BLUE}🧪 Testing installed hooks...${NC}"
echo ""

# Test pre-commit hook
echo -e "${YELLOW}🔄 Testing pre-commit hook...${NC}"
if .git/hooks/pre-commit >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Pre-commit hook working${NC}"
else
    echo -e "${RED}❌ Pre-commit hook failed${NC}"
    ((failed_count++))
fi

# Test post-commit hook
echo -e "${YELLOW}🔄 Testing post-commit hook...${NC}"
if .git/hooks/post-commit >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Post-commit hook working${NC}"
else
    echo -e "${RED}❌ Post-commit hook failed${NC}"
    ((failed_count++))
fi

# Test pre-push hook (with fake parameters)
echo -e "${YELLOW}🔄 Testing pre-push hook...${NC}"
# Create a temporary test branch for pre-push testing
current_branch=$(git branch --show-current)
if [ "$current_branch" = "main" ] || [ "$current_branch" = "master" ]; then
    # Pre-push should fail on main branch (which is expected)
    if .git/hooks/pre-push origin fake-url >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Pre-push hook allows main branch push (unexpected)${NC}"
    else
        echo -e "${GREEN}✅ Pre-push hook correctly blocks main branch push${NC}"
    fi
else
    # Test on feature branch
    if .git/hooks/pre-push origin fake-url >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Pre-push hook working${NC}"
    else
        echo -e "${RED}❌ Pre-push hook failed${NC}"
        ((failed_count++))
    fi
fi

echo ""

if [ $failed_count -eq 0 ]; then
    echo -e "${GREEN}🎉 All hooks installed and tested successfully!${NC}"
    echo ""
    echo -e "${BLUE}📋 Installed hooks:${NC}"
    echo "  🔍 pre-commit  - Runs quality checks before each commit"
    echo "  🚀 pre-push    - Runs integration tests before pushing"
    echo "  ✅ post-commit - Provides commit feedback and next steps"
    echo ""
    echo -e "${BLUE}💡 Usage:${NC}"
    echo "  • Hooks run automatically during git operations"
    echo "  • To skip pre-commit hook: git commit --no-verify"
    echo "  • To skip pre-push hook: git push --no-verify"
    echo "  • View hook status: ls -la .git/hooks/"
    echo ""
    echo -e "${GREEN}🔧 Git hooks are now active for this repository!${NC}"
else
    echo -e "${RED}❌ Some hooks failed installation or testing${NC}"
    echo "💡 Check the error messages above and ensure:"
    echo "  • You have proper permissions"
    echo "  • Python and CLI dependencies are available"
    echo "  • You're in the correct project directory"
    exit 1
fi

exit 0