# macOS Setup Guide - LeanVibe Agent Hive

**🎯 Goal**: Get LeanVibe Agent Hive running on macOS in under 10 minutes with optimal performance.

## System Requirements

### Minimum Requirements
- **macOS**: 12.0+ (Monterey)
- **RAM**: 4GB available
- **Storage**: 2GB free space
- **Architecture**: Intel x64 or Apple Silicon (M1/M2/M3)

### Recommended Configuration
- **macOS**: 13.0+ (Ventura) or 14.0+ (Sonoma)
- **RAM**: 8GB+ available
- **Storage**: 10GB+ free space
- **Apple Silicon**: M1 Pro/Max/Ultra, M2/M3 for best performance

## Pre-Installation Setup

### 1. Install Command Line Tools
```bash
# Install Xcode Command Line Tools
xcode-select --install

# Verify installation
xcode-select -p
# Should output: /Applications/Xcode.app/Contents/Developer
```

### 2. Install Homebrew (Recommended)
```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Add to PATH (Apple Silicon)
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

# Add to PATH (Intel)
echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/usr/local/bin/brew shellenv)"

# Verify installation
brew doctor
```

### 3. Install System Dependencies
```bash
# Essential tools
brew install git curl wget jq

# Development tools (optional but recommended)
brew install htop tree httpie

# Python build dependencies
brew install sqlite3 openssl readline xz zlib

# For Apple Silicon - additional tools
if [[ $(uname -m) == "arm64" ]]; then
    brew install --cask docker
fi
```

## Quick Setup Methods

### Method 1: One-Command Setup (Fastest)
```bash
# Download and run setup script
curl -fsSL https://raw.githubusercontent.com/leanvibe/agent-hive/main/scripts/macos-setup.sh | bash
```

**What this script does:**
1. Checks system compatibility
2. Installs UV package manager
3. Clones the repository
4. Sets up Python environment
5. Installs dependencies
6. Runs verification tests
7. Configures development environment

### Method 2: Manual Setup (Step-by-step)

#### Step 1: Install UV Package Manager
```bash
# Using Homebrew (recommended)
brew install uv

# Or using official installer
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zprofile
```

#### Step 2: Clone and Setup Project
```bash
# Clone repository
git clone https://github.com/leanvibe/agent-hive.git
cd agent-hive

# Setup environment
uv sync --dev

# Verify installation
uv run pytest --tb=short -q
```

## macOS-Specific Optimizations

### 1. Apple Silicon Optimizations

#### Environment Variables
```bash
# Add to ~/.zprofile for persistence
cat >> ~/.zprofile << 'EOF'
# LeanVibe Agent Hive - Apple Silicon Optimizations
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
export PYTORCH_ENABLE_MPS_FALLBACK=1
export PYTHONDONTWRITEBYTECODE=1

# UV Configuration
export UV_CACHE_DIR="$HOME/.cache/uv"
export UV_PROJECT_ENVIRONMENT=".venv"
EOF

# Apply immediately
source ~/.zprofile
```

#### Performance Tuning
```bash
# Increase file descriptor limits
echo 'ulimit -n 10240' >> ~/.zprofile

# Optimize for development
echo 'export PYTHONUNBUFFERED=1' >> ~/.zprofile
echo 'export PYTHONDEBUG=0' >> ~/.zprofile

# Apply changes
source ~/.zprofile
```

### 2. Development Tools Configuration

#### VS Code Setup
```bash
# Install VS Code (if not already installed)
brew install --cask visual-studio-code

# Install essential extensions
code --install-extension ms-python.python
code --install-extension ms-python.black-formatter
code --install-extension ms-python.mypy-type-checker
code --install-extension charliermarsh.ruff
code --install-extension ms-vscode.vscode-json

# Open project with optimal settings
cd agent-hive && code .
```

#### Terminal Configuration
```bash
# Install oh-my-zsh for better terminal experience
sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

# Add project aliases
cat >> ~/.zshrc << 'EOF'
# LeanVibe Agent Hive Aliases
alias ah='cd ~/path/to/agent-hive'
alias aht='uv run pytest'
alias ahr='uv run python .claude/orchestrator.py'
alias ahc='uv run python cli.py'
alias ahs='uv run python -m http.server 8000'
alias ahb='uv run python -m build'
alias ahl='tail -f logs/orchestrator.log'
EOF

# Reload configuration
source ~/.zshrc
```

### 3. Docker Setup (Optional)

#### Install Docker Desktop
```bash
# Install Docker Desktop
brew install --cask docker

# Start Docker Desktop (first time)
open /Applications/Docker.app

# Configure Docker for development
mkdir -p ~/.docker/daemon.json
cat > ~/.docker/daemon.json << 'EOF'
{
  "experimental": true,
  "features": {
    "buildkit": true
  },
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  }
}
EOF
```

#### Memory Configuration
```bash
# Recommended Docker settings for Agent Hive:
# Memory: 6GB (8GB+ system) or 4GB (6GB+ system)
# CPU: 4 cores (8-core system) or 2 cores (4-core system)
# Disk: 64GB limit
# Swap: 1GB
```

## Security and Permissions

### 1. System Integrity Protection (SIP)
```bash
# Check SIP status
csrutil status

# If enabled (default and recommended), no action needed
# Agent Hive works with SIP enabled
```

### 2. Privacy Settings
```bash
# Grant Terminal full disk access for development
# System Preferences → Security & Privacy → Privacy → Full Disk Access
# Add Terminal.app and your IDE

# For VS Code specifically
# Add /Applications/Visual Studio Code.app
```

### 3. File Permissions
```bash
# Set proper permissions for project directory
chmod -R 755 ~/agent-hive
find ~/agent-hive -name "*.sh" -exec chmod +x {} \;

# Verify permissions
ls -la ~/agent-hive/scripts/
```

## Troubleshooting macOS Issues

### Common Issues and Solutions

#### 1. UV Installation Issues
```bash
# If UV installation fails
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH manually
export PATH="$HOME/.cargo/bin:$PATH"
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.zprofile

# Verify installation
uv --version
```

#### 2. Python Version Issues
```bash
# Check Python version
python3 --version

# If version is less than 3.12, install via UV
uv python install 3.12
uv python pin 3.12

# Or use Homebrew
brew install python@3.12
brew link python@3.12
```

#### 3. Permission Denied Errors
```bash
# Fix ownership of UV cache
sudo chown -R $(whoami) ~/.cache/uv

# Fix project permissions
chmod -R 755 .
find . -name "*.py" -exec chmod 644 {} \;
find . -name "*.sh" -exec chmod 755 {} \;
```

#### 4. Port Already in Use
```bash
# Find process using port 8080
lsof -i :8080

# Kill process (replace PID with actual process ID)
kill -9 PID

# Use alternative port
uv run python .claude/orchestrator.py --port 8081
```

#### 5. Apple Silicon Compatibility
```bash
# Force x86 emulation if needed (rare)
arch -x86_64 uv sync

# Check if running under Rosetta
sysctl -n sysctl.proc_translated

# Install Rosetta 2 if needed
softwareupdate --install-rosetta
```

#### 6. Memory Issues
```bash
# Check memory usage
top -o MEM

# Clear system cache
sudo purge

# Increase swap (macOS manages automatically, but you can monitor)
sysctl vm.swapusage
```

### Development-Specific Issues

#### 1. Hot Reload Not Working
```bash
# Install fswatch for file monitoring
brew install fswatch

# Run with file watching
fswatch -o . | while read f; do uv run python .claude/orchestrator.py --reload; done
```

#### 2. Test Failures
```bash
# Run tests with verbose output
uv run pytest -v --tb=long

# Check for macOS-specific test markers
uv run pytest -m "not macos_skip" -v

# Clear test cache
find . -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
```

#### 3. IDE Integration Issues
```bash
# Reset VS Code Python interpreter
# Command Palette → Python: Select Interpreter → ./venv/bin/python

# Clear VS Code workspace settings
rm -rf .vscode/settings.json

# Restart VS Code Python extension
# Command Palette → Python: Restart Language Server
```

## Performance Optimization

### 1. System-Level Optimizations
```bash
# Disable spotlight indexing for project directory (optional)
sudo mdutil -i off ~/agent-hive

# Enable performance mode (reduces thermal throttling)
sudo pmset -a lowpowermode 0

# Optimize energy settings
sudo pmset -a displaysleep 10 disksleep 10 sleep 30 hibernatemode 0
```

### 2. Development Optimizations
```bash
# Enable aggressive garbage collection
export PYTHONMALLOC=malloc
export PYTHONASYNCIODEBUG=0

# Optimize UV for development
export UV_CONCURRENT_BUILDS=4
export UV_CONCURRENT_DOWNLOADS=8

# Add to ~/.zprofile for persistence
echo 'export UV_CONCURRENT_BUILDS=4' >> ~/.zprofile
echo 'export UV_CONCURRENT_DOWNLOADS=8' >> ~/.zprofile
```

### 3. Network Optimizations
```bash
# Use fastest DNS servers
sudo networksetup -setdnsservers Wi-Fi 1.1.1.1 8.8.8.8
sudo networksetup -setdnsservers Ethernet 1.1.1.1 8.8.8.8

# Verify DNS changes
scutil --dns | grep nameserver
```

## Health Check and Verification

### 1. System Health Check
```bash
# Run comprehensive health check
uv run python scripts/health_check.py --platform macos

# Quick verification
uv run python -c "
import sys
print(f'Python: {sys.version}')
print(f'Platform: {sys.platform}')
print(f'Architecture: {sys.platform}')

import claude
print('✅ Agent Hive import successful')
"
```

### 2. Performance Benchmarks
```bash
# Run performance tests
uv run pytest tests/performance/ -v --benchmark

# Monitor resource usage during tests
uv run pytest tests/performance/ -v &
top -pid $!
```

### 3. Development Environment Test
```bash
# Test all core functionality
uv run pytest tests/test_orchestrator.py -v
uv run pytest tests/test_multi_agent_coordinator.py -v
uv run pytest tests/integration/ -v

# Test external APIs
uv run python cli.py external-api --api-command status
```

## Production Considerations

### 1. Security Hardening
```bash
# Enable firewall
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on

# Check security configuration
spctl --status
```

### 2. Monitoring Setup
```bash
# Install monitoring tools
brew install htop iftop nethogs

# Setup log rotation
sudo newsyslog -v
```

### 3. Backup Strategy
```bash
# Setup Time Machine backup (exclude cache directories)
tmutil addexclusion ~/agent-hive/.venv
tmutil addexclusion ~/agent-hive/.uv-cache
tmutil addexclusion ~/agent-hive/logs
```

## Next Steps

After successful setup:

1. **Read the Development Guide**: [DEVELOPMENT.md](../../DEVELOPMENT.md)
2. **Try the Quick Start**: [docs/getting-started/quick-start.md](../getting-started/quick-start.md)
3. **Explore Examples**: [examples/](../../examples/)
4. **Join the Community**: [GitHub Discussions](https://github.com/leanvibe/agent-hive/discussions)

## Additional Resources

- **macOS Development Best Practices**: [Apple Developer Documentation](https://developer.apple.com/documentation)
- **Homebrew Package Manager**: [brew.sh](https://brew.sh)
- **UV Package Manager**: [uv documentation](https://docs.astral.sh/uv/)
- **Python on macOS**: [Python.org macOS Guide](https://docs.python.org/3/using/mac.html)

---

**Last Updated**: July 19, 2025  
**Compatibility**: macOS 12.0+ (Monterey), Apple Silicon + Intel  
**Estimated Setup Time**: 5-15 minutes