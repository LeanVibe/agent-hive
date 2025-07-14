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

UV is a blazing-fast Python package installer and resolver, written in Rust. It's significantly faster than pip and provides better dependency resolution.

```bash
# Install UV using the official installer
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add UV to your PATH
source ~/.bashrc

# Verify installation
uv --version
```

**Expected Output**: Something like `uv 0.2.x`

**Why UV?**
- **10-100x faster** than pip for package installation
- **Better dependency resolution** with conflict detection
- **Compatible** with existing pip and requirements.txt workflows
- **Modern Python management** with support for multiple Python versions

### Step 3: Install Bun - Fast JavaScript Runtime & Package Manager (5 minutes)

Bun is an all-in-one JavaScript runtime and package manager that's significantly faster than Node.js and npm.

```bash
# Install Bun using the official installer
curl -fsSL https://bun.sh/install | bash

# Add Bun to your PATH
source ~/.bashrc

# Verify installation
bun --version
```

**Expected Output**: Something like `1.1.x`

**Why Bun?**
- **3x faster** than npm for package installation
- **Built-in bundler** and test runner
- **Drop-in replacement** for Node.js and npm
- **TypeScript support** out of the box

### Step 4: Install Claude CLI (5 minutes)

The Claude CLI enables direct integration with Claude AI for development assistance.

```bash
# Install Claude CLI
brew install anthropic/claude/claude

# Verify installation
claude --version

# Authenticate with your Claude account
claude auth login
```

**Expected Output**: 
```
Claude CLI v1.x.x
Please visit: https://claude.ai/cli/auth
Enter the code displayed in your browser: [enter code]
✅ Successfully authenticated!
```

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
# Clone the LeanVibe Agent Hive repository
git clone https://github.com/leanvibe-dev/agent-hive.git
cd agent-hive

# Install dependencies using UV
uv sync

# Run the test suite to verify installation
uv run pytest -v

# Verify the installation
uv run python -c "import main; print('LeanVibe Agent Hive installed successfully!')"
```

**Expected Output**: 
```
✅ All tests passed
✅ LeanVibe Agent Hive installed successfully!
```

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
NC='\033[0m' # No Color

check_tool() {
    local tool=$1
    local expected_pattern=$2
    
    if command -v $tool &> /dev/null; then
        local version=$($tool --version 2>&1 | head -1)
        if [[ $version =~ $expected_pattern ]]; then
            echo -e "✅ $tool: ${GREEN}$version${NC}"
            return 0
        else
            echo -e "⚠️  $tool: ${YELLOW}$version (unexpected version)${NC}"
            return 1
        fi
    else
        echo -e "❌ $tool: ${RED}Not found${NC}"
        return 1
    fi
}

echo -e "\n📦 Package Managers:"
check_tool "brew" "Homebrew"
check_tool "uv" "uv"
check_tool "bun" "bun"

echo -e "\n🐍 Python Environment:"
check_tool "python3" "Python 3"
if command -v python3 &> /dev/null; then
    python3 -c "import sys; print(f'✅ Python version: {sys.version.split()[0]}')"
fi

echo -e "\n🗃️  Database:"
check_tool "psql" "PostgreSQL"
if command -v psql &> /dev/null; then
    if psql -d conduit_tutorial -c "SELECT 1;" &> /dev/null; then
        echo -e "✅ Database connection: ${GREEN}conduit_tutorial accessible${NC}"
    else
        echo -e "❌ Database connection: ${RED}conduit_tutorial not accessible${NC}"
    fi
fi

echo -e "\n🤖 AI Tools:"
check_tool "claude" "Claude CLI"

echo -e "\n🔧 Development Tools:"
check_tool "git" "git version"

echo -e "\n🎯 LeanVibe Agent Hive:"
if [ -d "$HOME/Development/agent-hive" ] || [ -d "./agent-hive" ]; then
    echo -e "✅ Repository: ${GREEN}Found${NC}"
    
    # Test Python imports
    if python3 -c "import sys; sys.path.append('agent-hive' if os.path.exists('agent-hive') else '$HOME/Development/agent-hive'); import main" 2>/dev/null; then
        echo -e "✅ Python imports: ${GREEN}Working${NC}"
    else
        echo -e "❌ Python imports: ${RED}Failed${NC}"
    fi
else
    echo -e "❌ Repository: ${RED}Not found${NC}"
fi

echo -e "\n📊 Summary:"
echo "If all items show ✅, your environment is ready for the tutorial!"
echo "If you see ❌ or ⚠️, please review the installation steps above."

echo -e "\n🚀 Next Step:"
echo "Run: cd agent-hive/tutorials/medium-clone && open phase2-project-initialization.md"
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
✅ brew: Homebrew 4.1.x
✅ uv: uv 0.2.x  
✅ bun: bun 1.1.x

🐍 Python Environment:
✅ python3: Python 3.12.x
✅ Python version: 3.12.x

🗃️  Database:
✅ psql: PostgreSQL 15.x
✅ Database connection: conduit_tutorial accessible

🤖 AI Tools:
✅ claude: Claude CLI v1.x.x

🔧 Development Tools:
✅ git: git version 2.x.x

🎯 LeanVibe Agent Hive:
✅ Repository: Found
✅ Python imports: Working

📊 Summary:
If all items show ✅, your environment is ready for the tutorial!

🚀 Next Step:
Run: cd agent-hive/tutorials/medium-clone && open phase2-project-initialization.md
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