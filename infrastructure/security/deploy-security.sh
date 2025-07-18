#!/bin/bash
# LeanVibe Agent Hive - Security Deployment Script
# Deploys comprehensive security policies, monitoring, and hardening

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="production"
DEPLOY_MONITORING=true
DEPLOY_POLICIES=true
DEPLOY_SECRETS=false  # Secrets require manual configuration
DRY_RUN=false
VERBOSE=false

# Functions
print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Deploy LeanVibe Agent Hive Security Infrastructure"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV      Target environment (development|staging|production) [default: production]"
    echo "  --skip-monitoring          Skip security monitoring deployment"
    echo "  --skip-policies            Skip security policies deployment"
    echo "  --deploy-secrets           Deploy secret templates (REQUIRES MANUAL CONFIGURATION)"
    echo "  --dry-run                  Show what would be deployed without applying"
    echo "  -v, --verbose              Enable verbose output"
    echo "  -h, --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -e production                    # Deploy all security components"
    echo "  $0 --skip-monitoring               # Deploy without security monitoring"
    echo "  $0 --deploy-secrets --dry-run      # Show secret templates"
    echo ""
    echo "⚠️  WARNING: --deploy-secrets will deploy template secrets that MUST be"
    echo "    updated with real values before production use!"
    echo ""
}

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --skip-monitoring)
            DEPLOY_MONITORING=false
            shift
            ;;
        --skip-policies)
            DEPLOY_POLICIES=false
            shift
            ;;
        --deploy-secrets)
            DEPLOY_SECRETS=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    error "Invalid environment: $ENVIRONMENT. Must be one of: development, staging, production"
fi

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is required but not installed"
    fi
    
    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
    fi
    
    # Check if namespace exists
    if ! kubectl get namespace leanvibe-agent-hive &> /dev/null; then
        warning "Namespace leanvibe-agent-hive does not exist - it will be created"
    fi
    
    # Check cluster admin permissions for security policies
    if ! kubectl auth can-i create podsecuritypolicies &> /dev/null; then
        warning "May not have permissions to create Pod Security Policies"
    fi
    
    success "Prerequisites check passed"
}

# Deploy security policies
deploy_security_policies() {
    if [[ "$DEPLOY_POLICIES" != true ]]; then
        log "Skipping security policies deployment"
        return
    fi
    
    log "Deploying security policies..."
    
    # Pod Security Standards and Policies
    local psp_file="policies/pod-security-standards.yaml"
    
    if [[ "$DRY_RUN" == true ]]; then
        log "Dry run - would deploy Pod Security Policies"
        kubectl apply --dry-run=client -f "$psp_file"
    else
        kubectl apply -f "$psp_file"
    fi
    
    # Network Policies
    local network_policies_file="policies/network-policies.yaml"
    
    if [[ "$DRY_RUN" == true ]]; then
        log "Dry run - would deploy Network Policies"
        kubectl apply --dry-run=client -f "$network_policies_file"
    else
        kubectl apply -f "$network_policies_file"
    fi
    
    success "Security policies deployment completed"
}

# Deploy secret management
deploy_secret_management() {
    if [[ "$DEPLOY_SECRETS" != true ]]; then
        log "Skipping secret management deployment (use --deploy-secrets to enable)"
        return
    fi
    
    warning "Deploying secret templates - THESE MUST BE UPDATED WITH REAL VALUES!"
    
    local secrets_file="secrets/secret-management.yaml"
    
    if [[ "$DRY_RUN" == true ]]; then
        log "Dry run - would deploy secret templates"
        kubectl apply --dry-run=client -f "$secrets_file"
    else
        kubectl apply -f "$secrets_file"
        
        warning "⚠️  SECRET TEMPLATES DEPLOYED - UPDATE IMMEDIATELY!"
        warning "1. Update all 'REPLACE_WITH_*' values in secrets"
        warning "2. Use 'kubectl edit secret <secret-name> -n leanvibe-agent-hive'"
        warning "3. Or use external secret management system"
    fi
    
    success "Secret management deployment completed"
}

# Deploy security monitoring
deploy_security_monitoring() {
    if [[ "$DEPLOY_MONITORING" != true ]]; then
        log "Skipping security monitoring deployment"
        return
    fi
    
    log "Deploying security monitoring..."
    
    local monitoring_file="monitoring/security-monitoring.yaml"
    
    if [[ "$DRY_RUN" == true ]]; then
        log "Dry run - would deploy security monitoring"
        kubectl apply --dry-run=client -f "$monitoring_file"
    else
        kubectl apply -f "$monitoring_file"
        
        # Wait for security monitoring to be ready
        log "Waiting for security monitoring to be ready..."
        kubectl wait --namespace leanvibe-agent-hive \
            --for=condition=ready pod \
            --selector=app.kubernetes.io/name=security-monitoring \
            --timeout=180s || warning "Security monitoring readiness check timed out"
    fi
    
    success "Security monitoring deployment completed"
}

# Validate security deployment
validate_security() {
    if [[ "$DRY_RUN" == true ]]; then
        return
    fi
    
    log "Validating security deployment..."
    
    # Check Pod Security Policies
    if [[ "$DEPLOY_POLICIES" == true ]]; then
        local psp_count=$(kubectl get podsecuritypolicy leanvibe-agent-hive-psp 2>/dev/null | wc -l)
        if [[ "$psp_count" -gt 0 ]]; then
            success "Pod Security Policy is configured"
        else
            warning "Pod Security Policy may not be configured"
        fi
        
        # Check Network Policies
        local np_count=$(kubectl get networkpolicy -n leanvibe-agent-hive -o name | wc -l)
        if [[ "$np_count" -gt 0 ]]; then
            success "Network Policies are configured ($np_count policies)"
        else
            warning "No Network Policies found"
        fi
    fi
    
    # Check Security Monitoring
    if [[ "$DEPLOY_MONITORING" == true ]]; then
        local monitoring_ready=$(kubectl get pods -n leanvibe-agent-hive -l app.kubernetes.io/name=security-monitoring -o jsonpath='{.items[*].status.phase}' | grep -o Running | wc -l)
        if [[ "$monitoring_ready" -gt 0 ]]; then
            success "Security monitoring is running"
        else
            warning "Security monitoring may not be ready"
        fi
    fi
    
    # Check Secrets (if deployed)
    if [[ "$DEPLOY_SECRETS" == true ]]; then
        local secret_count=$(kubectl get secrets -n leanvibe-agent-hive | grep -E "(agent-hive-secrets|grafana-admin)" | wc -l)
        if [[ "$secret_count" -gt 0 ]]; then
            warning "Secret templates are deployed - UPDATE WITH REAL VALUES!"
        fi
    fi
}

# Security assessment
run_security_assessment() {
    if [[ "$DRY_RUN" == true ]]; then
        return
    fi
    
    log "Running security assessment..."
    
    # Check for non-root containers
    local non_root_pods=$(kubectl get pods -n leanvibe-agent-hive -o jsonpath='{.items[*].spec.securityContext.runAsNonRoot}' | grep -o true | wc -l)
    local total_pods=$(kubectl get pods -n leanvibe-agent-hive --no-headers | wc -l)
    
    if [[ "$total_pods" -gt 0 ]]; then
        log "Security Assessment Results:"
        echo "  - Non-root containers: $non_root_pods/$total_pods"
    fi
    
    # Check for read-only root filesystems
    local readonly_pods=$(kubectl get pods -n leanvibe-agent-hive -o jsonpath='{.items[*].spec.containers[*].securityContext.readOnlyRootFilesystem}' | grep -o true | wc -l)
    echo "  - Read-only root filesystems: $readonly_pods containers"
    
    # Check for dropped capabilities
    local dropped_caps=$(kubectl get pods -n leanvibe-agent-hive -o jsonpath='{.items[*].spec.containers[*].securityContext.capabilities.drop}' | grep -o ALL | wc -l)
    echo "  - Containers with dropped capabilities: $dropped_caps"
    
    # Check network policies
    local network_policies=$(kubectl get networkpolicy -n leanvibe-agent-hive --no-headers | wc -l)
    echo "  - Network policies configured: $network_policies"
    
    if [[ "$network_policies" -gt 0 && "$readonly_pods" -gt 0 && "$non_root_pods" -gt 0 ]]; then
        success "Security assessment: GOOD - Multiple security controls active"
    else
        warning "Security assessment: NEEDS IMPROVEMENT - Consider additional hardening"
    fi
}

# Show security commands
show_security_commands() {
    echo ""
    log "Useful security management commands:"
    echo ""
    echo "  # Check security policies"
    echo "  kubectl get podsecuritypolicy"
    echo "  kubectl get networkpolicy -n leanvibe-agent-hive"
    echo ""
    echo "  # Check security monitoring"
    echo "  kubectl get pods -n leanvibe-agent-hive -l app.kubernetes.io/name=security-monitoring"
    echo "  kubectl logs -f daemonset/security-monitoring-agent -n leanvibe-agent-hive"
    echo ""
    echo "  # Check secrets"
    echo "  kubectl get secrets -n leanvibe-agent-hive"
    echo "  kubectl describe secret agent-hive-secrets -n leanvibe-agent-hive"
    echo ""
    echo "  # Security assessment"
    echo "  kubectl get pods -n leanvibe-agent-hive -o custom-columns='NAME:.metadata.name,ROOT:.spec.securityContext.runAsNonRoot,READONLY:.spec.containers[*].securityContext.readOnlyRootFilesystem'"
    echo ""
    echo "  # Check certificate status"
    echo "  kubectl get certificates -n leanvibe-agent-hive"
    echo "  openssl s_client -connect your-domain.com:443 -servername your-domain.com | openssl x509 -noout -dates"
    echo ""
}

# Show security recommendations
show_security_recommendations() {
    echo ""
    log "Security Recommendations:"
    echo ""
    echo "1. 🔑 SECRET MANAGEMENT:"
    echo "   - Replace all template secrets with secure, random values"
    echo "   - Use external secret management (Vault, AWS Secrets Manager, etc.)"
    echo "   - Implement secret rotation procedures"
    echo ""
    echo "2. 🔒 ACCESS CONTROL:"
    echo "   - Enable Kubernetes RBAC audit logging"
    echo "   - Implement least privilege principle for service accounts"
    echo "   - Regular access reviews and cleanup"
    echo ""
    echo "3. 📊 MONITORING:"
    echo "   - Configure alerting for security events"
    echo "   - Set up log aggregation and analysis"
    echo "   - Regular security assessments and penetration testing"
    echo ""
    echo "4. 🛡️ NETWORK SECURITY:"
    echo "   - Review and tighten network policies"
    echo "   - Implement ingress/egress filtering"
    echo "   - Consider service mesh for additional security"
    echo ""
    echo "5. 📜 COMPLIANCE:"
    echo "   - Document security procedures"
    echo "   - Implement change management"
    echo "   - Regular compliance audits"
    echo ""
}

# Main execution
main() {
    log "Starting LeanVibe Agent Hive security deployment"
    log "Environment: $ENVIRONMENT"
    log "Deploy Policies: $DEPLOY_POLICIES"
    log "Deploy Monitoring: $DEPLOY_MONITORING"
    log "Deploy Secrets: $DEPLOY_SECRETS"
    log "Dry run: $DRY_RUN"
    
    check_prerequisites
    deploy_security_policies
    deploy_secret_management
    deploy_security_monitoring
    validate_security
    run_security_assessment
    show_security_commands
    show_security_recommendations
    
    success "Security deployment process completed!"
    
    if [[ "$DEPLOY_SECRETS" == true && "$DRY_RUN" != true ]]; then
        echo ""
        warning "🚨 CRITICAL: Secret templates have been deployed!"
        warning "You MUST update all secrets with secure values before production use!"
        warning "Use: kubectl edit secret <secret-name> -n leanvibe-agent-hive"
    fi
}

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Run main function
main