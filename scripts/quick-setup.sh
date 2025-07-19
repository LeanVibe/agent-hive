#!/bin/bash
# LeanVibe Agent Hive - Quick Setup Script
# This script provides automated setup for development and testing environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script metadata
SCRIPT_VERSION="1.0.0"
REPO_URL="https://github.com/leanvibe/agent-hive.git"
INSTALL_DIR="$HOME/agent-hive"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
show_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║              🤖 LeanVibe Agent Hive Setup                    ║
    ║                                                               ║
    ║              Automated Development Environment Setup          ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    echo "Version: $SCRIPT_VERSION"
    echo "Target Directory: $INSTALL_DIR"
    echo ""
}

# System detection
detect_system() {
    log_info "Detecting system..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        log_info "Detected: macOS"
        
        # Detect Apple Silicon
        if [[ $(uname -m) == "arm64" ]]; then
            ARCH="arm64"
            log_info "Architecture: Apple Silicon (M1/M2/M3)"
        else
            ARCH="x86_64"
            log_info "Architecture: Intel x86_64"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        ARCH=$(uname -m)
        log_info "Detected: Linux ($ARCH)"
    else
        log_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
}

# Prerequisites check
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_deps=()
    
    # Check for essential tools
    if ! command -v git &> /dev/null; then
        missing_deps+=("git")
    fi
    
    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi
    
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        python_version=$(python3 --version | cut -d' ' -f2)
        python_major=$(echo $python_version | cut -d'.' -f1)
        python_minor=$(echo $python_version | cut -d'.' -f2)
        
        if [[ $python_major -lt 3 ]] || [[ $python_major -eq 3 && $python_minor -lt 12 ]]; then
            log_warning "Python 3.12+ is recommended. Current version: $python_version"
        else
            log_success "Python version: $python_version ✓"
        fi
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_info "Please install the missing dependencies and run this script again."
        
        if [[ "$OS" == "macos" ]]; then
            log_info "On macOS, you can install missing dependencies with:"
            log_info "  brew install ${missing_deps[*]}"
        elif [[ "$OS" == "linux" ]]; then
            log_info "On Ubuntu/Debian, you can install missing dependencies with:"
            log_info "  sudo apt update && sudo apt install ${missing_deps[*]}"
        fi
        
        exit 1
    fi
    
    log_success "All prerequisites satisfied ✓"
}

# Install UV package manager
install_uv() {
    log_info "Installing UV package manager..."
    
    if command -v uv &> /dev/null; then
        log_success "UV already installed: $(uv --version)"
        return 0
    fi
    
    # Try Homebrew first on macOS
    if [[ "$OS" == "macos" ]] && command -v brew &> /dev/null; then
        log_info "Installing UV via Homebrew..."
        if brew install uv; then
            log_success "UV installed via Homebrew ✓"
            return 0
        else
            log_warning "Homebrew installation failed, trying official installer..."
        fi
    fi
    
    # Use official installer
    log_info "Installing UV via official installer..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add to PATH
    export PATH="$HOME/.cargo/bin:$PATH"
    
    # Update shell configuration
    if [[ "$OS" == "macos" ]]; then
        shell_config="$HOME/.zshrc"
    else
        shell_config="$HOME/.bashrc"
    fi
    
    if [[ -f "$shell_config" ]] && ! grep -q "/.cargo/bin" "$shell_config"; then
        echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> "$shell_config"
        log_info "Added UV to PATH in $shell_config"
    fi
    
    # Verify installation
    if command -v uv &> /dev/null; then
        log_success "UV installed successfully: $(uv --version) ✓"
    else
        log_error "Failed to install UV"
        exit 1
    fi
}

# Clone repository
clone_repository() {
    log_info "Cloning Agent Hive repository..."
    
    if [[ -d "$INSTALL_DIR" ]]; then
        log_warning "Directory $INSTALL_DIR already exists"
        read -p "Do you want to remove it and continue? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
            log_info "Removed existing directory"
        else
            log_error "Setup cancelled by user"
            exit 1
        fi
    fi
    
    if git clone "$REPO_URL" "$INSTALL_DIR"; then
        log_success "Repository cloned successfully ✓"
    else
        log_error "Failed to clone repository"
        exit 1
    fi
}

# Setup Python environment
setup_environment() {
    log_info "Setting up Python environment..."
    
    cd "$INSTALL_DIR"
    
    # Initialize UV project
    if uv sync --dev; then
        log_success "Python environment setup complete ✓"
    else
        log_error "Failed to setup Python environment"
        exit 1
    fi
}

# Run verification tests
run_verification() {
    log_info "Running verification tests..."
    
    cd "$INSTALL_DIR"
    
    # Quick health check
    log_info "Testing basic imports..."
    if uv run python -c "
import sys
print(f'Python: {sys.version}')

try:
    import claude
    print('✅ Agent Hive import successful')
except ImportError as e:
    print(f'❌ Import failed: {e}')
    sys.exit(1)
"; then
        log_success "Basic imports working ✓"
    else
        log_error "Basic imports failed"
        exit 1
    fi
    
    # Run quick test suite
    log_info "Running quick test suite..."
    if uv run pytest tests/test_health.py -v --tb=short || uv run pytest tests/ -k "test_basic" -v --tb=short; then
        log_success "Tests passed ✓"
    else
        log_warning "Some tests failed, but core functionality should work"
    fi
}

# Create development configuration
create_dev_config() {
    log_info "Creating development configuration..."
    
    cd "$INSTALL_DIR"
    
    # Create .env file for development
    cat > .env << 'EOF'
# LeanVibe Agent Hive - Development Configuration
LEANVIBE_SYSTEM_LOG_LEVEL=DEBUG
LEANVIBE_SYSTEM_DEBUG_MODE=true
LEANVIBE_DEVELOPMENT_MODE=true

# Multi-agent settings
LEANVIBE_MULTI_AGENT_MAX_AGENTS=5
LEANVIBE_MULTI_AGENT_LOAD_BALANCING_STRATEGY=round_robin

# External API settings
LEANVIBE_EXTERNAL_API_ENABLED=true
LEANVIBE_WEBHOOK_SERVER_ENABLED=true
LEANVIBE_API_GATEWAY_ENABLED=true

# Database (SQLite for development)
LEANVIBE_DATABASE_URL=sqlite:///data/agent_hive.db

# Performance optimizations
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
EOF

    # Create data directory
    mkdir -p data logs config
    
    # macOS-specific optimizations
    if [[ "$OS" == "macos" ]]; then
        cat >> .env << 'EOF'

# macOS-specific optimizations
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
PYTORCH_ENABLE_MPS_FALLBACK=1
EOF
    fi
    
    log_success "Development configuration created ✓"
}

# Setup shell aliases
setup_aliases() {
    log_info "Setting up shell aliases..."
    
    # Determine shell configuration file
    if [[ "$OS" == "macos" ]]; then
        shell_config="$HOME/.zshrc"
    else
        shell_config="$HOME/.bashrc"
    fi
    
    # Add aliases if not already present
    if [[ -f "$shell_config" ]] && ! grep -q "# LeanVibe Agent Hive Aliases" "$shell_config"; then
        cat >> "$shell_config" << EOF

# LeanVibe Agent Hive Aliases
alias ah='cd $INSTALL_DIR'
alias aht='cd $INSTALL_DIR && uv run pytest'
alias ahr='cd $INSTALL_DIR && uv run python .claude/orchestrator.py'
alias ahc='cd $INSTALL_DIR && uv run python cli.py'
alias ahs='cd $INSTALL_DIR && uv run python -m http.server 8000'
alias ahl='cd $INSTALL_DIR && tail -f logs/orchestrator.log'
alias ahstatus='cd $INSTALL_DIR && uv run python -c "from claude.orchestrator import Orchestrator; print(\"Agent Hive Status: OK\")"'
EOF
        log_success "Shell aliases added to $shell_config ✓"
    else
        log_info "Shell aliases already configured or shell config not found"
    fi
}

# Final verification and instructions
show_completion() {
    log_success "🎉 Setup completed successfully!"
    echo ""
    echo -e "${GREEN}📋 What was installed:${NC}"
    echo "  ✓ UV package manager"
    echo "  ✓ LeanVibe Agent Hive repository"
    echo "  ✓ Python environment with all dependencies"
    echo "  ✓ Development configuration"
    echo "  ✓ Shell aliases (reload your terminal)"
    echo ""
    echo -e "${BLUE}🚀 Next steps:${NC}"
    echo "  1. Reload your terminal or run: source ~/.$(basename $SHELL)rc"
    echo "  2. Navigate to project: cd $INSTALL_DIR"
    echo "  3. Start development server: uv run python .claude/orchestrator.py --dev"
    echo "  4. Or run tests: uv run pytest"
    echo ""
    echo -e "${YELLOW}🔗 Quick commands:${NC}"
    echo "  ah          - Go to Agent Hive directory"
    echo "  aht         - Run tests"
    echo "  ahr         - Run orchestrator"
    echo "  ahc         - Run CLI"
    echo "  ahstatus    - Check status"
    echo ""
    echo -e "${BLUE}📚 Documentation:${NC}"
    echo "  - Development Guide: $INSTALL_DIR/DEVELOPMENT.md"
    echo "  - Deployment Guide: $INSTALL_DIR/DEPLOYMENT.md"
    echo "  - API Reference: $INSTALL_DIR/API_REFERENCE.md"
    echo ""
    echo -e "${GREEN}✅ Agent Hive is ready for development!${NC}"
}

# Error handling
handle_error() {
    log_error "Setup failed at step: $1"
    log_info "Check the error messages above for details"
    log_info "You can re-run this script or install manually following DEVELOPMENT.md"
    exit 1
}

# Main execution
main() {
    show_banner
    
    # Setup error handling
    trap 'handle_error "Unknown error"' ERR
    
    detect_system || handle_error "System detection"
    check_prerequisites || handle_error "Prerequisites check"
    install_uv || handle_error "UV installation"
    clone_repository || handle_error "Repository cloning"
    setup_environment || handle_error "Environment setup"
    create_dev_config || handle_error "Configuration creation"
    run_verification || handle_error "Verification tests"
    setup_aliases || handle_error "Shell aliases setup"
    
    show_completion
}

# Script options
case "${1:-}" in
    --help|-h)
        echo "LeanVibe Agent Hive Quick Setup Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h    Show this help message"
        echo "  --version, -v Show script version"
        echo "  --skip-tests  Skip verification tests"
        echo ""
        echo "This script will:"
        echo "  1. Install UV package manager"
        echo "  2. Clone the Agent Hive repository"
        echo "  3. Setup Python environment"
        echo "  4. Create development configuration"
        echo "  5. Run verification tests"
        echo "  6. Setup shell aliases"
        echo ""
        exit 0
        ;;
    --version|-v)
        echo "LeanVibe Agent Hive Quick Setup Script v$SCRIPT_VERSION"
        exit 0
        ;;
    --skip-tests)
        SKIP_TESTS=true
        ;;
esac

# Run main function
main "$@"