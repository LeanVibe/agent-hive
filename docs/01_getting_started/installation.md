# Installation Guide

This guide provides detailed installation instructions for LeanVibe Agent Hive on various platforms.

## System Requirements

### Minimum Requirements
- **Python**: 3.12 or higher
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 2GB free space for installation
- **Network**: Internet connection for package downloads

### Recommended System
- **Python**: 3.12+ with virtual environment support
- **Memory**: 16GB RAM for optimal performance
- **Storage**: 10GB free space for development
- **CPU**: Multi-core processor for parallel agent execution

### Platform Support
- ✅ **macOS**: 10.15+ (Intel and Apple Silicon)
- ✅ **Linux**: Ubuntu 20.04+, CentOS 8+, Debian 11+
- ✅ **Windows**: Windows 10+ with WSL2 recommended

## Installation Methods

### Method 1: Quick Install (Recommended)

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/leanvibe/agent-hive.git
cd agent-hive

# Install dependencies and setup environment
uv sync

# Verify installation
python cli.py --version
```

### Method 2: Docker Installation

```bash
# Pull the latest image
docker pull leanvibe/agent-hive:latest

# Run with default configuration
docker run -it --rm leanvibe/agent-hive:latest

# Run with custom configuration
docker run -it --rm -v $(pwd)/config:/app/config leanvibe/agent-hive:latest
```

### Method 3: Development Installation

```bash
# Clone repository for development
git clone https://github.com/leanvibe/agent-hive.git
cd agent-hive

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt

# Setup pre-commit hooks
pre-commit install
```

## Platform-Specific Instructions

### macOS Installation

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.12
brew install python@3.12

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add UV to PATH
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Clone and install Agent Hive
git clone https://github.com/leanvibe/agent-hive.git
cd agent-hive
uv sync

# Verify installation
python cli.py --help
```

### Linux Installation (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Install Python 3.12 and dependencies
sudo apt install python3.12 python3.12-venv python3.12-dev git curl

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

# Clone and install Agent Hive
git clone https://github.com/leanvibe/agent-hive.git
cd agent-hive
uv sync

# Verify installation
python cli.py --version
```

### Windows Installation (WSL2)

```bash
# Install WSL2 (PowerShell as Administrator)
wsl --install

# Restart and setup Ubuntu
# Open Ubuntu terminal and run:
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev git curl

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Clone and install Agent Hive
git clone https://github.com/leanvibe/agent-hive.git
cd agent-hive
uv sync
```

## Configuration

### Environment Setup

Create a `.env` file in the project root:

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
nano .env  # or your preferred editor
```

### Basic Configuration

```bash
# .env file
LEANVIBE_ENV=development
LEANVIBE_LOG_LEVEL=INFO
LEANVIBE_MAX_AGENTS=10
LEANVIBE_REDIS_URL=redis://localhost:6379
LEANVIBE_DATABASE_URL=sqlite:///./agent_hive.db
```

### Advanced Configuration

For production deployments, see the [Configuration Guide](../guides/configuration.md).

## Verification

### Basic Functionality Test

```bash
# Test CLI
python cli.py --help

# Test agent spawn
python cli.py spawn test-agent --type basic

# Test coordination
python cli.py coordinate --agents test-agent

# Check status
python cli.py status
```

### Health Check

```bash
# Run comprehensive health check
python cli.py health-check

# Expected output:
# ✅ Python version: 3.12+
# ✅ Dependencies installed
# ✅ Configuration valid
# ✅ Database connection
# ✅ Redis connection (if configured)
# ✅ Agent spawning capability
```

### Performance Test

```bash
# Run performance benchmarks
python cli.py benchmark

# Test multi-agent coordination
python cli.py test-coordination --agents 5
```

## Troubleshooting

### Common Installation Issues

**Python Version Error**
```bash
# Check Python version
python --version

# If < 3.12, install latest:
# macOS: brew install python@3.12
# Linux: sudo apt install python3.12
# Windows: Download from python.org
```

**UV Installation Failed**
```bash
# Manual UV installation
pip install uv

# Or using pipx
pipx install uv
```

**Permission Errors**
```bash
# On Linux/macOS, avoid sudo pip
# Use virtual environment instead:
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

**Import Errors**
```bash
# Reinstall dependencies
uv sync --reinstall

# Clear cache
uv cache clean

# Check Python path
python -c "import sys; print(sys.path)"
```

### Platform-Specific Issues

**macOS Apple Silicon**
```bash
# If you encounter architecture issues:
arch -arm64 brew install python@3.12
arch -arm64 uv sync
```

**Linux ARM64**
```bash
# Install ARM64 specific packages
sudo apt install python3.12-dev gcc g++ make

# Use platform-specific wheels
uv sync --python-platform linux_aarch64
```

**Windows WSL Issues**
```bash
# Reset WSL if needed
wsl --shutdown
wsl --unregister Ubuntu
wsl --install

# Fix file permissions
chmod +x cli.py
```

### Network Issues

**Corporate Firewall**
```bash
# Configure proxy
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080

# Use corporate certificate
uv sync --cert /path/to/corporate-cert.pem
```

**GitHub Access Issues**
```bash
# Use HTTPS instead of SSH
git clone https://github.com/leanvibe/agent-hive.git

# Configure Git credentials
git config --global credential.helper store
```

## Post-Installation Setup

### Development Environment

```bash
# Install development tools
uv add --dev pytest black flake8 mypy

# Setup IDE integration
# VS Code: Install Python extension
# PyCharm: Configure interpreter to .venv/bin/python
```

### Production Environment

```bash
# Install production dependencies only
uv sync --no-dev

# Setup systemd service (Linux)
sudo cp scripts/agent-hive.service /etc/systemd/system/
sudo systemctl enable agent-hive
sudo systemctl start agent-hive
```

### Database Setup

```bash
# Initialize database
python cli.py db init

# Run migrations
python cli.py db migrate

# Create admin user
python cli.py user create admin --admin
```

## Updating

### Regular Updates

```bash
# Pull latest changes
git pull origin main

# Update dependencies
uv sync

# Run migrations
python cli.py db migrate

# Restart services
python cli.py restart
```

### Version Migration

```bash
# Check current version
python cli.py --version

# Backup before upgrade
python cli.py backup

# Follow migration guide
# See: docs/reference/migration-guide.md
```

## Uninstallation

### Clean Removal

```bash
# Stop all services
python cli.py shutdown

# Remove virtual environment
rm -rf .venv

# Remove configuration (optional)
rm -rf ~/.config/leanvibe

# Remove database (optional)
rm agent_hive.db
```

### Docker Cleanup

```bash
# Remove containers
docker rm $(docker ps -a -q --filter ancestor=leanvibe/agent-hive)

# Remove images
docker rmi leanvibe/agent-hive

# Remove volumes
docker volume prune
```

## Getting Help

### Support Channels
- **Documentation**: [docs.leanvibe.com](https://docs.leanvibe.com)
- **GitHub Issues**: [github.com/leanvibe/agent-hive/issues](https://github.com/leanvibe/agent-hive/issues)
- **Community Discord**: [discord.gg/leanvibe](https://discord.gg/leanvibe)

### Diagnostic Information

When reporting issues, include:

```bash
# System information
python cli.py system-info

# Installation log
uv sync --verbose > install.log 2>&1

# Environment details
python -c "
import sys, platform, os
print(f'Python: {sys.version}')
print(f'Platform: {platform.platform()}')
print(f'Architecture: {platform.machine()}')
print(f'PATH: {os.environ.get(\"PATH\", \"Not set\")}')
"
```

## Next Steps

After successful installation:

1. **First Project**: Follow the [Quick Start Guide](quick-start.md)
2. **Configuration**: Review [Configuration Guide](../guides/configuration.md)
3. **Architecture**: Read [System Overview](../architecture/overview.md)
4. **Tutorials**: Try the [Medium Clone Tutorial](../../tutorials/MEDIUM_CLONE_TUTORIAL.md)

---

**Installation Complete!** 🎉 You're ready to start building with LeanVibe Agent Hive.