# LeanVibe Agent Hive - Kubernetes Deployment

Complete Kubernetes deployment manifests for LeanVibe Agent Hive with production-ready configuration, monitoring, and auto-scaling.

## Overview

This directory contains Kubernetes manifests organized using Kustomize for deploying LeanVibe Agent Hive across different environments (development, staging, production).

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Ingress       │    │  Load Balancer  │    │   Monitoring    │
│  (NGINX)        │    │     (HPA)       │    │  (Prometheus)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Agent Hive     │    │   PostgreSQL    │    │     Redis       │
│  (FastAPI)      │    │ (StatefulSet)   │    │ (Deployment)    │
│  3 replicas     │    │   1 replica     │    │   1 replica     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Directory Structure

```
k8s/
├── base/                           # Base Kubernetes resources
│   ├── namespace.yaml             # Namespace definition
│   ├── configmap.yaml             # Application configuration
│   ├── secret.yaml                # Secrets (passwords, keys)
│   ├── rbac.yaml                  # Service accounts and permissions
│   ├── pvc.yaml                   # Persistent volume claims
│   ├── agent-hive-deployment.yaml # Main application deployment
│   ├── agent-hive-service.yaml    # Service definitions
│   ├── postgres-statefulset.yaml  # PostgreSQL database
│   ├── redis-deployment.yaml      # Redis cache
│   ├── prometheus-deployment.yaml # Prometheus monitoring
│   ├── grafana-deployment.yaml    # Grafana dashboards
│   ├── ingress.yaml               # External access and SSL
│   ├── hpa.yaml                   # Auto-scaling configuration
│   └── kustomization.yaml         # Base kustomization
├── overlays/
│   ├── development/               # Development environment
│   │   ├── kustomization.yaml
│   │   ├── agent-hive-deployment-patch.yaml
│   │   ├── configmap-patch.yaml
│   │   ├── hpa-patch.yaml
│   │   └── service-nodeport.yaml
│   ├── staging/                   # Staging environment (future)
│   └── production/                # Production environment
│       ├── kustomization.yaml
│       ├── agent-hive-deployment-patch.yaml
│       ├── configmap-patch.yaml
│       ├── postgres-statefulset-patch.yaml
│       ├── resource-limits-patch.yaml
│       └── monitoring-service-monitor.yaml
├── deploy.sh                     # Deployment script
└── README.md                     # This file
```

## Prerequisites

1. **Kubernetes Cluster**: v1.25+
2. **kubectl**: Configured to access your cluster
3. **kustomize**: v4.0+ (usually bundled with kubectl)
4. **Docker**: For building images (unless using pre-built images)
5. **Storage Classes**: 
   - `fast-ssd` for databases and high-performance storage
   - `standard` for general purpose storage

### Optional (Recommended for Production)
- **NGINX Ingress Controller**: For external access
- **cert-manager**: For automatic SSL certificate management
- **Prometheus Operator**: For advanced monitoring

## Quick Start

### 1. Development Deployment

```bash
# Deploy to development environment
./deploy.sh -e development

# Or manually with kustomize
kubectl apply -k overlays/development/
```

### 2. Production Deployment

```bash
# Build and deploy to production
./deploy.sh -e production -t v1.0.0

# Dry run first (recommended)
./deploy.sh -e production -t v1.0.0 --dry-run
```

## Environment Configurations

### Development
- **Namespace**: `leanvibe-agent-hive-dev`
- **Replicas**: 1 for all services
- **Resources**: Minimal (128Mi memory, 100m CPU)
- **Debug**: Enabled
- **Storage**: Reduced sizes
- **Access**: NodePort for easy local access

### Production
- **Namespace**: `leanvibe-agent-hive`
- **Replicas**: 3 for Agent Hive, 1 for databases
- **Resources**: Production-sized (2Gi memory, 2000m CPU)
- **Debug**: Disabled
- **Storage**: Full production sizes
- **Access**: Ingress with SSL termination
- **Monitoring**: Full observability stack

## Resource Requirements

### Minimum Cluster Requirements
- **CPU**: 4 cores
- **Memory**: 8GB RAM
- **Storage**: 200GB available

### Production Recommendations
- **CPU**: 16+ cores
- **Memory**: 32GB+ RAM
- **Storage**: 1TB+ SSD
- **Nodes**: 3+ for high availability

## Configuration

### Secrets Management

Before deploying to production, update the secrets in `base/secret.yaml`:

```bash
# Generate base64 encoded values
echo -n "your_production_password" | base64
echo -n "your_jwt_secret" | base64
echo -n "your_api_key" | base64
```

Replace the placeholder values in `secret.yaml` with your actual secrets.

### Domain Configuration

Update the Ingress configuration in `base/ingress.yaml`:

```yaml
spec:
  tls:
  - hosts:
    - your-domain.com
    - api.your-domain.com
    - monitoring.your-domain.com
```

### Storage Classes

Ensure your cluster has the required storage classes:

```bash
# Check available storage classes
kubectl get storageclass

# Create if needed (example for local development)
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
EOF
```

## Deployment Script Usage

The `deploy.sh` script provides a convenient way to deploy to different environments:

```bash
# Basic usage
./deploy.sh -e development               # Deploy to development
./deploy.sh -e production -t v1.0.0     # Deploy tagged version to production

# Advanced options
./deploy.sh -e staging -d               # Dry run for staging
./deploy.sh -e production -v            # Verbose output
./deploy.sh -e development -s           # Skip Docker build
./deploy.sh -h                          # Show help
```

## Monitoring and Observability

### Prometheus Metrics
- **Endpoint**: `http://prometheus-service:9090`
- **Targets**: Agent Hive, PostgreSQL, Redis
- **Retention**: 15 days

### Grafana Dashboards
- **Endpoint**: `http://grafana-service:3000`
- **Default Credentials**: admin/admin (change in production)
- **Dashboards**: Pre-configured for Agent Hive overview

### Jaeger Tracing
- **Endpoint**: `http://jaeger-service:16686`
- **Features**: Distributed tracing for request flows

## Auto-scaling

### Horizontal Pod Autoscaler (HPA)
- **Metrics**: CPU (70%), Memory (80%), HTTP requests
- **Development**: 1-3 replicas
- **Production**: 2-10 replicas
- **Scale-up**: Aggressive (100% in 15s)
- **Scale-down**: Conservative (10% in 5min)

### Vertical Pod Autoscaler (VPA)
Not currently configured but can be added for automatic resource adjustment.

## Security

### Pod Security
- **Non-root containers**: All containers run as non-root
- **Read-only filesystem**: Where possible
- **Security contexts**: Restrictive security contexts applied
- **Network policies**: Traffic isolation between services

### RBAC
- **Service accounts**: Dedicated service accounts per component
- **Roles**: Minimal required permissions
- **Cluster roles**: Only for Prometheus monitoring

### Secrets
- **Kubernetes secrets**: Encrypted at rest
- **Secret rotation**: Manual (automated rotation can be added)
- **Access control**: Limited to necessary pods only

## Troubleshooting

### Common Issues

1. **Pods stuck in Pending**
   ```bash
   kubectl describe pod <pod-name> -n <namespace>
   # Check for resource constraints or storage issues
   ```

2. **Application not accessible**
   ```bash
   kubectl get ingress -n <namespace>
   kubectl describe ingress <ingress-name> -n <namespace>
   # Check ingress controller and DNS
   ```

3. **Database connection issues**
   ```bash
   kubectl logs deployment/agent-hive -n <namespace>
   kubectl exec -it postgres-0 -n <namespace> -- psql -U postgres
   ```

### Debugging Commands

```bash
# Check pod status
kubectl get pods -n leanvibe-agent-hive

# View logs
kubectl logs -f deployment/agent-hive -n leanvibe-agent-hive

# Access container shell
kubectl exec -it deployment/agent-hive -n leanvibe-agent-hive -- /bin/bash

# Port forward for local access
kubectl port-forward service/agent-hive-service 8000:8000 -n leanvibe-agent-hive

# Check resource usage
kubectl top pods -n leanvibe-agent-hive
kubectl top nodes
```

## Backup and Disaster Recovery

### Database Backup
```bash
# Manual backup
kubectl exec postgres-0 -n leanvibe-agent-hive -- pg_dump -U postgres agent_hive > backup.sql

# Restore
kubectl exec -i postgres-0 -n leanvibe-agent-hive -- psql -U postgres agent_hive < backup.sql
```

### Persistent Volume Backup
Consider using Velero or your cloud provider's volume snapshot features.

## Updates and Rollbacks

### Rolling Updates
```bash
# Update image
kubectl set image deployment/agent-hive agent-hive=leanvibe-agent-hive:v1.1.0 -n leanvibe-agent-hive

# Check rollout status
kubectl rollout status deployment/agent-hive -n leanvibe-agent-hive
```

### Rollbacks
```bash
# View rollout history
kubectl rollout history deployment/agent-hive -n leanvibe-agent-hive

# Rollback to previous version
kubectl rollout undo deployment/agent-hive -n leanvibe-agent-hive

# Rollback to specific revision
kubectl rollout undo deployment/agent-hive --to-revision=2 -n leanvibe-agent-hive
```

## Performance Tuning

### Resource Optimization
- Monitor resource usage with Prometheus
- Adjust HPA thresholds based on traffic patterns
- Use resource quotas to prevent resource exhaustion

### Database Tuning
- PostgreSQL configuration optimized for Kubernetes
- Connection pooling enabled
- Query optimization monitoring

### Network Optimization
- Service mesh (Istio) can be added for advanced traffic management
- Network policies for security and performance isolation

## Future Enhancements

1. **GitOps Integration**: ArgoCD for automated deployments
2. **Service Mesh**: Istio for advanced traffic management
3. **Chaos Engineering**: Chaos Monkey for resilience testing
4. **Advanced Monitoring**: Loki for log aggregation
5. **Automated Backups**: Velero for complete cluster backups
6. **Multi-region Deployment**: Cross-region disaster recovery

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review logs using the debugging commands
3. Consult the main LeanVibe Agent Hive documentation
4. Create GitHub issues for bugs or feature requests