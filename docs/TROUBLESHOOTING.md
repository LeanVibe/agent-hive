# Troubleshooting Guide

**📋 Implementation Status**: This troubleshooting guide covers common issues with tested solutions and workarounds.

Comprehensive troubleshooting guide for LeanVibe Agent Hive - solutions for common issues, error patterns, and system recovery procedures.

## Table of Contents

- [Overview](#overview)
- [Installation and Setup Issues](#installation-and-setup-issues)
- [CLI Command Errors](#cli-command-errors)
- [External API Integration Issues](#external-api-integration-issues)
- [Performance and Resource Issues](#performance-and-resource-issues)
- [Coordination and Agent Issues](#coordination-and-agent-issues)
- [Error Codes Reference](#error-codes-reference)
- [Recovery Procedures](#recovery-procedures)
- [Debug Mode and Logging](#debug-mode-and-logging)
- [Known Issues and Workarounds](#known-issues-and-workarounds)

## Overview

This guide provides solutions for common issues encountered when using LeanVibe Agent Hive. Each section includes error symptoms, root causes, and step-by-step solutions.

### Quick Diagnostic Commands

```bash
# Basic system health check
python cli.py monitor --health

# Verify CLI functionality
python cli.py --help

# Check dependencies
python -c "import cli; print('CLI module available')"

# Performance check
python cli.py performance --action dashboard
```

## Installation and Setup Issues

### Issue: "ModuleNotFoundError" or Import Errors

**Symptoms:**
```
ModuleNotFoundError: No module named 'advanced_orchestration'
ModuleNotFoundError: No module named 'external_api'
```

**Root Cause:** Missing dependencies or incorrect Python environment.

**Solutions:**

1. **Verify Python Version:**
   ```bash
   python --version  # Should be 3.12+
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Check Python Path:**
   ```bash
   python -c "import sys; print('\n'.join(sys.path))"
   ```

4. **Virtual Environment Setup:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

5. **Manual Module Check:**
   ```bash
   python -c "import advanced_orchestration; print('Advanced orchestration available')"
   python -c "import external_api; print('External API available')"
   ```

### Issue: "Permission Denied" Errors

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: 'checkpoints'
```

**Root Cause:** Insufficient file system permissions.

**Solutions:**

1. **Check Directory Permissions:**
   ```bash
   ls -la checkpoints/
   ```

2. **Create Directory with Proper Permissions:**
   ```bash
   mkdir -p checkpoints
   chmod 755 checkpoints
   ```

3. **Fix Ownership (if needed):**
   ```bash
   sudo chown -R $USER:$USER checkpoints/
   ```

## CLI Command Errors

### Issue: CLI Commands Timeout

**Symptoms:**
```
TimeoutExpired: Command 'python cli.py monitor' timed out after 30 seconds
```

**Root Cause:** System resource constraints or hanging processes.

**Solutions:**

1. **Check System Resources:**
   ```bash
   # Check CPU and memory usage
   top
   # or
   htop
   ```

2. **Increase Timeout:**
   ```bash
   # For programmatic usage, increase timeout values
   timeout 60 python cli.py monitor --health
   ```

3. **Kill Hanging Processes:**
   ```bash
   # Find Python processes
   ps aux | grep "cli.py"
   
   # Kill specific process
   kill -9 <process_id>
   ```

4. **Resource Optimization:**
   ```bash
   # Clear system caches
   python cli.py performance --action clear
   
   # Restart with minimal resources
   python cli.py monitor --health
   ```

### Issue: "Command Not Found" Errors

**Symptoms:**
```
python: can't open file 'cli.py': [Errno 2] No such file or directory
```

**Root Cause:** Working directory or file path issues.

**Solutions:**

1. **Verify Current Directory:**
   ```bash
   pwd
   ls -la cli.py
   ```

2. **Use Absolute Path:**
   ```bash
   python /full/path/to/cli.py --help
   ```

3. **Add to PATH (optional):**
   ```bash
   export PATH="$PATH:/path/to/leanvibe"
   ```

## External API Integration Issues

### Issue: API Gateway Initialization Errors

**Symptoms:**
```
❌ Failed to initialize systems: ApiGateway() takes no arguments
💡 Check if the advanced_orchestration module is available
```

**Root Cause:** Configuration class mismatch or missing parameters.

**Known Issue:** This is a documented configuration issue with the external API components.

**Workarounds:**

1. **Check Individual Components:**
   ```bash
   # Test basic CLI without external APIs
   python cli.py monitor --health
   python cli.py dashboard --format compact
   ```

2. **Use Alternative Commands:**
   ```bash
   # Instead of external-api status, check individual components
   python cli.py monitor --metrics
   python cli.py performance --action dashboard
   ```

3. **Manual Configuration Check:**
   ```python
   # Test external API imports
   python -c "
   try:
       from external_api.models import ApiGatewayConfig
       print('✅ External API models available')
   except ImportError as e:
       print(f'❌ Import error: {e}')
   "
   ```

**Future Resolution:** This issue is tracked for resolution in upcoming updates.

### Issue: Webhook Server Port Conflicts

**Symptoms:**
```
❌ Webhook server failed: [Errno 48] Address already in use
```

**Root Cause:** Port already in use by another process.

**Solutions:**

1. **Check Port Usage:**
   ```bash
   # Check what's using port 8080
   lsof -i :8080
   netstat -an | grep 8080
   ```

2. **Use Different Port:**
   ```bash
   python cli.py webhook --action start --port 8082
   ```

3. **Kill Process Using Port:**
   ```bash
   # Find and kill process
   sudo lsof -t -i:8080 | xargs kill -9
   ```

4. **Check Available Ports:**
   ```bash
   # Find available ports
   python -c "
   import socket
   for port in range(8080, 8090):
       with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
           result = s.connect_ex(('localhost', port))
           if result != 0:
               print(f'Port {port} is available')
               break
   "
   ```

## Performance and Resource Issues

### Issue: High Memory Usage

**Symptoms:**
- System becomes slow
- CLI commands timeout frequently
- Out of memory errors

**Root Cause:** Resource leaks or insufficient system resources.

**Solutions:**

1. **Monitor Resource Usage:**
   ```bash
   python cli.py monitor --metrics
   python cli.py performance --action dashboard
   ```

2. **Clear Performance Metrics:**
   ```bash
   python cli.py performance --action clear
   ```

3. **Restart System Components:**
   ```bash
   # Stop all external services
   python cli.py external-api --api-command stop-all
   
   # Wait and restart
   sleep 5
   python cli.py external-api --api-command start-all
   ```

4. **System Resource Check:**
   ```bash
   # Check system memory
   free -h
   
   # Check disk space
   df -h
   ```

### Issue: Slow CLI Response Times

**Symptoms:**
- CLI commands take >5 seconds to respond
- Timeout errors

**Root Cause:** System overload or inefficient operations.

**Solutions:**

1. **Performance Profiling:**
   ```bash
   # Time CLI commands
   time python cli.py monitor --health
   time python cli.py dashboard --format compact
   ```

2. **Reduce Resource Usage:**
   ```bash
   # Use lightweight commands
   python cli.py monitor  # Instead of --metrics
   python cli.py dashboard --format compact  # Instead of detailed
   ```

3. **System Optimization:**
   ```bash
   # Clear caches
   python cli.py performance --action clear
   
   # Restart with minimal configuration
   python cli.py monitor --health
   ```

## Coordination and Agent Issues

### Issue: Agent Coordination Failures

**Symptoms:**
```
❌ Orchestration failed: Agent coordination timeout
```

**Root Cause:** Agent communication issues or resource constraints.

**Solutions:**

1. **Check System Health:**
   ```bash
   python cli.py monitor --health --comprehensive
   ```

2. **Restart Orchestration:**
   ```bash
   # Use basic workflow first
   python cli.py orchestrate --workflow default
   ```

3. **Check Resource Availability:**
   ```bash
   python cli.py monitor --metrics
   ```

4. **Create Checkpoint Before Retry:**
   ```bash
   python cli.py checkpoint --name "before-retry-$(date +%Y%m%d-%H%M)"
   ```

### Issue: Task Spawning Failures

**Symptoms:**
```
❌ Task creation failed: Agent assignment error
```

**Root Cause:** Agent availability or configuration issues.

**Solutions:**

1. **Use Simpler Task Configuration:**
   ```bash
   # Start with basic task
   python cli.py spawn --task "simple test task" --depth standard
   ```

2. **Check Agent Status:**
   ```bash
   python cli.py dashboard --format compact
   ```

3. **Try Sequential Execution:**
   ```bash
   # Avoid parallel execution if having issues
   python cli.py spawn --task "test task" --depth standard
   # (don't use --parallel flag)
   ```

## Error Codes Reference

### CLI Exit Codes

| Exit Code | Meaning | Common Causes |
|-----------|---------|---------------|
| 0 | Success | Command completed successfully |
| 1 | General Error | Import errors, configuration issues |
| 2 | Misuse | Invalid command syntax |
| 126 | Permission Denied | File permissions, directory access |
| 127 | Command Not Found | Missing dependencies, path issues |
| 130 | Script Terminated | User interrupt (Ctrl+C) |

### Common Error Patterns

| Error Pattern | Likely Cause | Solution |
|---------------|--------------|----------|
| `ModuleNotFoundError` | Missing dependencies | Install requirements |
| `PermissionError` | File system permissions | Fix directory permissions |
| `TimeoutExpired` | Resource constraints | Increase timeout, check resources |
| `ConnectionError` | Network/service issues | Check service status |
| `JSONDecodeError` | Corrupted configuration | Reset configuration |

## Recovery Procedures

### Emergency System Recovery

1. **Complete System Reset:**
   ```bash
   # Stop all services
   python cli.py external-api --api-command stop-all
   
   # Clear performance metrics
   python cli.py performance --action clear
   
   # Basic health check
   python cli.py monitor --health
   
   # Restart with minimal configuration
   python cli.py orchestrate --workflow default
   ```

2. **Checkpoint Recovery:**
   ```bash
   # List available checkpoints
   python cli.py checkpoint --list
   
   # Use most recent checkpoint
   # Note: Restore functionality may be available in future versions
   ```

3. **Configuration Reset:**
   ```bash
   # Backup current configuration
   cp -r checkpoints/ checkpoints.backup/
   
   # Clear corrupted checkpoints
   rm -rf checkpoints/*.json
   
   # Restart system
   python cli.py monitor --health
   ```

### Gradual Recovery Process

1. **Level 1 - Basic Functionality:**
   ```bash
   python cli.py --help
   python cli.py monitor --health
   ```

2. **Level 2 - Core Operations:**
   ```bash
   python cli.py dashboard --format compact
   python cli.py performance --action dashboard
   ```

3. **Level 3 - Advanced Features:**
   ```bash
   python cli.py orchestrate --workflow default
   python cli.py spawn --task "test task" --depth standard
   ```

4. **Level 4 - Full Integration:**
   ```bash
   python cli.py external-api --api-command status
   ```

## Debug Mode and Logging

### Enable Debug Mode

```bash
# Enable debug output for any command
python cli.py --debug monitor --health
python cli.py --debug orchestrate --workflow default
python cli.py --debug spawn --task "debug task"
```

### Logging Configuration

1. **Environment Variables:**
   ```bash
   export LEANVIBE_LOG_LEVEL="DEBUG"
   export LEANVIBE_DEBUG_MODE="true"
   ```

2. **Manual Logging:**
   ```bash
   # Redirect output to file
   python cli.py monitor --health > health-check.log 2>&1
   
   # View logs
   tail -f health-check.log
   ```

3. **Structured Logging:**
   ```python
   # For programmatic usage
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

## Known Issues and Workarounds

### Current Known Issues

1. **External API Configuration Issue**
   - **Issue:** ApiGateway initialization error
   - **Affected Commands:** `external-api --api-command status`
   - **Workaround:** Use individual component commands
   - **Status:** Under investigation

2. **Real-time Monitoring Memory Usage**
   - **Issue:** Memory usage increases during long monitoring sessions
   - **Affected Commands:** `monitor --real-time`
   - **Workaround:** Use shorter monitoring intervals
   - **Status:** Optimization in progress

3. **Checkpoint Restore Functionality**
   - **Issue:** Checkpoint restore not fully implemented
   - **Affected Commands:** `checkpoint --restore`
   - **Workaround:** Manual configuration reset
   - **Status:** Planned for future release

### Version-Specific Issues

#### v1.0.0 Issues
- External API component initialization
- Real-time monitoring resource usage
- Checkpoint restore functionality

### Compatibility Issues

#### Python Version Compatibility
- **Supported:** Python 3.12+
- **Partially Supported:** Python 3.10-3.11 (may have import issues)
- **Not Supported:** Python <3.10

#### Operating System Compatibility
- **Fully Supported:** Linux, macOS
- **Partially Supported:** Windows (some command variations)
- **Known Issues:** Windows path handling in some edge cases

## Getting Additional Help

### Support Channels

1. **Documentation:**
   - API Reference: `docs/API_REFERENCE.md`
   - CLI Commands: `docs/CLI_COMMANDS.md`
   - Integration Examples: `docs/INTEGRATION_EXAMPLES.md`

2. **Command-Line Help:**
   ```bash
   python cli.py --help
   python cli.py <command> --help
   ```

3. **Debug Information:**
   ```bash
   python cli.py --debug <command>
   ```

### Diagnostic Information Collection

When reporting issues, collect the following information:

```bash
# System information
python --version
pip list | grep -E "(click|asyncio|fastapi)"

# CLI version and health
python cli.py --version
python cli.py monitor --health

# Recent logs
tail -n 50 logs/leanvibe.log  # if available

# Performance metrics
python cli.py performance --action dashboard
```

### Issue Reporting Template

```
## Issue Description
Brief description of the problem

## Environment
- Python Version: 
- Operating System: 
- LeanVibe Version: 

## Steps to Reproduce
1. 
2. 
3. 

## Expected Behavior


## Actual Behavior


## Error Messages
```
Include full error messages here
```

## Diagnostic Output
```
Include output from diagnostic commands
```

## Additional Context
Any additional information that might be helpful
```

---

*This troubleshooting guide covers the most common issues encountered with LeanVibe Agent Hive. For issues not covered here, use the debug mode and diagnostic commands to gather more information.*