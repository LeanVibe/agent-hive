#!/bin/bash
# LeanVibe Agent Hive Kubernetes Deployment Script
# Supports development, staging, and production environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="development"
NAMESPACE=""
DRY_RUN=false
VERBOSE=false
SKIP_BUILD=false
IMAGE_TAG="latest"

# Functions
print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Deploy LeanVibe Agent Hive to Kubernetes"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV    Target environment (development|staging|production) [default: development]"
    echo "  -n, --namespace NS       Kubernetes namespace [default: auto-detected from environment]"
    echo "  -t, --tag TAG           Docker image tag [default: latest]"
    echo "  -d, --dry-run           Show what would be deployed without applying"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -s, --skip-build        Skip Docker image build"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -e development                    # Deploy to development"
    echo "  $0 -e production -t v1.0.0          # Deploy tagged version to production"
    echo "  $0 -e staging -d                    # Dry run for staging"
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
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -s|--skip-build)
            SKIP_BUILD=true
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

# Set namespace if not provided
if [[ -z "$NAMESPACE" ]]; then
    case $ENVIRONMENT in
        development)
            NAMESPACE="leanvibe-agent-hive-dev"
            ;;
        staging)
            NAMESPACE="leanvibe-agent-hive-staging"
            ;;
        production)
            NAMESPACE="leanvibe-agent-hive"
            ;;
    esac
fi

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is required but not installed"
    fi
    
    # Check kustomize
    if ! command -v kustomize &> /dev/null; then
        error "kustomize is required but not installed"
    fi
    
    # Check docker (if not skipping build)
    if [[ "$SKIP_BUILD" != true ]] && ! command -v docker &> /dev/null; then
        error "docker is required but not installed"
    fi
    
    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
    fi
    
    success "Prerequisites check passed"
}

# Build Docker image
build_image() {
    if [[ "$SKIP_BUILD" == true ]]; then
        log "Skipping Docker image build"
        return
    fi
    
    log "Building Docker image..."
    
    local dockerfile_target="production"
    if [[ "$ENVIRONMENT" == "development" ]]; then
        dockerfile_target="dev-server"
    fi
    
    docker build --target "$dockerfile_target" -t "leanvibe-agent-hive:$IMAGE_TAG" ../..
    
    if [[ "$ENVIRONMENT" != "development" ]]; then
        docker tag "leanvibe-agent-hive:$IMAGE_TAG" "leanvibe-agent-hive:latest"
    fi
    
    success "Docker image built successfully"
}

# Deploy to Kubernetes
deploy() {
    log "Deploying to $ENVIRONMENT environment (namespace: $NAMESPACE)..."
    
    local overlay_path="overlays/$ENVIRONMENT"
    if [[ ! -d "$overlay_path" ]]; then
        error "Environment overlay not found: $overlay_path"
    fi
    
    # Build kustomization
    local kustomize_cmd="kustomize build $overlay_path"
    if [[ "$VERBOSE" == true ]]; then
        log "Running: $kustomize_cmd"
    fi
    
    # Apply or show what would be applied
    if [[ "$DRY_RUN" == true ]]; then
        log "Dry run - showing what would be deployed:"
        eval "$kustomize_cmd"
    else
        log "Applying Kubernetes manifests..."
        eval "$kustomize_cmd" | kubectl apply -f -
        
        # Wait for deployment to be ready
        log "Waiting for deployment to be ready..."
        kubectl wait --for=condition=available --timeout=300s \
            deployment/agent-hive -n "$NAMESPACE" || warning "Deployment readiness check timed out"
        
        # Show deployment status
        kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=leanvibe-agent-hive
        
        success "Deployment completed successfully"
    fi
}

# Verify deployment
verify_deployment() {
    if [[ "$DRY_RUN" == true ]]; then
        return
    fi
    
    log "Verifying deployment..."
    
    # Check pod status
    local pods=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=leanvibe-agent-hive -o jsonpath='{.items[*].status.phase}')
    if [[ "$pods" =~ "Running" ]]; then
        success "Pods are running"
    else
        warning "Some pods may not be running yet"
    fi
    
    # Check service endpoints
    if kubectl get service -n "$NAMESPACE" agent-hive-service &> /dev/null; then
        local service_ip=$(kubectl get service -n "$NAMESPACE" agent-hive-service -o jsonpath='{.spec.clusterIP}')
        log "Service available at: $service_ip:8000"
    fi
    
    # Show useful commands
    echo ""
    log "Useful commands:"
    echo "  kubectl get pods -n $NAMESPACE"
    echo "  kubectl logs -f deployment/agent-hive -n $NAMESPACE"
    echo "  kubectl describe deployment agent-hive -n $NAMESPACE"
    echo "  kubectl port-forward service/agent-hive-service 8000:8000 -n $NAMESPACE"
}

# Main execution
main() {
    log "Starting LeanVibe Agent Hive deployment"
    log "Environment: $ENVIRONMENT"
    log "Namespace: $NAMESPACE"
    log "Image tag: $IMAGE_TAG"
    log "Dry run: $DRY_RUN"
    
    check_prerequisites
    build_image
    deploy
    verify_deployment
    
    success "Deployment process completed!"
}

# Run main function
main