#!/bin/bash
# LeanVibe Agent Hive - Ingress and Load Balancer Deployment Script
# Deploys NGINX Ingress Controller, cert-manager, and load balancer configurations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="production"
DOMAIN="yourdomain.com"
EMAIL="admin@yourdomain.com"
CLOUDFLARE_TOKEN=""
DRY_RUN=false
VERBOSE=false
SKIP_CERT_MANAGER=false
SKIP_INGRESS_CONTROLLER=false

# Functions
print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Deploy LeanVibe Agent Hive Ingress and Load Balancer"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV      Target environment (development|staging|production) [default: production]"
    echo "  -d, --domain DOMAIN        Base domain name [default: yourdomain.com]"
    echo "  --email EMAIL              Email for Let's Encrypt [default: admin@yourdomain.com]"
    echo "  --cloudflare-token TOKEN   Cloudflare API token for DNS challenges"
    echo "  --dry-run                  Show what would be deployed without applying"
    echo "  -v, --verbose              Enable verbose output"
    echo "  --skip-cert-manager        Skip cert-manager deployment"
    echo "  --skip-ingress             Skip ingress controller deployment"
    echo "  -h, --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -e production -d agent-hive.com --email admin@agent-hive.com"
    echo "  $0 -e development --dry-run"
    echo "  $0 --cloudflare-token YOUR_TOKEN -d yourdomain.com"
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
        -d|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        --email)
            EMAIL="$2"
            shift 2
            ;;
        --cloudflare-token)
            CLOUDFLARE_TOKEN="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --skip-cert-manager)
            SKIP_CERT_MANAGER=true
            shift
            ;;
        --skip-ingress)
            SKIP_INGRESS_CONTROLLER=true
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
    
    # Check if running as cluster admin (for CRDs)
    if ! kubectl auth can-i create customresourcedefinitions &> /dev/null; then
        warning "May not have permissions to create CustomResourceDefinitions"
    fi
    
    success "Prerequisites check passed"
}

# Deploy NGINX Ingress Controller
deploy_ingress_controller() {
    if [[ "$SKIP_INGRESS_CONTROLLER" == true ]]; then
        log "Skipping NGINX Ingress Controller deployment"
        return
    fi
    
    log "Deploying NGINX Ingress Controller..."
    
    local ingress_file="controllers/nginx-ingress-controller.yaml"
    
    if [[ "$DRY_RUN" == true ]]; then
        log "Dry run - would deploy NGINX Ingress Controller"
        kubectl apply --dry-run=client -f "$ingress_file"
    else
        kubectl apply -f "$ingress_file"
        
        # Wait for ingress controller to be ready
        log "Waiting for NGINX Ingress Controller to be ready..."
        kubectl wait --namespace ingress-nginx \
            --for=condition=ready pod \
            --selector=app.kubernetes.io/component=controller \
            --timeout=300s || warning "Ingress controller readiness check timed out"
    fi
    
    success "NGINX Ingress Controller deployment completed"
}

# Deploy cert-manager
deploy_cert_manager() {
    if [[ "$SKIP_CERT_MANAGER" == true ]]; then
        log "Skipping cert-manager deployment"
        return
    fi
    
    log "Deploying cert-manager..."
    
    # Create temporary cert-manager file with domain substitution
    local cert_manager_file="/tmp/cert-manager-${ENVIRONMENT}.yaml"
    sed "s/yourdomain.com/${DOMAIN}/g; s/admin@yourdomain.com/${EMAIL}/g" \
        configs/cert-manager.yaml > "$cert_manager_file"
    
    # Add Cloudflare token if provided
    if [[ -n "$CLOUDFLARE_TOKEN" ]]; then
        sed -i "s/YOUR_CLOUDFLARE_API_TOKEN/${CLOUDFLARE_TOKEN}/g" "$cert_manager_file"
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        log "Dry run - would deploy cert-manager"
        kubectl apply --dry-run=client -f "$cert_manager_file"
    else
        # Deploy cert-manager CRDs and controller
        kubectl apply -f "$cert_manager_file"
        
        # Wait for cert-manager to be ready
        log "Waiting for cert-manager to be ready..."
        kubectl wait --namespace cert-manager \
            --for=condition=ready pod \
            --selector=app.kubernetes.io/name=cert-manager \
            --timeout=300s || warning "cert-manager readiness check timed out"
    fi
    
    # Cleanup temp file
    rm -f "$cert_manager_file"
    
    success "cert-manager deployment completed"
}

# Deploy load balancer configuration
deploy_load_balancer() {
    log "Deploying load balancer configuration..."
    
    local lb_config_file="configs/load-balancer-config.yaml"
    
    if [[ "$DRY_RUN" == true ]]; then
        log "Dry run - would deploy load balancer configuration"
        kubectl apply --dry-run=client -f "$lb_config_file"
    else
        kubectl apply -f "$lb_config_file"
        
        # Wait for load balancer to be ready
        log "Waiting for load balancer to be ready..."
        kubectl wait --namespace leanvibe-agent-hive \
            --for=condition=ready pod \
            --selector=app.kubernetes.io/name=nginx-load-balancer \
            --timeout=180s || warning "Load balancer readiness check timed out"
    fi
    
    success "Load balancer configuration deployment completed"
}

# Deploy ingress routes
deploy_ingress_routes() {
    log "Deploying ingress routes..."
    
    # Create temporary ingress routes file with domain substitution
    local ingress_routes_file="/tmp/ingress-routes-${ENVIRONMENT}.yaml"
    sed "s/yourdomain.com/${DOMAIN}/g; s/admin@yourdomain.com/${EMAIL}/g" \
        configs/ingress-routes.yaml > "$ingress_routes_file"
    
    if [[ "$DRY_RUN" == true ]]; then
        log "Dry run - would deploy ingress routes"
        kubectl apply --dry-run=client -f "$ingress_routes_file"
    else
        kubectl apply -f "$ingress_routes_file"
    fi
    
    # Cleanup temp file
    rm -f "$ingress_routes_file"
    
    success "Ingress routes deployment completed"
}

# Verify deployment
verify_deployment() {
    if [[ "$DRY_RUN" == true ]]; then
        return
    fi
    
    log "Verifying deployment..."
    
    # Check ingress controller
    if [[ "$SKIP_INGRESS_CONTROLLER" != true ]]; then
        local ingress_ready=$(kubectl get pods -n ingress-nginx -l app.kubernetes.io/component=controller -o jsonpath='{.items[*].status.phase}' | grep -o Running | wc -l)
        if [[ "$ingress_ready" -gt 0 ]]; then
            success "NGINX Ingress Controller is running"
        else
            warning "NGINX Ingress Controller may not be ready"
        fi
    fi
    
    # Check cert-manager
    if [[ "$SKIP_CERT_MANAGER" != true ]]; then
        local cert_manager_ready=$(kubectl get pods -n cert-manager -l app.kubernetes.io/name=cert-manager -o jsonpath='{.items[*].status.phase}' | grep -o Running | wc -l)
        if [[ "$cert_manager_ready" -gt 0 ]]; then
            success "cert-manager is running"
        else
            warning "cert-manager may not be ready"
        fi
    fi
    
    # Check load balancer
    local lb_ready=$(kubectl get pods -n leanvibe-agent-hive -l app.kubernetes.io/name=nginx-load-balancer -o jsonpath='{.items[*].status.phase}' | grep -o Running | wc -l)
    if [[ "$lb_ready" -gt 0 ]]; then
        success "Load balancer is running"
    else
        warning "Load balancer may not be ready"
    fi
    
    # Check ingress resources
    local ingress_count=$(kubectl get ingress -n leanvibe-agent-hive -o name | wc -l)
    if [[ "$ingress_count" -gt 0 ]]; then
        success "Ingress routes are configured ($ingress_count ingress resources)"
    else
        warning "No ingress routes found"
    fi
    
    # Get external IP (if available)
    local external_ip=$(kubectl get service -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    if [[ "$external_ip" != "pending" && -n "$external_ip" ]]; then
        log "External IP: $external_ip"
        log "You can now point your DNS records to this IP"
    else
        log "External IP is still pending - check your cloud provider's load balancer"
    fi
}

# Show useful commands
show_useful_commands() {
    echo ""
    log "Useful commands for managing ingress:"
    echo ""
    echo "  # Check ingress controller status"
    echo "  kubectl get pods -n ingress-nginx"
    echo ""
    echo "  # Check cert-manager status"
    echo "  kubectl get pods -n cert-manager"
    echo ""
    echo "  # Check certificates"
    echo "  kubectl get certificates -n leanvibe-agent-hive"
    echo "  kubectl describe certificate agent-hive-wildcard-cert -n leanvibe-agent-hive"
    echo ""
    echo "  # Check ingress resources"
    echo "  kubectl get ingress -n leanvibe-agent-hive"
    echo "  kubectl describe ingress agent-hive-main-ingress -n leanvibe-agent-hive"
    echo ""
    echo "  # Check load balancer"
    echo "  kubectl get pods -n leanvibe-agent-hive -l app.kubernetes.io/name=nginx-load-balancer"
    echo "  kubectl logs -f deployment/nginx-load-balancer -n leanvibe-agent-hive"
    echo ""
    echo "  # Get external IP"
    echo "  kubectl get service -n ingress-nginx ingress-nginx-controller"
    echo ""
    echo "  # Test endpoints (replace with your domain)"
    echo "  curl -H \"Host: agent-hive.${DOMAIN}\" http://\$EXTERNAL_IP/health"
    echo ""
}

# Main execution
main() {
    log "Starting LeanVibe Agent Hive ingress deployment"
    log "Environment: $ENVIRONMENT"
    log "Domain: $DOMAIN"
    log "Email: $EMAIL"
    log "Dry run: $DRY_RUN"
    
    check_prerequisites
    deploy_ingress_controller
    deploy_cert_manager
    deploy_load_balancer
    deploy_ingress_routes
    verify_deployment
    show_useful_commands
    
    success "Ingress deployment process completed!"
    
    if [[ "$DRY_RUN" != true ]]; then
        log "Next steps:"
        log "1. Point your DNS records to the external IP shown above"
        log "2. Wait for Let's Encrypt certificates to be issued (may take a few minutes)"
        log "3. Test your endpoints using the commands shown above"
    fi
}

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Run main function
main