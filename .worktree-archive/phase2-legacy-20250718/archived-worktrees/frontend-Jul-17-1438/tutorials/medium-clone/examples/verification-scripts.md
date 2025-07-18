# Tutorial Verification Scripts

This directory contains comprehensive verification scripts to validate each phase of the tutorial and ensure everything is working correctly.

## 📋 Phase Verification Scripts

### Phase 1: Environment Verification

Create and run this script to verify your environment setup:

```bash
# File: verify-phase1.sh
#!/bin/bash

echo "🔍 Phase 1: Environment Setup Verification"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass_count=0
fail_count=0

check_command() {
    local cmd=$1
    local name=$2
    local expected_pattern=$3
    
    if command -v $cmd &> /dev/null; then
        local version=$($cmd --version 2>&1 | head -1)
        if [[ $version =~ $expected_pattern ]] || [[ -z $expected_pattern ]]; then
            echo -e "✅ $name: ${GREEN}$version${NC}"
            ((pass_count++))
        else
            echo -e "⚠️  $name: ${YELLOW}$version (unexpected version)${NC}"
            ((pass_count++))
        fi
    else
        echo -e "❌ $name: ${RED}Not found${NC}"
        ((fail_count++))
    fi
}

echo -e "\n📦 Package Managers:"
check_command "brew" "Homebrew" "Homebrew"
check_command "uv" "UV" "uv"
check_command "bun" "Bun" "bun"

echo -e "\n🐍 Python Environment:"
check_command "python3" "Python" "Python 3"

echo -e "\n🗃️ Database:"
check_command "psql" "PostgreSQL" "PostgreSQL"

if command -v psql &> /dev/null; then
    if psql -d conduit_tutorial -c "SELECT 1;" &> /dev/null 2>&1; then
        echo -e "✅ Database: ${GREEN}conduit_tutorial accessible${NC}"
        ((pass_count++))
    else
        echo -e "❌ Database: ${RED}conduit_tutorial not accessible${NC}"
        ((fail_count++))
    fi
fi

echo -e "\n🤖 AI Tools:"
check_command "claude" "Claude CLI" "Claude CLI"

echo -e "\n🔧 Development Tools:"
check_command "git" "Git" "git version"
check_command "docker" "Docker" "Docker version"

echo -e "\n🎯 LeanVibe Agent Hive:"
if [ -d "agent-hive" ] || [ -d "../../../.claude" ]; then
    echo -e "✅ Repository: ${GREEN}Found${NC}"
    ((pass_count++))
else
    echo -e "❌ Repository: ${RED}Not found${NC}"
    ((fail_count++))
fi

echo -e "\n📊 Verification Summary:"
echo -e "✅ Passed: ${GREEN}$pass_count${NC}"
echo -e "❌ Failed: ${RED}$fail_count${NC}"

if [ $fail_count -eq 0 ]; then
    echo -e "\n🎉 ${GREEN}Phase 1 verification passed! Ready for Phase 2.${NC}"
    exit 0
else
    echo -e "\n⚠️  ${YELLOW}Some checks failed. Review the installation steps in phase1-environment-setup.md${NC}"
    exit 1
fi
```

### Phase 2: Project Structure Verification

```bash
# File: verify-phase2.sh
#!/bin/bash

echo "🔍 Phase 2: Project Initialization Verification"
echo "=============================================="

PROJECT_DIR="conduit-tutorial"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass_count=0
fail_count=0

check_file() {
    local file=$1
    local description=$2
    
    if [ -f "$file" ]; then
        echo -e "✅ $description: ${GREEN}Found${NC}"
        ((pass_count++))
    else
        echo -e "❌ $description: ${RED}Missing${NC}"
        ((fail_count++))
    fi
}

check_directory() {
    local dir=$1
    local description=$2
    
    if [ -d "$dir" ]; then
        echo -e "✅ $description: ${GREEN}Found${NC}"
        ((pass_count++))
    else
        echo -e "❌ $description: ${RED}Missing${NC}"
        ((fail_count++))
    fi
}

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "❌ Project directory ${RED}$PROJECT_DIR${NC} not found!"
    echo "Please run Phase 2 setup first."
    exit 1
fi

cd "$PROJECT_DIR"

echo -e "\n📁 Project Structure:"
check_file "README.md" "Project README"
check_file "docker-compose.yml" "Docker Compose config"
check_directory "backend" "Backend directory"
check_directory "frontend" "Frontend directory"
check_directory ".claude" "Agent Hive config"
check_directory "scripts" "Development scripts"

echo -e "\n🐍 Backend Structure:"
check_file "backend/pyproject.toml" "Backend dependencies"
check_file "backend/app/main.py" "FastAPI application"
check_directory "backend/app/api" "API routes"
check_directory "backend/app/core" "Core configuration"
check_directory "backend/tests" "Backend tests"

echo -e "\n🌐 Frontend Structure:"
check_file "frontend/package.json" "Frontend dependencies"
check_file "frontend/src/main.ts" "Frontend application"
check_directory "frontend/src/components" "Frontend components"
check_directory "frontend/public" "Static assets"
check_file "frontend/public/index.html" "HTML entry point"

echo -e "\n⚙️ Configuration:"
check_file ".claude/config/tutorial.yaml" "Agent Hive config"
check_directory ".claude/memory" "Agent memory"
check_file "scripts/setup.sh" "Setup script"
check_file "scripts/dev.sh" "Development script"

echo -e "\n🧪 Testing Setup:"
# Test backend imports
if cd backend && python -c "from app.main import app; print('FastAPI app loads')" &> /dev/null; then
    echo -e "✅ Backend: ${GREEN}FastAPI imports working${NC}"
    ((pass_count++))
else
    echo -e "❌ Backend: ${RED}FastAPI import failed${NC}"
    ((fail_count++))
fi
cd ..

# Test frontend compilation
if cd frontend && bun run --silent build &> /dev/null; then
    echo -e "✅ Frontend: ${GREEN}TypeScript compilation working${NC}"
    ((pass_count++))
else
    echo -e "❌ Frontend: ${RED}TypeScript compilation failed${NC}"
    ((fail_count++))
fi
cd ..

echo -e "\n📊 Verification Summary:"
echo -e "✅ Passed: ${GREEN}$pass_count${NC}"
echo -e "❌ Failed: ${RED}$fail_count${NC}"

if [ $fail_count -eq 0 ]; then
    echo -e "\n🎉 ${GREEN}Phase 2 verification passed! Ready for Phase 3.${NC}"
    exit 0
else
    echo -e "\n⚠️  ${YELLOW}Some checks failed. Review the project initialization steps.${NC}"
    exit 1
fi
```

### Phase 3: Development Verification

```bash
# File: verify-phase3.sh
#!/bin/bash

echo "🔍 Phase 3: Core Development Verification"
echo "========================================"

PROJECT_DIR="conduit-tutorial"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "❌ Project directory ${RED}$PROJECT_DIR${NC} not found!"
    exit 1
fi

cd "$PROJECT_DIR"

pass_count=0
fail_count=0

# Check if development servers can start
echo -e "\n🧪 Development Server Tests:"

# Test backend server startup
echo -n "Testing backend server startup... "
cd backend
if timeout 10s uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 &> /dev/null; then
    echo -e "${GREEN}✅ Success${NC}"
    ((pass_count++))
else
    echo -e "${RED}❌ Failed${NC}"
    ((fail_count++))
fi
cd ..

# Test frontend build
echo -n "Testing frontend build... "
cd frontend
if bun run build &> /dev/null; then
    echo -e "${GREEN}✅ Success${NC}"
    ((pass_count++))
else
    echo -e "${RED}❌ Failed${NC}"
    ((fail_count++))
fi
cd ..

# Check for core features implementation
echo -e "\n🎯 Feature Implementation Check:"

# Check authentication endpoints
if grep -q "login\|register" backend/app/api/api_v1/endpoints/auth.py 2>/dev/null; then
    echo -e "✅ Authentication: ${GREEN}Endpoints implemented${NC}"
    ((pass_count++))
else
    echo -e "❌ Authentication: ${RED}Endpoints missing${NC}"
    ((fail_count++))
fi

# Check article endpoints
if grep -q "articles" backend/app/api/api_v1/endpoints/articles.py 2>/dev/null; then
    echo -e "✅ Articles: ${GREEN}Endpoints implemented${NC}"
    ((pass_count++))
else
    echo -e "❌ Articles: ${RED}Endpoints missing${NC}"
    ((fail_count++))
fi

# Check frontend components
if find frontend/src -name "*.ts" -exec grep -l "@customElement" {} \; | wc -l | grep -q "[1-9]"; then
    echo -e "✅ Components: ${GREEN}Lit components found${NC}"
    ((pass_count++))
else
    echo -e "❌ Components: ${RED}No Lit components found${NC}"
    ((fail_count++))
fi

# Database migration check
echo -n "Testing database migrations... "
cd backend
if [ -d "alembic" ] && ls alembic/versions/*.py &> /dev/null; then
    echo -e "${GREEN}✅ Migrations exist${NC}"
    ((pass_count++))
else
    echo -e "${YELLOW}⚠️  No migrations found${NC}"
fi
cd ..

echo -e "\n📊 Verification Summary:"
echo -e "✅ Passed: ${GREEN}$pass_count${NC}"
echo -e "❌ Failed: ${RED}$fail_count${NC}"

if [ $fail_count -eq 0 ]; then
    echo -e "\n🎉 ${GREEN}Phase 3 verification passed! Ready for Phase 4.${NC}"
    exit 0
else
    echo -e "\n⚠️  ${YELLOW}Some checks failed. Review the development implementation.${NC}"
    exit 1
fi
```

### Phase 4: Production Verification

```bash
# File: verify-phase4.sh
#!/bin/bash

echo "🔍 Phase 4: Testing & Deployment Verification"
echo "============================================"

PROJECT_DIR="conduit-tutorial"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "❌ Project directory ${RED}$PROJECT_DIR${NC} not found!"
    exit 1
fi

cd "$PROJECT_DIR"

pass_count=0
fail_count=0

echo -e "\n🧪 Test Suite Verification:"

# Backend tests
echo -n "Running backend tests... "
cd backend
if uv run pytest tests/ --quiet &> /dev/null; then
    test_count=$(uv run pytest tests/ --collect-only --quiet 2>/dev/null | grep -c "test_")
    echo -e "${GREEN}✅ $test_count tests passed${NC}"
    ((pass_count++))
else
    echo -e "${RED}❌ Tests failed${NC}"
    ((fail_count++))
fi
cd ..

# Frontend tests
echo -n "Running frontend tests... "
cd frontend
if bun test &> /dev/null; then
    echo -e "${GREEN}✅ Tests passed${NC}"
    ((pass_count++))
else
    echo -e "${RED}❌ Tests failed${NC}"
    ((fail_count++))
fi
cd ..

echo -e "\n🐳 Docker Verification:"

# Check Dockerfiles
if [ -f "backend/Dockerfile" ]; then
    echo -e "✅ Backend Dockerfile: ${GREEN}Found${NC}"
    ((pass_count++))
else
    echo -e "❌ Backend Dockerfile: ${RED}Missing${NC}"
    ((fail_count++))
fi

if [ -f "frontend/Dockerfile" ]; then
    echo -e "✅ Frontend Dockerfile: ${GREEN}Found${NC}"
    ((pass_count++))
else
    echo -e "❌ Frontend Dockerfile: ${RED}Missing${NC}"
    ((fail_count++))
fi

# Test Docker builds
echo -n "Testing backend Docker build... "
if docker build -t conduit-backend-test backend/ &> /dev/null; then
    echo -e "${GREEN}✅ Success${NC}"
    ((pass_count++))
    docker rmi conduit-backend-test &> /dev/null
else
    echo -e "${RED}❌ Failed${NC}"
    ((fail_count++))
fi

echo -n "Testing frontend Docker build... "
if docker build -t conduit-frontend-test frontend/ &> /dev/null; then
    echo -e "${GREEN}✅ Success${NC}"
    ((pass_count++))
    docker rmi conduit-frontend-test &> /dev/null
else
    echo -e "${RED}❌ Failed${NC}"
    ((fail_count++))
fi

echo -e "\n🚀 Production Configuration:"

# Check production docker-compose
if [ -f "docker-compose.prod.yml" ]; then
    echo -e "✅ Production compose: ${GREEN}Found${NC}"
    ((pass_count++))
else
    echo -e "❌ Production compose: ${RED}Missing${NC}"
    ((fail_count++))
fi

# Check environment configuration
if [ -f ".env.example" ] || [ -f ".env.prod" ]; then
    echo -e "✅ Environment config: ${GREEN}Found${NC}"
    ((pass_count++))
else
    echo -e "❌ Environment config: ${RED}Missing${NC}"
    ((fail_count++))
fi

echo -e "\n📊 Verification Summary:"
echo -e "✅ Passed: ${GREEN}$pass_count${NC}"
echo -e "❌ Failed: ${RED}$fail_count${NC}"

if [ $fail_count -eq 0 ]; then
    echo -e "\n🎉 ${GREEN}Phase 4 verification passed! Tutorial complete!${NC}"
    echo -e "\n🚀 Your Medium clone is ready for production deployment!"
    exit 0
else
    echo -e "\n⚠️  ${YELLOW}Some checks failed. Review the testing and deployment setup.${NC}"
    exit 1
fi
```

## 🔧 Utility Scripts

### Complete Tutorial Verification

```bash
# File: verify-all-phases.sh
#!/bin/bash

echo "🔍 Complete Tutorial Verification"
echo "================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

total_phases=0
passed_phases=0

run_phase_verification() {
    local phase_num=$1
    local script_name="verify-phase${phase_num}.sh"
    
    echo -e "\n" 
    echo "================================================"
    echo "Phase $phase_num Verification"
    echo "================================================"
    
    ((total_phases++))
    
    if [ -f "$SCRIPT_DIR/$script_name" ]; then
        if bash "$SCRIPT_DIR/$script_name"; then
            echo -e "🎉 ${GREEN}Phase $phase_num: PASSED${NC}"
            ((passed_phases++))
        else
            echo -e "❌ ${RED}Phase $phase_num: FAILED${NC}"
        fi
    else
        echo -e "⚠️  ${YELLOW}Phase $phase_num verification script not found${NC}"
    fi
}

# Run all phase verifications
run_phase_verification 1
run_phase_verification 2
run_phase_verification 3
run_phase_verification 4

echo -e "\n"
echo "================================================"
echo "Final Tutorial Verification Summary"
echo "================================================"
echo -e "Total Phases: $total_phases"
echo -e "Passed: ${GREEN}$passed_phases${NC}"
echo -e "Failed: ${RED}$((total_phases - passed_phases))${NC}"

if [ $passed_phases -eq $total_phases ]; then
    echo -e "\n🎉 ${GREEN}CONGRATULATIONS!${NC}"
    echo -e "🎯 All tutorial phases completed successfully!"
    echo -e "🚀 Your Medium clone is fully functional and production-ready!"
    exit 0
else
    echo -e "\n⚠️  ${YELLOW}Some phases need attention.${NC}"
    echo -e "📋 Review the failed phases and fix the issues."
    echo -e "💡 Check the troubleshooting guide: troubleshooting.md"
    exit 1
fi
```

### Development Environment Reset

```bash
# File: reset-tutorial.sh
#!/bin/bash

echo "🔄 Tutorial Environment Reset"
echo "============================"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

read -p "⚠️  This will delete your conduit-tutorial project. Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Reset cancelled."
    exit 1
fi

echo -e "\n🧹 Cleaning up existing project..."

# Stop any running services
echo "Stopping Docker services..."
cd ~/Development/conduit-tutorial 2>/dev/null && docker-compose down &> /dev/null

# Remove project directory
echo "Removing project directory..."
rm -rf ~/Development/conduit-tutorial

# Clean Docker resources
echo "Cleaning Docker resources..."
docker system prune -f &> /dev/null

# Reset database
echo "Resetting database..."
dropdb conduit_tutorial 2>/dev/null || true
createdb conduit_tutorial

echo -e "\n✅ ${GREEN}Tutorial environment reset complete!${NC}"
echo -e "📋 You can now start fresh from Phase 1:"
echo -e "   cd agent-hive/tutorials/medium-clone"
echo -e "   open phase1-environment-setup.md"
```

## 📊 Usage Instructions

### Running Verification Scripts

1. **Make scripts executable**:
```bash
chmod +x tutorials/medium-clone/examples/verify-*.sh
```

2. **Run individual phase verification**:
```bash
# From the tutorial directory
./examples/verify-phase1.sh
./examples/verify-phase2.sh
./examples/verify-phase3.sh
./examples/verify-phase4.sh
```

3. **Run complete verification**:
```bash
./examples/verify-all-phases.sh
```

4. **Reset environment if needed**:
```bash
./examples/reset-tutorial.sh
```

### Integration with Tutorial

These verification scripts are designed to be run after completing each phase to ensure everything is working correctly before proceeding to the next phase.

**Recommended workflow**:
1. Complete Phase 1 → Run `verify-phase1.sh`
2. Complete Phase 2 → Run `verify-phase2.sh`  
3. Complete Phase 3 → Run `verify-phase3.sh`
4. Complete Phase 4 → Run `verify-phase4.sh`
5. Final validation → Run `verify-all-phases.sh`

This ensures a smooth tutorial experience and catches issues early!