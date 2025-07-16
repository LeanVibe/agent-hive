# Agent Hive Quick Start Guide

**Time to Complete**: 5 minutes  
**Prerequisites**: Python 3.12+, Git  
**Difficulty**: Beginner  

## Overview
Get Agent Hive up and running quickly with this streamlined guide. You'll have a working multi-agent orchestration system in just a few minutes.

## Prerequisites
- Python 3.12 or higher
- Git
- macOS 10.15+ (optimized for modern macOS development)
- [UV](https://docs.astral.sh/uv/) (recommended for Python dependency management)

## Step-by-Step Instructions

### Step 1: Clone and Setup
Clone the repository and set up your development environment.

```bash
# Clone the repository
git clone https://github.com/leanvibe/agent-hive.git
cd agent-hive

# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or restart terminal

# Setup dependencies
uv sync
```

**Expected Output**:
```
Resolved X packages in XXXms
Installed X packages in XXXms
```

### Step 2: Verify Installation
Test that everything is working correctly.

```bash
# Run the test suite
uv run pytest

# Test Python API
uv run python -c "from advanced_orchestration import MultiAgentCoordinator; print('✅ Agent Hive ready!')"
```

**Validation**:
- [ ] All tests pass
- [ ] Python API imports successfully
- [ ] No import errors

### Step 3: Start Your First Agent Session
Initialize a basic multi-agent coordinator.

```bash
# Start interactive Python session
uv run python
```

```python
# Initialize the coordinator
from advanced_orchestration import MultiAgentCoordinator
from advanced_orchestration.models import CoordinatorConfig

# Create configuration
config = CoordinatorConfig()
print(f"Configuration: {config}")

# Initialize coordinator
coordinator = MultiAgentCoordinator(config)
print("✅ Multi-agent coordinator initialized!")

# Test basic functionality
print("Agent Hive is ready for autonomous development!")
```

**Expected Output**:
```
Configuration: CoordinatorConfig(...)
✅ Multi-agent coordinator initialized!
Agent Hive is ready for autonomous development!
```

### Step 4: Explore the System
Check out the key components and capabilities.

```bash
# View available CLI commands (when implemented)
uv run python cli.py --help

# Explore the codebase structure
ls -la advanced_orchestration/
ls -la tests/
```

**Validation**:
- [ ] CLI help displays
- [ ] Core modules are present
- [ ] Test suite is comprehensive

## What You've Accomplished

✅ **Installed Agent Hive**: Complete installation with all dependencies  
✅ **Verified Setup**: Confirmed all components are working  
✅ **Initialized Coordinator**: Started your first multi-agent session  
✅ **Explored Components**: Familiarized yourself with the system structure  

## Next Steps

### Learn the Fundamentals
- [Installation Guide](installation.md) - Detailed installation options
- [First Project Tutorial](first-project.md) - Build your first agent workflow
- [Architecture Overview](../architecture/overview.md) - Understand the system design

### Build Something Real
- [Medium Clone Tutorial](../../tutorials/MEDIUM_CLONE_TUTORIAL.md) - Complete real-world project
- [Agent Creation Tutorial](../../tutorials/agent-creation.md) - Create custom agents
- [Workflow Customization](../../tutorials/workflow-customization.md) - Customize workflows

### Advanced Configuration
- [Configuration Guide](../guides/configuration.md) - Complete configuration reference
- [Deployment Guide](../../DEPLOYMENT.md) - Production deployment strategies
- [API Reference](../../API_REFERENCE.md) - Complete API documentation

## Troubleshooting

### Common Issues

**Issue**: `uv: command not found`
**Solution**: Install UV with `curl -LsSf https://astral.sh/uv/install.sh | sh`

**Issue**: Python version compatibility
**Solution**: Ensure Python 3.12+ is installed: `python --version`

**Issue**: Import errors
**Solution**: Verify installation: `uv sync` and check virtual environment

### Get Help
- Check [Troubleshooting Guide](../../TROUBLESHOOTING.md)
- Review [Installation Guide](installation.md)
- Ask questions in [GitHub Discussions](https://github.com/leanvibe/agent-hive/discussions)

## Welcome to Agent Hive!

You're now ready to start building autonomous development systems with multi-agent coordination. The system is designed to maximize autonomous work time while maintaining high quality through comprehensive testing and validation.

Happy coding! 🚀