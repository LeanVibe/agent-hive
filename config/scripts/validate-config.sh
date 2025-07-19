#!/bin/bash
# Configuration Validation Script
# Validates configuration files for all environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$CONFIG_DIR")"

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check required Python packages
    python3 -c "import yaml, jinja2" 2>/dev/null || {
        error "Required Python packages missing. Install with: pip install pyyaml jinja2"
        exit 1
    }
    
    success "Prerequisites check passed"
}

# Validate YAML syntax
validate_yaml_syntax() {
    local file="$1"
    local env="$2"
    
    log "Validating YAML syntax for $env..."
    
    if python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
        success "YAML syntax valid for $env"
        return 0
    else
        error "YAML syntax invalid for $env"
        return 1
    fi
}

# Validate configuration logic
validate_config_logic() {
    local env="$1"
    
    log "Validating configuration logic for $env..."
    
    cd "$PROJECT_ROOT"
    if python3 config/scripts/config-manager.py validate -e "$env" --config-dir config; then
        success "Configuration logic valid for $env"
        return 0
    else
        error "Configuration logic invalid for $env"
        return 1
    fi
}

# Generate test configurations
generate_test_configs() {
    local env="$1"
    
    log "Generating test configurations for $env..."
    
    cd "$PROJECT_ROOT"
    if python3 config/scripts/config-manager.py generate -e "$env" --config-dir config; then
        success "Test configurations generated for $env"
        return 0
    else
        error "Failed to generate test configurations for $env"
        return 1
    fi
}

# Validate environment-specific requirements
validate_environment_requirements() {
    local env="$1"
    
    log "Validating environment-specific requirements for $env..."
    
    case "$env" in
        "development")
            # Development should have debug enabled
            if grep -q "debug: true" "$CONFIG_DIR/environments/$env.yaml"; then
                success "Development debug mode enabled"
            else
                warning "Development debug mode not enabled"
            fi
            ;;
        "production")
            # Production should have debug disabled
            if grep -q "debug: false" "$CONFIG_DIR/environments/$env.yaml"; then
                success "Production debug mode disabled"
            else
                error "Production debug mode should be disabled"
                return 1
            fi
            
            # Production should have security settings
            if grep -q "allow_origins:" "$CONFIG_DIR/environments/$env.yaml"; then
                success "Production CORS settings configured"
            else
                warning "Production CORS settings not explicitly configured"
            fi
            ;;
        "staging")
            # Staging should be production-like but with testing enabled
            if grep -q "testing: true" "$CONFIG_DIR/environments/$env.yaml"; then
                success "Staging testing mode enabled"
            else
                warning "Staging testing mode not enabled"
            fi
            ;;
    esac
    
    return 0
}

# Main validation function
validate_environment() {
    local env="$1"
    local config_file="$CONFIG_DIR/environments/$env.yaml"
    
    if [[ ! -f "$config_file" ]]; then
        error "Configuration file not found: $config_file"
        return 1
    fi
    
    log "Validating environment: $env"
    
    # Validate YAML syntax
    if ! validate_yaml_syntax "$config_file" "$env"; then
        return 1
    fi
    
    # Validate configuration logic
    if ! validate_config_logic "$env"; then
        return 1
    fi
    
    # Generate test configurations
    if ! generate_test_configs "$env"; then
        return 1
    fi
    
    # Validate environment-specific requirements
    if ! validate_environment_requirements "$env"; then
        return 1
    fi
    
    success "All validations passed for environment: $env"
    return 0
}

# Main execution
main() {
    log "Starting configuration validation"
    
    check_prerequisites
    
    # Get list of environments
    environments=()
    for config_file in "$CONFIG_DIR"/environments/*.yaml; do
        if [[ -f "$config_file" ]]; then
            env=$(basename "$config_file" .yaml)
            environments+=("$env")
        fi
    done
    
    if [[ ${#environments[@]} -eq 0 ]]; then
        error "No environment configurations found"
        exit 1
    fi
    
    log "Found environments: ${environments[*]}"
    
    # Validate each environment
    failed_environments=()
    for env in "${environments[@]}"; do
        if ! validate_environment "$env"; then
            failed_environments+=("$env")
        fi
        echo ""  # Add spacing between environments
    done
    
    # Summary
    if [[ ${#failed_environments[@]} -eq 0 ]]; then
        success "All environment configurations are valid!"
        log "Validated environments: ${environments[*]}"
    else
        error "Validation failed for environments: ${failed_environments[*]}"
        exit 1
    fi
}

# Check if specific environment was requested
if [[ $# -eq 1 ]]; then
    ENV="$1"
    if [[ -f "$CONFIG_DIR/environments/$ENV.yaml" ]]; then
        check_prerequisites
        validate_environment "$ENV"
    else
        error "Environment configuration not found: $ENV"
        exit 1
    fi
else
    main
fi