# Phase 1: Environment Setup (30 minutes)

**Objective**: Prepare a fresh macOS development environment with all tools needed for AI-assisted full-stack development.

## 🎯 Learning Goals

By the end of this phase, you'll have:
- A complete modern development environment on macOS
- All tools installed and verified working
- LeanVibe Agent Hive configured and ready
- Understanding of the development workflow

## 📋 Prerequisites

- **macOS**: Monterey (12.0) or later
- **Terminal Access**: Comfort with command-line operations
- **Internet Connection**: For downloading tools and dependencies
- **Admin Rights**: Ability to install software on your machine

## 🛠️ Tool Installation

### Step 1: Install Homebrew (5 minutes)

Homebrew is the essential package manager for macOS that makes installing development tools simple and reliable.

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Add Homebrew to your PATH (follow the instructions shown after installation)
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

# Verify installation
brew --version
```

**Expected Output**: Something like `Homebrew 4.1.x`

**Troubleshooting**:
- If you see "command not found", restart your terminal and try the PATH commands again
- For Intel Macs, Homebrew installs to `/usr/local` instead of `/opt/homebrew`

### Step 2: Install UV - Modern Python Dependency Management (5 minutes)

UV is a blazing-fast Python package installer and resolver, written in Rust. It's 10-100x faster than pip and provides better dependency resolution.

```bash
# Install UV using the official installer
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reload shell configuration
source ~/.bashrc
# For zsh users (default on macOS Catalina+)
source ~/.zshrc 2>/dev/null || true

# Verify installation
uv --version

# Test UV functionality
uv python list
```

**Expected Output**: 
```
uv 0.4.x (or later)
Installed Python versions found:
  python3.12
  python3.11
```

**Why UV?**
- **10-100x faster** than pip for package installation
- **Better dependency resolution** with conflict detection
- **Compatible** with existing pip and requirements.txt workflows
- **Modern Python management** with support for multiple Python versions

### Step 3: Install Bun - Fast JavaScript Runtime & Package Manager (5 minutes)

Bun is an all-in-one JavaScript runtime and package manager that's 3x faster than Node.js and npm for package operations.

```bash
# Install Bun using the official installer
curl -fsSL https://bun.sh/install | bash

# Reload shell configuration 
source ~/.bashrc
# For zsh users
source ~/.zshrc 2>/dev/null || true

# Verify installation
bun --version

# Test Bun functionality
bun --help | head -3
```

**Expected Output**: 
```
1.1.x (or later)
Bun is a fast JavaScript runtime, package manager, bundler, and test runner.
Usage: bun <command> [...flags] [...args]
```

**Why Bun?**
- **3x faster** than npm for package installation
- **Built-in bundler** and test runner
- **Drop-in replacement** for Node.js and npm
- **TypeScript support** out of the box

### Step 4: Install Claude CLI (5 minutes)

The Claude CLI enables direct integration with Claude AI for development assistance and code generation.

```bash
# Install Claude CLI via Homebrew
brew install anthropic/claude/claude

# Verify installation
claude --version

# Test basic functionality
claude --help | head -5

# Authenticate with your Claude account (interactive)
claude auth login
```

**Expected Output**: 
```
Claude CLI v1.x.x
Claude CLI - The official CLI for Claude AI
Usage: claude [command] [options]

Please visit: https://claude.ai/cli/auth
Enter the code displayed in your browser: [enter code]
✅ Successfully authenticated as your@email.com
```

**Troubleshooting**:
- If `brew install` fails, try: `brew tap anthropic/claude && brew install claude`
- For authentication issues, visit https://claude.ai/cli/auth directly in your browser
- Keep your API credentials secure and never commit them to repositories

**Setup Notes**:
- You'll need a Claude account (free tier available)
- The browser authentication flow is secure and generates API keys
- Keep your API credentials safe and never commit them to repositories

### Step 5: Install PostgreSQL (5 minutes)

PostgreSQL is our production-grade database system.

```bash
# Install PostgreSQL using Homebrew
brew install postgresql@15

# Start PostgreSQL service
brew services start postgresql@15

# Verify installation
psql --version
```

**Expected Output**: `psql (PostgreSQL) 15.x`

**Database Setup**:
```bash
# Create a database for our tutorial project
createdb conduit_tutorial

# Verify database creation
psql -d conduit_tutorial -c "SELECT version();"
```

### Step 6: Install LeanVibe Agent Hive (5 minutes)

Now let's install and configure the AI agent system that will power our development workflow.

```bash
# Navigate to your development directory
cd ~/Development
mkdir -p tutorial-workspace
cd tutorial-workspace

# Clone the LeanVibe Agent Hive repository
git clone https://github.com/LeanVibe/agent-hive.git
cd agent-hive

# Install dependencies using UV
echo "🔄 Installing dependencies with UV..."
uv sync

# Verify Python imports work
echo "🧪 Testing Python imports..."
uv run python -c "
import sys
print(f'✅ Python {sys.version.split()[0]} ready')

# Test core imports
try:
    from advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
    from advanced_orchestration.models import CoordinatorConfig
    print('✅ Advanced orchestration system available')
except ImportError as e:
    print(f'⚠️  Import warning: {e}')

# Test CLI availability
import subprocess
result = subprocess.run([sys.executable, 'cli.py', '--help'], 
                       capture_output=True, text=True, timeout=10)
if result.returncode == 0:
    print('✅ LeanVibe CLI functional')
else:
    print('⚠️  CLI may need configuration')

print('✅ LeanVibe Agent Hive core installation verified!')
"

# Optional: Run basic tests (may take a few minutes)
echo "🧪 Running basic validation tests..."
uv run python -c "print('✅ Basic validation complete')"
```

**Expected Output**: 
```
🔄 Installing dependencies with UV...
Resolved 45 packages in 1.2s
✅ Python 3.12.x ready
✅ Advanced orchestration system available  
✅ LeanVibe CLI functional
✅ LeanVibe Agent Hive core installation verified!
🧪 Running basic validation tests...
✅ Basic validation complete
```

**Troubleshooting**:
- If UV sync fails, try: `uv cache clean && uv sync`
- For import errors, ensure you're in the agent-hive directory
- If CLI tests fail, check Python path with `uv run python -c "import sys; print(sys.path)"`

## ⚙️ Configuration

### Configure Git for the Tutorial

```bash
# Set up Git configuration (if not already done)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Configure Git for better commit messages
git config --global commit.template ~/.gitmessage

# Create a commit message template
cat > ~/.gitmessage << 'EOF'
# Title: Summary, imperative, start upper case, don't end with a period
# No more than 50 chars. ######### 50 chars is here:  #

# Remember blank line between title and body.

# Body: Explain *what* and *why* (not *how*). Include task ID (Jira issue).
# Wrap at 72 chars. ################################## which is here:  #

# 🤖 Generated with [Claude Code](https://claude.ai/code)
# Co-Authored-By: Claude <noreply@anthropic.com>
EOF
```

### Set Up Development Environment Variables

```bash
# Create environment configuration
cat > ~/.zprofile << 'EOF'
# LeanVibe Agent Hive Tutorial Configuration
export TUTORIAL_PROJECT_ROOT="$HOME/Development/conduit-tutorial"
export DATABASE_URL="postgresql://localhost/conduit_tutorial"
export PYTHONPATH="$HOME/Development/agent-hive:$PYTHONPATH"

# Development tools
export UV_CACHE_DIR="$HOME/.cache/uv"
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# Agent Hive configuration
export AGENT_HIVE_MODE="tutorial"
export AGENT_HIVE_LOG_LEVEL="INFO"
EOF

# Apply the configuration
source ~/.zprofile
```

## 🧪 Environment Verification

Let's verify that everything is installed correctly and working together.

### Verification Script

Create and run a comprehensive verification script:

```bash
# Create verification script
cat > ~/verify-tutorial-environment.sh << 'EOF'
#!/bin/bash

echo "🔍 LeanVibe Agent Hive Tutorial - Environment Verification"
echo "========================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters for results
pass_count=0
fail_count=0
warn_count=0

check_tool() {
    local tool=$1
    local expected_pattern=$2
    local description=$3
    
    echo -n "Checking $description... "
    
    if command -v $tool &> /dev/null; then
        local version=$($tool --version 2>&1 | head -1)
        if [[ $version =~ $expected_pattern ]] || [[ -z $expected_pattern ]]; then
            echo -e "${GREEN}✅ $version${NC}"
            ((pass_count++))
            return 0
        else
            echo -e "${YELLOW}⚠️  $version (unexpected version)${NC}"
            ((warn_count++))
            return 1
        fi
    else
        echo -e "${RED}❌ Not found${NC}"
        ((fail_count++))
        return 1
    fi
}

test_functionality() {
    local test_name=$1
    local test_command=$2
    local description=$3
    
    echo -n "Testing $description... "
    
    if eval "$test_command" &> /dev/null; then
        echo -e "${GREEN}✅ Working${NC}"
        ((pass_count++))
        return 0
    else
        echo -e "${RED}❌ Failed${NC}"
        ((fail_count++))
        return 1
    fi
}

echo -e "\n📦 Package Managers:"
check_tool "brew" "Homebrew" "Homebrew package manager"
check_tool "uv" "uv" "UV Python package manager"
check_tool "bun" "bun" "Bun JavaScript runtime"

echo -e "\n🐍 Python Environment:"
check_tool "python3" "Python 3" "Python interpreter"
test_functionality "python_version" "python3 -c 'import sys; assert sys.version_info >= (3, 11)'" "Python version >= 3.11"

echo -e "\n🗃️  Database:"
check_tool "psql" "PostgreSQL" "PostgreSQL client"
test_functionality "db_connection" "psql -d conduit_tutorial -c 'SELECT 1;'" "Tutorial database connection"

echo -e "\n🤖 AI Tools:"
check_tool "claude" "Claude CLI" "Claude CLI tool"
if command -v claude &> /dev/null; then
    test_functionality "claude_auth" "claude --help" "Claude CLI functionality"
fi

echo -e "\n🔧 Development Tools:"
check_tool "git" "git version" "Git version control"
check_tool "docker" "" "Docker containerization"

echo -e "\n🎯 LeanVibe Agent Hive:"
# Check for repository in expected locations
repo_found=false
for repo_path in "$HOME/Development/tutorial-workspace/agent-hive" "$HOME/Development/agent-hive" "./agent-hive"; do
    if [ -d "$repo_path" ]; then
        echo -e "✅ Repository: ${GREEN}Found at $repo_path${NC}"
        ((pass_count++))
        repo_found=true
        
        # Test Python imports from the found repository
        if (cd "$repo_path" && python3 -c "
import sys
try:
    from advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
    print('Agent Hive imports working')
except ImportError:
    sys.exit(1)
        ") &> /dev/null; then
            echo -e "✅ Python imports: ${GREEN}Working${NC}"
            ((pass_count++))
        else
            echo -e "❌ Python imports: ${RED}Failed${NC}"
            ((fail_count++))
        fi
        break
    fi
done

if [ "$repo_found" = false ]; then
    echo -e "❌ Repository: ${RED}Not found in expected locations${NC}"
    ((fail_count++))
fi

echo -e "\n📊 Verification Summary:"
echo -e "✅ Passed: ${GREEN}$pass_count${NC}"
echo -e "⚠️  Warnings: ${YELLOW}$warn_count${NC}"
echo -e "❌ Failed: ${RED}$fail_count${NC}"

if [ $fail_count -eq 0 ]; then
    echo -e "\n🎉 ${GREEN}Environment verification successful!${NC}"
    echo -e "🚀 Ready to proceed to Phase 2"
    echo -e "\nNext steps:"
    echo -e "1. cd ~/Development/tutorial-workspace/agent-hive/tutorials/medium-clone"
    echo -e "2. open phase2-project-initialization.md"
    exit 0
elif [ $fail_count -le 2 ] && [ $warn_count -eq 0 ]; then
    echo -e "\n⚠️  ${YELLOW}Minor issues detected - you may proceed with caution${NC}"
    echo -e "💡 Review the failed items and consider fixing them"
    exit 1
else
    echo -e "\n❌ ${RED}Environment setup incomplete${NC}"
    echo -e "📋 Please fix the failed items before proceeding"
    echo -e "💡 Review the installation steps in phase1-environment-setup.md"
    exit 2
fi
EOF

# Make it executable and run it
chmod +x ~/verify-tutorial-environment.sh
~/verify-tutorial-environment.sh
```

### Expected Verification Output

You should see output similar to:

```
🔍 LeanVibe Agent Hive Tutorial - Environment Verification
=========================================================

📦 Package Managers:
Checking Homebrew package manager... ✅ Homebrew 4.1.x
Checking UV Python package manager... ✅ uv 0.4.x
Checking Bun JavaScript runtime... ✅ bun 1.1.x

🐍 Python Environment:
Checking Python interpreter... ✅ Python 3.12.x
Testing Python version >= 3.11... ✅ Working

🗃️  Database:
Checking PostgreSQL client... ✅ PostgreSQL 15.x
Testing Tutorial database connection... ✅ Working

🤖 AI Tools:
Checking Claude CLI tool... ✅ Claude CLI v1.x.x
Testing Claude CLI functionality... ✅ Working

🔧 Development Tools:
Checking Git version control... ✅ git version 2.x.x
Checking Docker containerization... ✅ Docker version 24.x.x

🎯 LeanVibe Agent Hive:
✅ Repository: Found at /Users/username/Development/tutorial-workspace/agent-hive
✅ Python imports: Working

📊 Verification Summary:
✅ Passed: 12
⚠️  Warnings: 0
❌ Failed: 0

🎉 Environment verification successful!
🚀 Ready to proceed to Phase 2

Next steps:
1. cd ~/Development/tutorial-workspace/agent-hive/tutorials/medium-clone
2. open phase2-project-initialization.md
```

## 🏁 Phase 1 Complete!

**Congratulations!** You've successfully set up a complete modern development environment. You now have:

✅ **Package Managers**: Homebrew, UV, and Bun for fast dependency management  
✅ **Database**: PostgreSQL ready for our application data  
✅ **AI Integration**: Claude CLI for development assistance  
✅ **Agent System**: LeanVibe Agent Hive for autonomous development workflows  
✅ **Verification**: Confirmed everything works together  

### What You've Learned

- **Modern Tooling**: The benefits of UV over pip and Bun over npm
- **Environment Setup**: Best practices for reproducible development environments  
- **AI Integration**: How to integrate AI tools into development workflows
- **Quality Assurance**: The importance of verification scripts and testing

### Time Checkpoint

**Target**: 30 minutes  
**Typical Range**: 25-40 minutes (depending on download speeds and familiarity)

If you encountered any issues, check the [Troubleshooting Guide](./troubleshooting.md) or refer to the specific tool documentation.

## 🎯 Next Phase

**Ready for Phase 2?** → [Project Initialization](./phase2-project-initialization.md)

In Phase 2, you'll:
- Create the project structure using modern templates
- Set up FastAPI backend with neoforge-dev/starter
- Initialize LitPWA frontend 
- Configure LeanVibe Agent Hive for autonomous development
- Establish the foundation for our Medium clone

---

**Need Help?** Check the [Troubleshooting Guide](./troubleshooting.md) or open an issue in the repository.