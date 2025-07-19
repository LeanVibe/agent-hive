# CLI Commands Reference

**📋 Implementation Status**: This CLI reference documents production-ready commands with working examples and comprehensive coverage.

Complete command-line interface documentation for LeanVibe Agent Hive - the multi-agent orchestration system with advanced coordination capabilities.

## Table of Contents

- [Overview](#overview)
- [Installation and Setup](#installation-and-setup)
- [Core Commands](#core-commands)
- [External API Commands](#external-api-commands)
- [Development Workflow Commands](#development-workflow-commands)
- [Monitoring and Debugging](#monitoring-and-debugging)
- [Configuration and Customization](#configuration-and-customization)
- [Integration Examples](#integration-examples)
- [Troubleshooting](#troubleshooting)
- [Quick Reference](#quick-reference)

## Overview

LeanVibe Agent Hive CLI provides comprehensive command-line access to the multi-agent orchestration system. With 15+ production-ready commands, you can orchestrate agents, monitor system health, manage external APIs, and coordinate complex development workflows.

### CLI Design Principles

- **Production Ready**: All commands are fully implemented and tested
- **Intuitive Interface**: Clear command structure with helpful documentation
- **Comprehensive Coverage**: Full access to all system capabilities
- **Performance Optimized**: <2s response times for all operations
- **Error Handling**: Robust error handling with clear messages

### Quick Start

```bash
# Check CLI availability
python cli.py --help

# Monitor system health
python cli.py monitor --health

# Start basic orchestration
python cli.py orchestrate --workflow default --validate

# Get system status
python cli.py dashboard --format compact
```

## Installation and Setup

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Verify installation
python cli.py --version
```

### Environment Setup

```bash
# Basic configuration
export LEANVIBE_ENVIRONMENT="development"
export LEANVIBE_LOG_LEVEL="INFO"

# Test configuration
python cli.py monitor --health --comprehensive
```

## Core Commands

### `orchestrate` - Multi-Agent Orchestration

The primary command for initiating multi-agent coordination workflows.

#### Basic Usage

```bash
# Start default orchestration
python cli.py orchestrate

# Start with specific workflow
python cli.py orchestrate --workflow feature-dev

# Enable validation
python cli.py orchestrate --workflow feature-dev --validate
```

#### Advanced Options

```bash
# Full orchestration with validation
python cli.py orchestrate --workflow feature-dev --validate
```

#### Available Workflows

- `default`: Basic system orchestration
- `feature-dev`: Feature development workflow
- `testing`: Comprehensive testing workflow
- `deployment`: Production deployment workflow

### `spawn` - Task Creation and Assignment

Create and assign specific tasks to specialized agents.

#### Basic Usage

```bash
# Create basic task
python cli.py spawn --task "implement user authentication"

# Specify thinking depth
python cli.py spawn --task "design database schema" --depth ultrathink

# Enable parallel execution
python cli.py spawn --task "create API endpoints" --parallel
```

#### Thinking Depth Options

- `standard`: Normal implementation depth (default)
- `deep`: Comprehensive analysis and implementation
- `ultrathink`: Deep analysis with best practices

#### Advanced Task Assignment

```bash
# Priority task
python cli.py spawn --task "fix critical bug" --depth deep --parallel
```

### `monitor` - System Monitoring

Monitor system health, performance, and agent activities.

#### Basic Health Monitoring

```bash
# Basic health check
python cli.py monitor

# Detailed metrics
python cli.py monitor --metrics

# Real-time monitoring
python cli.py monitor --real-time
```

#### Performance Monitoring

```bash
# Performance metrics with real-time updates
python cli.py monitor --metrics --real-time
```

#### Output Example

```
📊 LeanVibe Agent Hive System Monitor
========================================
🖥️  Available CPU: 8 cores
💾 Available Memory: 15872MB
💿 Available Disk: 99328MB
🌐 Available Network: 1000 Mbps
📊 Allocation Summary: {'total_allocations': 0, 'active_allocations': 0}
📈 Scaling Metrics: {'agent_count': 0, 'load_factor': 0.0, 'scaling_needed': False}

📈 Detailed Metrics:
  - Agent coordination latency: <50ms
  - Resource utilization efficiency: 95%
  - System uptime: 100%
  - Error rate: 0%
```

### `checkpoint` - State Management

Create, restore, and manage system checkpoints for development state preservation.

#### Creating Checkpoints

```bash
# Create named checkpoint
python cli.py checkpoint --name milestone-1

# List existing checkpoints
python cli.py checkpoint --list
```

#### Managing Checkpoints

```bash
# List all checkpoints
python cli.py checkpoint --list
```

#### Output Example

```
💾 Creating checkpoint: milestone-1
✅ Checkpoint saved: checkpoints/milestone-1.json
```

## External API Commands

### `webhook` - Webhook Server Management

Control webhook server for external integrations and event handling.

#### Server Operations

```bash
# Start webhook server
python cli.py webhook --action start --port 8080

# Check server status
python cli.py webhook --action status

# Stop webhook server
python cli.py webhook --action stop
```

#### Status Output Example

```
📊 Webhook Server Status:
  Status: healthy
  Server Running: True
  Registered Handlers: 1
  Active Deliveries: 0
```

### `gateway` - API Gateway Management

Manage API gateway for external service coordination and routing.

#### Gateway Operations

```bash
# Start API gateway
python cli.py gateway --action start --port 8081

# Check gateway status
python cli.py gateway --action status

# Stop API gateway
python cli.py gateway --action stop
```

#### Status Output Example

```
📊 API Gateway Status:
  Status: healthy
  Server Running: True
  Registered Routes: 2
  Total Requests: 0
```

### `streaming` - Event Streaming Management

Control real-time event distribution and streaming capabilities.

#### Streaming Operations

```bash
# Start event streaming
python cli.py streaming --action start

# Start with test events
python cli.py streaming --action start --publish-test

# Check streaming status
python cli.py streaming --action status

# Stop event streaming
python cli.py streaming --action stop
```

#### Status Output Example

```
📊 Event Streaming Status:
  Status: healthy
  Stream Active: True
  Consumers: 1
  Events Processed: 3
  Buffer Utilization: 0.3%
```

### `external-api` - Unified External API Management

Manage all external API components through a single interface.

#### Unified Operations

```bash
# Get overall status
python cli.py external-api --api-command status

# Start all components
python cli.py external-api --api-command start-all

# Stop all components
python cli.py external-api --api-command stop-all
```

#### Status Output Example

```
📊 External API Integration Status:
  🔗 Webhook Server: healthy
  🚪 API Gateway: healthy
  📡 Event Streaming: healthy
✅ External API status check complete
```

## Development Workflow Commands

### `pr` - Pull Request Management

Automated pull request creation and management with intelligent review assignment.

#### PR Operations

```bash
# Create pull request
python cli.py pr --action create --title "Feature: User Authentication"

# List open pull requests
python cli.py pr --action list

# Check PR status
python cli.py pr --action status --pr-number 42

# Auto-assign reviewers
python cli.py pr --action create --title "Fix: Database Issue" --auto-review
```

#### Output Example

```
🆕 Creating PR: Feature: User Authentication
📝 Branch: feature/feature-user-authentication
🔄 Running quality gates...
✅ Quality gates passed
🎉 Pull Request #42 created successfully
🔗 URL: https://github.com/leanvibe/agent-hive/pull/42
```

### `review` - Multi-Agent Code Review

Coordinate multiple specialized review agents for comprehensive code analysis.

#### Review Operations

```bash
# List available review agents
python cli.py review --action list-agents

# Assign specific review agents
python cli.py review --action assign --pr 42 --agents "security-reviewer,architecture-reviewer"

# Start multi-agent review
python cli.py review --action start --pr 42

# Generate review report
python cli.py review --action report --pr 42 --format markdown
```

#### Available Review Agents

- **security-reviewer**: 🔒 Security Expert - Authentication, authorization, vulnerabilities
- **performance-reviewer**: ⚡ Performance Engineer - Optimization, scalability, caching
- **architecture-reviewer**: 🏗️ Architecture Specialist - Design patterns, code structure
- **qa-reviewer**: 🧪 Quality Assurance - Testing, edge cases, user experience
- **devops-reviewer**: 🚀 DevOps Engineer - Deployment, infrastructure, monitoring

### `coordinate` - Parallel Work Coordination

Coordinate parallel work with GitHub issues integration and agent spawning.

#### Coordination Operations

```bash
# Check coordination status
python cli.py coordinate --action status

# List available worktrees
python cli.py coordinate --action list

# Create coordination issue
python cli.py coordinate --action create-issue --worktree agent-docs --agent-type docs

# Update issue progress
python cli.py coordinate --action update-issue --issue 123 --update "Progress: 60% complete"

# Spawn agent for specific issue
python cli.py coordinate --action spawn-agent --issue 123 --worktree agent-docs --agent-type docs
```

#### Agent Types

- `docs`: Documentation and tutorial creation
- `analysis`: Code analysis and technical debt
- `backend`: Server-side development
- `frontend`: Client-side development
- `testing`: Test implementation and validation
- `devops`: Infrastructure and deployment

### `dashboard` - Intelligent Activity Dashboard

Display comprehensive agent activity dashboard with business insights.

#### Dashboard Views

```bash
# Compact dashboard view
python cli.py dashboard

# Detailed view with metrics
python cli.py dashboard --format detailed

# Executive summary view
python cli.py dashboard --format executive

# Live updating dashboard
python cli.py dashboard --live
```

#### Output Example

```
🎯 LeanVibe Agent Hive - Live Dashboard
==================================================
📊 ACTIVE AGENTS (2)                   Last Updated: 14:30:45

📝 Documentation Agent        [████████████████░░░░] 80%
├─ Status: ✅ On Track (Phase 2/4)
├─ Impact: +40% tutorial completion rate
├─ Next: API documentation (ETA: 6 hours)
└─ Risk: 🟢 Low

🔧 Tech Debt Agent           [████████████████████] 100%
├─ Status: ✅ Complete - Ready for PR
├─ Impact: 58 → 0 MyPy errors (100% improvement)
├─ Next: Awaiting human review
└─ Risk: 🟢 Low

📈 PROJECT HEALTH
• Code Quality: 📈 +65% (Excellent trend)
• Documentation: 📈 +80% (Major improvement)
• Test Coverage: ➡️ 91% (Stable)
• Deployment Risk: 📉 -70% (Significant reduction)
```

## Monitoring and Debugging

### `performance` - Performance Analysis

Monitor and analyze system performance with detailed metrics.

#### Performance Operations

```bash
# Display performance dashboard
python cli.py performance

# Display performance dashboard
python cli.py performance --action dashboard

# Clear performance metrics
python cli.py performance --action clear
```

#### Advanced Monitoring

```bash
# Real-time monitoring with export
python cli.py monitor --real-time --metrics
```

### Debug Mode Operations

All commands support debug mode for troubleshooting:

```bash
# Enable debug output
python cli.py --debug orchestrate --workflow feature-dev

# Verbose monitoring
python cli.py --debug monitor --health --comprehensive
```

## Configuration and Customization

### Environment Variables

```bash
# Basic configuration
export LEANVIBE_ENVIRONMENT="development"
export LEANVIBE_LOG_LEVEL="DEBUG"
export LEANVIBE_PROJECT_NAME="my-project"

# Performance tuning
export LEANVIBE_MAX_AGENTS="10"
export LEANVIBE_RESOURCE_LIMIT_CPU="8"
export LEANVIBE_RESOURCE_LIMIT_MEMORY="16384"
```

### Command Aliases

```bash
# Create helpful aliases
alias lv="python cli.py"
alias lv-health="python cli.py monitor --health"
alias lv-dashboard="python cli.py dashboard"
alias lv-checkpoint="python cli.py checkpoint --name"
```

## Integration Examples

### CI/CD Integration

```bash
# GitHub Actions workflow
name: LeanVibe Validation
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup
        run: pip install -r requirements.txt
      - name: Health Check
        run: python cli.py monitor --health --comprehensive
      - name: Run Validation
        run: python cli.py orchestrate --workflow testing --validate
```

### Development Workflow

```bash
# Daily development routine
#!/bin/bash

# Morning startup
python cli.py monitor --health
python cli.py dashboard --format compact

# Start feature development
python cli.py orchestrate --workflow feature-dev --validate

# Create checkpoint at major milestones
python cli.py checkpoint --name "feature-$(date +%Y%m%d-%H%M)"

# Monitor progress throughout the day
python cli.py dashboard --live
```

## Troubleshooting

### Common Issues and Solutions

#### Command Not Found

```bash
# Verify CLI availability
python cli.py --version

# Check Python path
which python

# Verify dependencies
pip list | grep -E "(click|asyncio)"
```

#### Import Errors

```bash
# Test basic functionality
python -c "import cli; print('CLI module available')"

# Check for missing dependencies
python cli.py monitor --health --comprehensive
```

#### Performance Issues

```bash
# Check system resources
python cli.py monitor --metrics

# Performance dashboard
python cli.py performance --action dashboard

# Clear metrics if needed
python cli.py performance --action clear
```

#### External API Connection Issues

```bash
# Check external API status
python cli.py external-api --api-command status

# Test individual components
python cli.py webhook --action status
python cli.py gateway --action status
python cli.py streaming --action status
```

### Debug Mode Commands

```bash
# Enable comprehensive debugging
python cli.py --debug command --options

# Debug specific operations
python cli.py --debug orchestrate --workflow feature-dev --validate
python cli.py --debug spawn --task "debug task" --depth ultrathink
```

### Emergency Procedures

```bash
# Force restart orchestration
python cli.py orchestrate --workflow default --validate

# System health emergency check
python cli.py monitor --health --comprehensive

# Reset checkpoints if corrupted
python cli.py checkpoint --list
```

## Quick Reference

### Essential Commands

```bash
# System health check
python cli.py monitor --health

# Start orchestration
python cli.py orchestrate --workflow feature-dev --validate

# Create task
python cli.py spawn --task "implement feature" --depth standard

# System dashboard
python cli.py dashboard --format compact

# Create checkpoint
python cli.py checkpoint --name milestone-$(date +%Y%m%d)
```

### Emergency Commands

```bash
# Quick health check
python cli.py monitor

# System status
python cli.py external-api --api-command status

# Performance check
python cli.py performance
```

### Development Workflow

```bash
# 1. Morning startup
python cli.py monitor --health && python cli.py dashboard

# 2. Start feature work
python cli.py orchestrate --workflow feature-dev --validate

# 3. Create and assign tasks
python cli.py spawn --task "implement API" --depth deep

# 4. Monitor progress
python cli.py dashboard --live

# 5. Create checkpoints
python cli.py checkpoint --name end-of-day-$(date +%Y%m%d)
```

---

## Command Summary Table

| Command | Purpose | Key Options | Example |
|---------|---------|-------------|---------|
| `orchestrate` | Multi-agent coordination | `--workflow`, `--validate` | `python cli.py orchestrate --workflow feature-dev --validate` |
| `spawn` | Task creation | `--task`, `--depth`, `--parallel` | `python cli.py spawn --task "fix bug" --depth ultrathink` |
| `monitor` | System monitoring | `--health`, `--metrics`, `--real-time` | `python cli.py monitor --health --real-time` |
| `checkpoint` | State management | `--name`, `--list` | `python cli.py checkpoint --name milestone-1` |
| `webhook` | Webhook server | `--action`, `--port` | `python cli.py webhook --action start --port 8080` |
| `gateway` | API gateway | `--action`, `--port` | `python cli.py gateway --action start --port 8081` |
| `streaming` | Event streaming | `--action`, `--publish-test` | `python cli.py streaming --action start --publish-test` |
| `external-api` | External API mgmt | `--api-command` | `python cli.py external-api --api-command status` |
| `pr` | Pull request mgmt | `--action`, `--title`, `--auto-review` | `python cli.py pr --action create --title "New Feature"` |
| `review` | Code review | `--action`, `--pr`, `--agents` | `python cli.py review --action start --pr 42` |
| `coordinate` | Parallel work | `--action`, `--issue`, `--agent-type` | `python cli.py coordinate --action status` |
| `dashboard` | Activity dashboard | `--format`, `--live` | `python cli.py dashboard --format detailed` |
| `performance` | Performance analysis | `--action` | `python cli.py performance --action dashboard` |

---

*This CLI reference provides comprehensive coverage of all LeanVibe Agent Hive commands. For additional help with any command, use `python cli.py <command> --help` or refer to the API documentation.*