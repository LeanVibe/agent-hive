# Tutorial Troubleshooting Guide

**Quick Reference**: Common issues and solutions for the Medium Clone tutorial

## 🚨 Emergency Quick Fixes

### Can't Continue Tutorial?
```bash
# Reset to clean state
cd ~/Development
rm -rf conduit-tutorial
git clone https://github.com/leanvibe-dev/agent-hive.git
cd agent-hive/tutorials/medium-clone
# Start from Phase 1
```

### Agent Hive Not Responding?
```bash
# Restart orchestrator
pkill -f orchestrator
uv run python .claude/orchestrator.py --reset
```

## 📋 Phase-Specific Issues

### Phase 1: Environment Setup

#### UV Installation Issues
**Problem**: `uv: command not found`
```bash
# Reinstall UV
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
# For zsh users
source ~/.zshrc
# Verify
uv --version
```

**Problem**: UV permissions denied
```bash
# Fix permissions
chmod +x ~/.local/bin/uv
# Add to PATH permanently
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### Bun Installation Issues  
**Problem**: Bun installation fails
```bash
# Alternative installation
brew install bun
# Verify
bun --version
```

**Problem**: Bun permissions on macOS
```bash
# Fix macOS security restrictions
xattr -d com.apple.quarantine ~/.bun/bin/bun
```

#### PostgreSQL Issues
**Problem**: PostgreSQL won't start
```bash
# Restart PostgreSQL
brew services restart postgresql@15
# Check status
brew services list | grep postgres

# If still failing, reinstall
brew uninstall postgresql@15
brew install postgresql@15
brew services start postgresql@15
```

**Problem**: Database connection refused
```bash
# Check if PostgreSQL is running
psql -d postgres -c "SELECT version();"

# Create user and database
createuser -s postgres
createdb conduit_tutorial
```

### Phase 2: Project Initialization

#### FastAPI Import Errors
**Problem**: `ModuleNotFoundError: No module named 'fastapi'`
```bash
cd backend
# Reinstall dependencies
uv sync --reinstall
# Verify installation
uv run python -c "import fastapi; print('FastAPI available')"
```

#### Frontend Dependencies Issues
**Problem**: Bun install fails
```bash
cd frontend
# Clear cache and reinstall
rm -rf node_modules bun.lockb
bun install --force
```

**Problem**: TypeScript compilation errors
```bash
# Update TypeScript
bun add --dev typescript@latest
# Check tsconfig.json exists and is valid
cat tsconfig.json
```

#### Agent Hive Configuration Issues
**Problem**: Config file not found
```bash
# Create missing config directory
mkdir -p .claude/config .claude/memory
# Copy default config
cp ~/.claude/config/config.yaml .claude/config/tutorial.yaml
```

### Phase 3: Core Development

#### Agent Coordination Problems
**Problem**: Agents not responding or coordinating
```bash
# Check orchestrator status
ps aux | grep orchestrator
# Restart with debug mode
uv run python .claude/orchestrator.py --debug --verbose
```

**Problem**: Backend agent fails to generate code
```bash
# Check Python environment
uv run python -c "import sys; print(sys.path)"
# Verify agent configuration
cat .claude/config/tutorial.yaml
```

#### Database Migration Issues
**Problem**: Alembic migration fails
```bash
cd backend
# Initialize Alembic (if not done)
uv run alembic init alembic
# Create initial migration
uv run alembic revision --autogenerate -m "Initial migration"
# Apply migration
uv run alembic upgrade head
```

**Problem**: SQLAlchemy model errors
```bash
# Check database connection
uv run python -c "
from app.core.config import settings
print('Database URL:', settings.DATABASE_URL)
"
# Test database connectivity
psql -d conduit_tutorial -c "SELECT 1;"
```

#### Frontend Component Issues
**Problem**: Lit components not rendering
```bash
# Check browser console for errors
# Verify component registration
cat frontend/src/main.ts
# Test component loading
bun run dev
```

### Phase 4: Testing & Deployment

#### Test Failures
**Problem**: Backend tests failing
```bash
cd backend
# Run specific failing test
uv run pytest tests/unit/test_auth_service.py -v
# Check test database
export DATABASE_URL="postgresql://localhost/conduit_test"
uv run pytest tests/ --create-db
```

**Problem**: Frontend tests failing
```bash
cd frontend
# Run tests with verbose output
bun test --verbose
# Check test configuration
cat web-test-runner.config.js
```

#### Docker Issues
**Problem**: Docker build fails
```bash
# Check Docker is running
docker info
# Build with verbose output
docker build --no-cache -t conduit-backend backend/
# Check Dockerfile syntax
docker run --rm -i hadolint/hadolint < backend/Dockerfile
```

**Problem**: Container connectivity issues
```bash
# Check network connectivity
docker network ls
docker network inspect conduit_default
# Test container access
docker exec -it conduit-backend-1 curl http://localhost:8000/health
```

## 🔧 Development Environment Issues

### Python Environment Problems
**Problem**: Import errors or version conflicts
```bash
# Reset Python environment
uv venv --python 3.12
uv sync --reinstall
# Verify Python version
uv run python --version
```

### Node/JavaScript Environment Issues
**Problem**: Module resolution errors
```bash
cd frontend
# Clear all caches
rm -rf node_modules .cache dist
bun install
# Verify installation
bun run build
```

### Git Workflow Issues
**Problem**: Git conflicts or branch issues
```bash
# Reset to clean state
git status
git stash
git checkout main
git pull origin main
# Start fresh feature branch
git checkout -b tutorial/retry-$(date +%s)
```

## 🚀 Performance Issues

### Slow Development Performance
**Problem**: Agents or builds are slow
```bash
# Check system resources
top -l 1 | head -10
# Free up memory
purge  # macOS command to free memory
# Restart Docker if using
docker system prune -f
```

### Database Performance Issues
**Problem**: Slow database queries
```bash
# Check PostgreSQL performance
psql -d conduit_tutorial -c "
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
"
# Restart PostgreSQL
brew services restart postgresql@15
```

## 🔍 Debugging Tools

### Agent Hive Debugging
```bash
# Enable debug mode
export LEANVIBE_SYSTEM_DEBUG_MODE=true
export LEANVIBE_SYSTEM_LOG_LEVEL=DEBUG

# Run with verbose logging
uv run python .claude/orchestrator.py --debug --log-level DEBUG

# Check agent health
uv run python -c "
from .claude.orchestrator import Orchestrator
orchestrator = Orchestrator()
print(orchestrator.get_agent_status())
"
```

### Application Debugging
```bash
# Backend debugging
cd backend
uv run uvicorn app.main:app --reload --log-level debug

# Frontend debugging  
cd frontend
bun run dev --debug

# Database debugging
psql -d conduit_tutorial
# Run: \dt to show tables
# Run: \d users to show user table structure
```

### Network Debugging
```bash
# Check port availability
lsof -i :8000  # Backend port
lsof -i :3000  # Frontend port
lsof -i :5432  # PostgreSQL port

# Test API connectivity
curl -v http://localhost:8000/health
curl -v http://localhost:3000/
```

## 📊 Health Checks

### System Health Verification
```bash
# Run comprehensive health check
cat > ~/check-tutorial-health.sh << 'EOF'
#!/bin/bash
echo "🔍 Tutorial Health Check"
echo "======================="

# Check UV
echo -n "UV: "
if command -v uv &> /dev/null; then
    echo "✅ $(uv --version)"
else
    echo "❌ Not installed"
fi

# Check Bun
echo -n "Bun: "
if command -v bun &> /dev/null; then
    echo "✅ $(bun --version)"
else
    echo "❌ Not installed"
fi

# Check PostgreSQL
echo -n "PostgreSQL: "
if psql -d conduit_tutorial -c "SELECT 1;" &> /dev/null; then
    echo "✅ Connected"
else
    echo "❌ Connection failed"
fi

# Check Docker
echo -n "Docker: "
if docker info &> /dev/null; then
    echo "✅ Running"
else
    echo "❌ Not running"
fi

echo ""
echo "If all items show ✅, your environment is healthy!"
EOF

chmod +x ~/check-tutorial-health.sh
~/check-tutorial-health.sh
```

## 🆘 Getting Help

### Community Support
- **GitHub Issues**: [Report tutorial issues](https://github.com/leanvibe-dev/agent-hive/issues)
- **Discussions**: [Ask questions](https://github.com/leanvibe-dev/agent-hive/discussions)
- **Documentation**: [Complete docs](../../../README.md)

### Self-Help Resources
- **Tutorial README**: [Overview and quick start](./README.md)
- **Main Documentation**: [Development guide](../../../DEVELOPMENT.md)
- **API Reference**: [Complete API docs](../../../API_REFERENCE.md)

### Emergency Recovery
```bash
# Nuclear option: Start completely fresh
cd ~/Development
rm -rf conduit-tutorial agent-hive
# Follow Phase 1 setup from beginning
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
git clone https://github.com/leanvibe-dev/agent-hive.git
cd agent-hive/tutorials/medium-clone
open phase1-environment-setup.md
```

---

**💡 Pro Tip**: Most issues can be resolved by checking the basics:
1. Are all tools installed and updated?
2. Is the database running and accessible?
3. Are you in the correct directory?
4. Have you activated the correct environment?

If you're still stuck, don't hesitate to ask for help in the community forums!