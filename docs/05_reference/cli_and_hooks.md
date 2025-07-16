# LeanVibe Agent Hive - CLI Commands and Hooks Reference

## Complete Reference Guide for Autonomous Development

### Overview
This comprehensive reference provides all CLI commands, hooks, and prompts needed to effectively use LeanVibe Agent Hive for autonomous software development. Use this guide to trigger orchestration, spawn agents, monitor progress, and leverage the full power of multi-agent coordination.

---

## 🛠️ CLI Commands Reference

### Core Commands

#### `orchestrate` - Start Orchestration Workflow
Primary command for initiating multi-agent coordination.

```bash
# Basic orchestration
python cli.py orchestrate --workflow feature-dev

# Advanced orchestration with validation
python cli.py orchestrate --workflow feature-dev --validate --parallel

# Project-specific orchestration
python cli.py orchestrate --workflow feature-dev --project medium-clone --agents 5

# Custom workflow orchestration
python cli.py orchestrate --workflow custom --config custom-workflow.yaml
```

**Available Workflows**:
- `feature-dev`: Full-stack feature development
- `documentation-tutorial`: Documentation and tutorial creation
- `testing-validation`: Comprehensive testing and validation
- `deployment-production`: Production deployment workflow
- `security-audit`: Security assessment and hardening
- `performance-optimization`: Performance analysis and optimization
- `health-check`: System health validation
- `custom`: User-defined workflow

**Advanced Options**:
```bash
# Parallel execution with multiple agents
--parallel --agents 5

# Validation mode with quality gates
--validate --quality-gates strict

# Debug mode for troubleshooting
--debug --verbose

# Resume from checkpoint
--resume checkpoint-name

# Force restart if stuck
--force-restart
```

#### `spawn` - Spawn New Task
Create and assign specific tasks to agents.

```bash
# Basic task spawning
python cli.py spawn --task "implement user authentication"

# Agent-specific task assignment
python cli.py spawn --task "create API endpoints" --agent backend

# Deep thinking mode for complex tasks
python cli.py spawn --task "design database schema" --depth ultrathink

# Priority task spawning
python cli.py spawn --task "fix critical bug" --priority high --urgent
```

**Task Depth Levels**:
- `quick`: Fast implementation for simple tasks
- `standard`: Normal implementation depth (default)
- `thorough`: Comprehensive implementation with testing
- `ultrathink`: Deep analysis and best-practice implementation

**Agent Specializations**:
- `backend`: Server-side, APIs, databases
- `frontend`: UI/UX, components, client-side
- `database`: Schema design, queries, optimization
- `testing`: Test coverage, validation, QA
- `devops`: Deployment, CI/CD, infrastructure
- `security`: Security analysis, hardening
- `docs`: Documentation, tutorials, guides

#### `monitor` - Monitor System Status
Track agent progress and system health.

```bash
# Real-time monitoring
python cli.py monitor --real-time

# Metrics and performance monitoring
python cli.py monitor --metrics --performance

# Agent-specific monitoring
python cli.py monitor --agents --filter backend,frontend

# Log monitoring with time filters
python cli.py monitor --logs --last 1h --level info

# Health check monitoring
python cli.py monitor --health --comprehensive
```

**Monitoring Options**:
```bash
# System health
--health                # Basic health check
--health --comprehensive # Complete system validation

# Performance metrics
--metrics               # Basic metrics
--performance          # Performance benchmarks
--load-test            # Load testing simulation

# Agent monitoring
--agents               # All agents status
--agents --filter type # Specific agent types
--agents --active      # Only active agents

# Log monitoring
--logs                 # Recent logs
--logs --last 2h       # Time-filtered logs
--logs --level error   # Error-level logs only
--logs --export file   # Export logs to file
```

#### `checkpoint` - Manage System Checkpoints
Create, restore, and manage development checkpoints.

```bash
# Create named checkpoint
python cli.py checkpoint --name milestone-1

# List all checkpoints
python cli.py checkpoint --list

# Restore from checkpoint
python cli.py checkpoint --restore milestone-1

# Validate checkpoint integrity
python cli.py checkpoint --validate milestone-1

# Archive old checkpoints
python cli.py checkpoint --archive --older-than 30d
```

**Checkpoint Operations**:
```bash
# Creation
--name checkpoint-name     # Create named checkpoint
--auto                    # Auto-generate checkpoint name
--include-state           # Include full system state

# Management
--list                    # List all checkpoints
--list --details          # Detailed checkpoint information
--export checkpoint-name  # Export checkpoint to file
--import checkpoint-file  # Import checkpoint from file

# Restoration
--restore checkpoint-name # Restore from checkpoint
--restore --force         # Force restore even with conflicts
--restore --partial       # Partial restore of specific components

# Validation
--validate checkpoint-name # Validate checkpoint integrity
--validate --all          # Validate all checkpoints
--cleanup                 # Remove corrupted checkpoints
```

### External API Commands

#### `webhook` - Manage Webhook Server
Control webhook server for external integrations.

```bash
# Start webhook server
python cli.py webhook --action start --port 8080

# Check webhook status
python cli.py webhook --action status

# Register webhook handler
python cli.py webhook --action register --event github.push --handler process_push

# Stop webhook server
python cli.py webhook --action stop
```

**Webhook Operations**:
```bash
# Server management
--action start --port 8080    # Start server on port 8080
--action stop                 # Stop webhook server
--action restart             # Restart webhook server
--action status              # Get server status

# Handler management
--action register --event type --handler function
--action unregister --event type
--action list-handlers       # List all registered handlers

# Configuration
--config webhook-config.yaml # Use custom configuration
--rate-limit 100            # Set rate limit (requests per minute)
--secret webhook-secret     # Set webhook secret for validation
```

#### `gateway` - Manage API Gateway
Control API gateway for external service coordination.

```bash
# Start API gateway
python cli.py gateway --action start --port 8081

# Register API route
python cli.py gateway --action register-route --path /api/v1/users --handler user_handler

# Check gateway status
python cli.py gateway --action status

# Enable authentication
python cli.py gateway --action auth --enable --provider oauth2
```

**Gateway Operations**:
```bash
# Server management
--action start --port 8081   # Start gateway on port 8081
--action stop                # Stop API gateway
--action restart            # Restart gateway
--action status             # Get gateway status

# Route management
--action register-route --path /path --handler function
--action unregister-route --path /path
--action list-routes        # List all registered routes

# Security
--action auth --enable --provider oauth2
--action rate-limit --limit 1000
--action cors --enable --origins "*"
```

#### `streaming` - Manage Event Streaming
Control real-time event distribution system.

```bash
# Start event streaming
python cli.py streaming --action start

# Publish test event
python cli.py streaming --action publish-test --event test.message

# Subscribe to events
python cli.py streaming --action subscribe --filter "*.important"

# Get streaming status
python cli.py streaming --action status
```

**Streaming Operations**:
```bash
# Stream management
--action start             # Start event streaming
--action stop              # Stop event streaming
--action status            # Get streaming status

# Event publishing
--action publish --event type --data "message"
--action publish-test      # Publish test event
--action publish-batch     # Publish multiple events

# Event subscription
--action subscribe --filter "pattern"
--action unsubscribe --filter "pattern"
--action list-subscriptions

# Configuration
--buffer-size 1000         # Set event buffer size
--compression gzip         # Enable compression
--retention 24h            # Set event retention time
```

#### `external-api` - Manage External API Integration
Unified command for external API operations.

```bash
# Get integration status
python cli.py external-api --api-command status

# Test all integrations
python cli.py external-api --api-command test-all

# Configure external services
python cli.py external-api --api-command configure --service github

# Health check for external APIs
python cli.py external-api --api-command health
```

---

## 🔗 Git Hooks Reference

### Pre-commit Hook
Automatic quality gates before commits.

**Triggered On**: Every `git commit`

**Quality Checks**:
1. **Python Syntax**: Validates all Python files
2. **CLI Import Validation**: Ensures CLI components work
3. **Basic Functionality**: Tests core CLI commands
4. **Code Quality**: Runs linting and formatting
5. **Project Structure**: Validates directory structure

**Hook Output Example**:
```
🔍 LeanVibe Pre-commit Quality Gate
==================================
📋 Running quality checks on staged files...

🔄 Checking Python syntax...
✅ Python syntax check passed

🔄 Validating CLI import paths...
✅ CLI import validation passed

🔄 Testing CLI basic functionality...
✅ CLI help system functional

✅ Core tests passed

🔄 Checking for common issues...
✅ Code quality checks passed

🔄 Validating project structure...
✅ Project structure validation passed

🎉 All quality checks passed!
✅ Commit is ready to proceed
```

**Manual Hook Execution**:
```bash
# Run pre-commit checks manually
.claude/hooks/pre-commit

# Skip hooks (emergency only)
git commit --no-verify -m "Emergency commit"
```

### Pre-push Hook
Comprehensive integration validation before pushing.

**Triggered On**: Every `git push`

**Integration Checks**:
1. **Comprehensive Python Validation**: Full import testing
2. **CLI Comprehensive Testing**: All commands tested
3. **System Integration Tests**: End-to-end validation
4. **Working Directory Status**: Clean state verification
5. **Branch Integrity**: Commit validation
6. **Performance Validation**: Performance benchmarks

**Hook Output Example**:
```
🚀 LeanVibe Pre-push Integration Gate
====================================
📡 Remote: origin
🔗 URL: https://github.com/LeanVibe/agent-hive.git

🌿 Current branch: feature/new-feature

📋 Running comprehensive integration checks...

🔄 Running comprehensive Python validation...
✅ All core imports successful
✅ Python import validation

🔄 Testing CLI comprehensive functionality...
✅ CLI comprehensive testing

🔄 Running test suite...
✅ System integration test passed
✅ System integration tests

🔄 Checking working directory status...
✅ Working directory clean

🔄 Validating branch integrity...
✅ Branch has commits

🔄 Running performance validation...
✅ CLI performance (250ms)

🎉 All integration checks passed!
✅ Branch is ready for push to origin
```

### Post-commit Hook
Success confirmation and guidance after commits.

**Triggered On**: After successful `git commit`

**Post-commit Actions**:
1. **Commit Summary**: Display commit information
2. **Branch Detection**: Identify branch type and next steps
3. **CLI Status**: Confirm CLI availability
4. **Change Statistics**: Show modified files and lines
5. **Next Steps**: Provide guidance for development flow

**Hook Output Example**:
```
✅ LeanVibe Agent Hive - Commit Successful
=========================================
📝 Commit: a1b2c3d
🌿 Branch: feature/new-feature
👤 Author: Developer Name
📅 Date: 2025-07-15 09:00:00

💬 Message:
Add new feature implementation

🚀 Feature Branch Detected
💡 Next steps:
   1. Continue development on this branch
   2. Push when ready: git push -u origin feature/new-feature
   3. Create pull request for code review

🔧 LeanVibe CLI Status: Available
   Run: python cli.py --help for usage
📊 Files changed: 3
📈 Changes: +150 -25

🎉 Ready for next task!
```

---

## 🎯 Agent Prompts and Workflows

### Development Workflow Prompts

#### Full-Stack Feature Development
```
Initialize full-stack feature development:

REQUIREMENTS:
1. Backend API endpoints with proper validation
2. Frontend components with responsive design
3. Database schema changes if needed
4. Comprehensive testing (unit, integration, E2E)
5. Documentation updates
6. Security considerations

TECHNOLOGY STACK:
- Backend: FastAPI with async/await
- Frontend: Lit components with PWA features
- Database: PostgreSQL with SQLAlchemy
- Testing: pytest + @web/test-runner
- Tools: UV + Bun for dependency management

QUALITY GATES:
- 90%+ test coverage
- Security scan passing
- Performance benchmarks met
- Documentation updated

FEATURE SPECIFICATION:
[Provide detailed feature requirements here]

Please coordinate multiple agents to implement this feature following TDD approach.
```

#### Database Schema Migration
```
Plan and execute database schema changes:

MIGRATION REQUIREMENTS:
1. Analyze current schema and requirements
2. Design new schema with proper relationships
3. Create migration scripts with rollback procedures
4. Update SQLAlchemy models
5. Modify API endpoints for schema changes
6. Update test fixtures and data
7. Performance optimization for new queries

VALIDATION REQUIREMENTS:
- Migration scripts tested on staging data
- Backward compatibility maintained
- Index optimization for performance
- Data integrity constraints enforced
- Documentation updated with schema changes

SCHEMA CHANGES NEEDED:
[Specify the database changes required]

Use Alembic for migrations and maintain production safety.
```

#### Security Implementation
```
Implement comprehensive security measures:

SECURITY REQUIREMENTS:
1. Authentication system (JWT, OAuth, SAML)
2. Authorization with role-based access control
3. Input validation and sanitization
4. SQL injection prevention
5. XSS protection
6. CSRF protection
7. Rate limiting
8. Security headers
9. Audit logging
10. Vulnerability scanning

COMPLIANCE TARGETS:
- OWASP Top 10 compliance
- Data privacy regulations (GDPR, CCPA)
- Industry standards (ISO 27001)

IMPLEMENTATION SCOPE:
[Specify security requirements for your application]

Prioritize security without compromising usability.
```

#### Performance Optimization
```
Optimize application performance:

PERFORMANCE TARGETS:
1. API response time <200ms (P95)
2. Page load time <3s (First Contentful Paint)
3. Database query optimization
4. Memory usage optimization
5. Bundle size optimization
6. Cache strategy implementation

OPTIMIZATION AREAS:
- Database: Index optimization, query analysis
- Backend: Async operations, connection pooling
- Frontend: Code splitting, lazy loading
- Infrastructure: CDN, caching layers

BENCHMARKING:
- Load testing with realistic traffic
- Performance monitoring setup
- Regression testing for performance
- Profiling and bottleneck identification

CURRENT PERFORMANCE ISSUES:
[Describe specific performance problems]

Focus on measurable improvements with monitoring.
```

### Testing and Validation Prompts

#### Comprehensive Testing Implementation
```
Create comprehensive testing suite:

TESTING STRATEGY:
1. Unit tests for all components (90%+ coverage)
2. Integration tests for API endpoints
3. E2E tests for critical user flows
4. Performance tests for scalability
5. Security tests for vulnerabilities
6. Accessibility tests for compliance

TESTING TOOLS:
- Backend: pytest, pytest-asyncio, httpx
- Frontend: @web/test-runner, Playwright
- Performance: Lighthouse, artillery
- Security: bandit, safety, dependency scanning

TEST SCENARIOS:
- Happy path user flows
- Error handling and edge cases
- Authentication and authorization
- Data validation and constraints
- Performance under load
- Security vulnerability testing

QUALITY GATES:
- All tests must pass
- Coverage >90% for new code
- Performance benchmarks met
- Security scans clean

Create tests that are fast, reliable, and maintainable.
```

#### Production Deployment Validation
```
Validate production readiness:

DEPLOYMENT CHECKLIST:
1. Environment configuration validation
2. Database migration testing
3. Security configuration review
4. Performance benchmark validation
5. Monitoring and alerting setup
6. Backup and recovery procedures
7. Rollback procedures tested
8. Documentation completeness

INFRASTRUCTURE VALIDATION:
- Container orchestration (Docker/Kubernetes)
- Load balancing configuration
- SSL/TLS certificate setup
- CDN configuration
- Database connection pooling
- Caching layer configuration

OPERATIONAL READINESS:
- Health check endpoints
- Logging configuration
- Metrics collection
- Error tracking
- Performance monitoring
- Alerting rules

COMPLIANCE VERIFICATION:
- Security standards compliance
- Data privacy requirements
- Industry regulations
- Internal policies

Ensure zero-downtime deployment capability.
```

### Documentation and Tutorial Prompts

#### API Documentation Generation
```
Generate comprehensive API documentation:

DOCUMENTATION REQUIREMENTS:
1. OpenAPI/Swagger specification
2. Endpoint descriptions with examples
3. Request/response schemas
4. Authentication methods
5. Error codes and messages
6. Rate limiting information
7. SDKs and client libraries
8. Interactive API explorer

QUALITY STANDARDS:
- All endpoints documented
- Examples for all operations
- Clear error handling documentation
- Version compatibility information
- Performance characteristics
- Security considerations

FORMATS:
- Interactive Swagger UI
- Postman collection
- Markdown documentation
- PDF export for offline use

AUTO-GENERATION:
- Generate from code annotations
- Keep documentation in sync with code
- Validate examples against actual API
- Version documentation with API changes

Make documentation developer-friendly and comprehensive.
```

#### User Guide Creation
```
Create comprehensive user documentation:

USER DOCUMENTATION TYPES:
1. Getting started guide
2. Feature documentation with screenshots
3. API integration tutorials
4. Troubleshooting guide
5. FAQ section
6. Video tutorials (scripts)
7. Admin user guide
8. Developer documentation

AUDIENCE CONSIDERATIONS:
- End users with varying technical skills
- Developers integrating with the system
- System administrators
- Business stakeholders

DOCUMENTATION FEATURES:
- Step-by-step instructions
- Visual aids (screenshots, diagrams)
- Code examples and snippets
- Search functionality
- Responsive design for mobile
- Accessibility compliance

MAINTENANCE STRATEGY:
- Documentation versioning
- Regular review and updates
- User feedback integration
- Analytics for usage patterns

Create documentation that reduces support burden.
```

---

## 🔧 Configuration and Customization

### Environment Configuration

#### Development Environment Setup
```bash
# Clone and setup LeanVibe Agent Hive
git clone https://github.com/leanvibe/agent-hive.git
cd agent-hive
uv sync

# Configure for your project
export LEANVIBE_PROJECT_NAME="your-project"
export LEANVIBE_ENVIRONMENT="development"
export LEANVIBE_LOG_LEVEL="DEBUG"

# Test configuration
python cli.py monitor --health --comprehensive
```

#### Production Environment Variables
```bash
# System configuration
export LEANVIBE_ENVIRONMENT="production"
export LEANVIBE_LOG_LEVEL="INFO"
export LEANVIBE_DEBUG_MODE="false"

# Database configuration
export DATABASE_URL="postgresql+asyncpg://user:pass@host/db"
export DATABASE_POOL_SIZE="20"
export DATABASE_MAX_OVERFLOW="0"

# Security configuration
export JWT_SECRET_KEY="your-secret-key"
export ENCRYPTION_KEY="your-encryption-key"
export ALLOWED_HOSTS="yourdomain.com,api.yourdomain.com"

# External services
export GITHUB_TOKEN="your-github-token"
export WEBHOOK_SECRET="your-webhook-secret"

# Performance configuration
export WORKER_PROCESSES="4"
export MAX_CONNECTIONS="1000"
export CACHE_TTL="3600"
```

### Custom Workflow Configuration

#### Creating Custom Workflows
Create `workflows/custom-workflow.yaml`:
```yaml
name: "custom-development-workflow"
description: "Custom workflow for specific project needs"
version: "1.0"

agents:
  - name: "backend"
    type: "backend"
    config:
      language: "python"
      framework: "fastapi"
      database: "postgresql"
  - name: "frontend"
    type: "frontend" 
    config:
      framework: "lit"
      features: ["pwa", "responsive"]
  - name: "testing"
    type: "testing"
    config:
      coverage_threshold: 90
      test_types: ["unit", "integration", "e2e"]

stages:
  - name: "planning"
    agents: ["backend", "frontend"]
    tasks:
      - "analyze requirements"
      - "design architecture"
      - "create implementation plan"
  
  - name: "implementation"
    agents: ["backend", "frontend", "testing"]
    parallel: true
    tasks:
      - "implement backend APIs"
      - "create frontend components"
      - "write comprehensive tests"
  
  - name: "validation"
    agents: ["testing"]
    tasks:
      - "run full test suite"
      - "performance testing"
      - "security validation"

quality_gates:
  - name: "test_coverage"
    threshold: 90
    type: "percentage"
  - name: "performance"
    threshold: 200
    type: "response_time_ms"
  - name: "security"
    threshold: 0
    type: "critical_vulnerabilities"
```

#### Using Custom Workflows
```bash
# Execute custom workflow
python cli.py orchestrate --workflow custom --config workflows/custom-workflow.yaml

# Validate workflow configuration
python cli.py orchestrate --workflow custom --config workflows/custom-workflow.yaml --validate-only

# Debug workflow execution
python cli.py orchestrate --workflow custom --config workflows/custom-workflow.yaml --debug
```

---

## 📊 Monitoring and Observability

### Real-time Monitoring Commands

#### System Health Monitoring
```bash
# Continuous health monitoring
python cli.py monitor --health --continuous --interval 30s

# Component health status
python cli.py monitor --health --components database,api,frontend

# Health check with detailed output
python cli.py monitor --health --verbose --export health-report.json
```

#### Performance Monitoring
```bash
# Real-time performance metrics
python cli.py monitor --performance --real-time --graph

# Performance benchmarking
python cli.py monitor --performance --benchmark --iterations 100

# Resource usage monitoring
python cli.py monitor --resources --cpu --memory --disk --network
```

#### Agent Activity Monitoring
```bash
# Monitor all agent activities
python cli.py monitor --agents --activity --real-time

# Filter agents by type and status
python cli.py monitor --agents --filter "backend,frontend" --status active

# Agent performance metrics
python cli.py monitor --agents --performance --metrics task_completion,response_time
```

### Log Analysis and Debugging

#### Log Analysis Commands
```bash
# Stream logs in real-time
python cli.py monitor --logs --follow --level info

# Search logs with patterns
python cli.py monitor --logs --search "error|exception" --last 24h

# Export logs for analysis
python cli.py monitor --logs --export logs-$(date +%Y%m%d).json --format json
```

#### Debug Mode Operations
```bash
# Enable debug mode for all operations
python cli.py --debug orchestrate --workflow feature-dev

# Debug specific agent issues
python cli.py --debug spawn --task "debug task" --agent backend --verbose

# Debug checkpoint and recovery
python cli.py --debug checkpoint --restore last-checkpoint --trace
```

---

## 🚀 Advanced Usage Patterns

### Multi-Project Orchestration

#### Managing Multiple Projects
```bash
# Switch between projects
export LEANVIBE_PROJECT="project-1"
python cli.py orchestrate --workflow feature-dev

export LEANVIBE_PROJECT="project-2"  
python cli.py orchestrate --workflow testing-validation

# Cross-project coordination
python cli.py orchestrate --workflow cross-project --projects "project-1,project-2"
```

#### Project-Specific Configuration
Create `.leanvibe/config.yaml` in each project:
```yaml
project:
  name: "my-awesome-project"
  type: "web-application"
  tech_stack:
    backend: "fastapi"
    frontend: "lit"
    database: "postgresql"

agents:
  preferred_specializations:
    - "backend"
    - "frontend" 
    - "database"
    - "testing"

workflows:
  default: "feature-dev"
  custom_workflows:
    - "custom-workflow.yaml"

quality_gates:
  test_coverage: 90
  performance_threshold: 200
  security_level: "strict"
```

### Integration with External Tools

#### CI/CD Integration
```bash
# GitHub Actions integration
name: LeanVibe Agent Hive CI
on: [push, pull_request]
jobs:
  leanvibe-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup LeanVibe Agent Hive
        run: |
          pip install -r requirements.txt
          python cli.py monitor --health --ci-mode
      - name: Run validation workflow
        run: |
          python cli.py orchestrate --workflow testing-validation --ci-mode
```

#### Development Tool Integration
```bash
# VS Code integration
echo 'alias lv="python cli.py"' >> ~/.bashrc

# Git aliases for common operations
git config --global alias.lv-checkpoint '!python cli.py checkpoint --name'
git config --global alias.lv-monitor '!python cli.py monitor --health'

# Shell completion
python cli.py --generate-completion bash >> ~/.bashrc
```

---

## 📋 Quick Reference Cheatsheet

### Essential Commands
```bash
# Start new feature development
python cli.py orchestrate --workflow feature-dev --validate

# Monitor system health
python cli.py monitor --health --real-time

# Create checkpoint
python cli.py checkpoint --name $(date +%Y%m%d-%H%M)

# Spawn urgent task
python cli.py spawn --task "fix critical issue" --priority high

# Check system status
python cli.py monitor --summary
```

### Emergency Procedures
```bash
# Force restart stuck orchestration
python cli.py orchestrate --force-restart

# Restore from last checkpoint
python cli.py checkpoint --restore last-known-good

# Emergency health check
python cli.py monitor --health --emergency

# Reset to clean state
python cli.py checkpoint --reset --confirm
```

### Daily Development Workflow
```bash
# Morning startup routine
python cli.py monitor --health
python cli.py orchestrate --workflow daily-startup

# Regular progress check
python cli.py monitor --agents --summary

# End of day checkpoint
python cli.py checkpoint --name end-of-day-$(date +%Y%m%d)
```

---

## 💡 Tips and Best Practices

### Effective Agent Coordination
1. **Clear Task Definition**: Provide specific, actionable task descriptions
2. **Appropriate Depth**: Use `--depth ultrathink` for complex architectural decisions
3. **Agent Specialization**: Assign tasks to specialized agents for best results
4. **Parallel Execution**: Use `--parallel` for independent tasks
5. **Regular Monitoring**: Check agent progress frequently with `monitor` commands

### Quality Assurance
1. **Frequent Checkpoints**: Create checkpoints at major milestones
2. **Comprehensive Testing**: Use testing workflows for quality validation
3. **Security First**: Regular security audits with security-focused workflows
4. **Performance Monitoring**: Continuous performance validation
5. **Documentation Sync**: Keep documentation updated with development

### Troubleshooting
1. **Debug Mode**: Use `--debug` flag for detailed operation logs
2. **Health Checks**: Regular system health validation
3. **Agent Logs**: Monitor agent-specific logs for issues
4. **Checkpoint Recovery**: Use checkpoints for quick recovery from issues
5. **Force Restart**: Last resort for stuck operations

---

## 🎓 Learning Path

### Beginner Level
1. Start with basic `orchestrate` and `monitor` commands
2. Learn checkpoint creation and restoration
3. Practice with simple task spawning
4. Understand agent specializations

### Intermediate Level
1. Create custom workflows for your projects
2. Master parallel agent coordination
3. Implement comprehensive monitoring
4. Integrate with external tools and CI/CD

### Advanced Level
1. Design complex multi-project orchestrations
2. Create custom agent specializations
3. Implement advanced monitoring and alerting
4. Contribute to LeanVibe Agent Hive development

---

*This reference guide provides everything needed to effectively use LeanVibe Agent Hive for autonomous software development. For additional help, use `python cli.py <command> --help` or check the comprehensive documentation in the `/docs` directory.*