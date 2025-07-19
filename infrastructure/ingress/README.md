# LeanVibe Agent Hive - Ingress and Load Balancer

Production-ready ingress controller, load balancer, and SSL certificate management for LeanVibe Agent Hive with high availability, security, and performance optimization.

## Overview

This directory contains comprehensive ingress and load balancing configurations:
- **NGINX Ingress Controller**: Production-grade ingress with advanced features
- **cert-manager**: Automatic SSL certificate management with Let's Encrypt
- **Load Balancer**: Internal NGINX load balancer for advanced routing
- **Security**: Rate limiting, CORS, security headers, and access control

## Architecture

```
Internet
    │
    ▼
┌─────────────────┐
│ Cloud Load      │  ← External Load Balancer (AWS ALB/GCP LB/Azure LB)
│ Balancer        │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ NGINX Ingress   │  ← Kubernetes Ingress Controller
│ Controller      │    • SSL Termination
└─────────────────┘    • Rate Limiting
    │                  • Security Headers
    ▼
┌─────────────────┐
│ Internal Load   │  ← Internal NGINX Load Balancer
│ Balancer        │    • Advanced Routing
└─────────────────┘    • Session Affinity
    │                  • Health Checks
    ▼
┌─────────────────┐
│ Agent Hive      │  ← Application Pods
│ Services        │    • API (8000)
└─────────────────┘    • Webhook (8080)
                      • Gateway (8081)
```

## Directory Structure

```
infrastructure/ingress/
├── controllers/
│   └── nginx-ingress-controller.yaml      # NGINX Ingress Controller
├── configs/
│   ├── load-balancer-config.yaml         # Internal load balancer
│   ├── ingress-routes.yaml               # Ingress routing rules
│   └── cert-manager.yaml                 # SSL certificate management
├── certificates/                         # SSL certificates (auto-managed)
├── deploy-ingress.sh                     # Deployment script
└── README.md                             # This file
```

## Quick Start

### 1. Deploy Complete Ingress Stack

```bash
# Deploy to production with your domain
./deploy-ingress.sh -e production -d yourdomain.com --email admin@yourdomain.com

# Deploy with Cloudflare DNS for wildcard certificates
./deploy-ingress.sh -d yourdomain.com --cloudflare-token YOUR_API_TOKEN

# Dry run to see what would be deployed
./deploy-ingress.sh --dry-run
```

### 2. Configure DNS

Point your DNS records to the external IP:

```bash
# Get external IP
kubectl get service -n ingress-nginx ingress-nginx-controller

# Configure DNS records
agent-hive.yourdomain.com      → EXTERNAL_IP
api.agent-hive.yourdomain.com  → EXTERNAL_IP
webhook.agent-hive.yourdomain.com → EXTERNAL_IP
monitoring.agent-hive.yourdomain.com → EXTERNAL_IP
```

### 3. Verify Deployment

```bash
# Check all components
kubectl get pods -n ingress-nginx
kubectl get pods -n cert-manager
kubectl get pods -n leanvibe-agent-hive

# Check certificates
kubectl get certificates -n leanvibe-agent-hive

# Test endpoints
curl https://agent-hive.yourdomain.com/health
```

## Components

### NGINX Ingress Controller

**Features:**
- Production-grade ingress with high performance
- SSL termination with TLS 1.2/1.3
- Rate limiting and DDoS protection
- Security headers and CORS configuration
- Session affinity and load balancing
- Metrics and monitoring integration

**Configuration Highlights:**
- `16384` max worker connections
- `64MB` max request body size
- `100 req/s` default rate limit
- Gzip compression enabled
- Security headers enforced

### cert-manager

**Features:**
- Automatic SSL certificate provisioning
- Let's Encrypt integration (staging and production)
- Wildcard certificate support via DNS challenge
- Certificate renewal automation
- Multi-domain support

**Certificate Types:**
- **HTTP Challenge**: For basic domain validation
- **DNS Challenge**: For wildcard certificates (Cloudflare)
- **Wildcard Support**: `*.agent-hive.yourdomain.com`

### Internal Load Balancer

**Features:**
- Advanced routing algorithms (least_conn, ip_hash, round_robin)
- Health checks and automatic failover
- Session affinity for webhooks
- Connection pooling and keepalive
- Request/response logging
- Upstream backup servers

**Load Balancing Strategies:**
- **API Endpoints**: `least_conn` for optimal distribution
- **Webhooks**: `ip_hash` for session affinity
- **Gateway**: `round_robin` for balanced load

### Security Features

**Rate Limiting:**
- API: 100 requests/second with 20 burst
- Webhooks: 20 requests/second with 10 burst
- Authentication: 2 requests/second with 5 burst

**Security Headers:**
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` with HSTS
- `Content-Security-Policy` for XSS protection

**Access Control:**
- Monitoring endpoints require basic auth
- Metrics endpoints restricted to internal networks
- Health checks publicly accessible
- Static assets cached with long expiry

## Configuration

### Environment-Specific Settings

#### Development
```bash
./deploy-ingress.sh -e development -d dev.yourdomain.com
```
- Self-signed certificates
- Relaxed rate limiting
- Debug headers enabled
- NodePort services for local access

#### Production
```bash
./deploy-ingress.sh -e production -d yourdomain.com --email admin@yourdomain.com
```
- Let's Encrypt certificates
- Strict security policies
- Performance optimization
- Full monitoring enabled

### Custom Domain Configuration

Update domain references in configuration files:

```bash
# Replace yourdomain.com with your actual domain
find configs/ -name "*.yaml" -exec sed -i 's/yourdomain.com/yourcompany.com/g' {} \;
```

### SSL Certificate Configuration

#### HTTP Challenge (Recommended for single domains)
```yaml
spec:
  acme:
    solvers:
    - http01:
        ingress:
          class: nginx
```

#### DNS Challenge (Required for wildcards)
```yaml
spec:
  acme:
    solvers:
    - dns01:
        cloudflare:
          email: admin@yourdomain.com
          apiTokenSecretRef:
            name: cloudflare-api-token-secret
            key: api-token
```

### Load Balancer Customization

#### Upstream Configuration
```nginx
upstream agent_hive_api {
    least_conn;
    server agent-hive-service:8000 max_fails=3 fail_timeout=30s weight=10;
    server agent-hive-service:8000 max_fails=3 fail_timeout=30s weight=10;
    keepalive 32;
}
```

#### Rate Limiting
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req zone=api burst=20 nodelay;
```

## Monitoring and Observability

### Metrics Collection

**NGINX Ingress Controller Metrics:**
- Request rate and latency
- Error rates by status code
- Upstream response times
- SSL certificate expiry

**cert-manager Metrics:**
- Certificate issuance success/failure
- Certificate expiry dates
- ACME challenge success rates

### Logging

**Access Logs:**
- Request details with timing
- Upstream server information
- Cache status and performance
- Security events and blocks

**Error Logs:**
- SSL handshake failures
- Upstream connection errors
- Rate limiting events
- Security violations

### Health Checks

```bash
# Ingress controller health
kubectl get pods -n ingress-nginx
curl http://EXTERNAL_IP/healthz

# cert-manager health
kubectl get pods -n cert-manager
kubectl describe certificate -n leanvibe-agent-hive

# Load balancer health
curl http://INTERNAL_LB_IP:8080/health
```

## Troubleshooting

### Common Issues

#### 1. Certificate Not Issued
```bash
# Check certificate status
kubectl describe certificate agent-hive-wildcard-cert -n leanvibe-agent-hive

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Verify DNS records for DNS challenge
dig _acme-challenge.yourdomain.com TXT
```

#### 2. Ingress Not Accessible
```bash
# Check ingress controller
kubectl get pods -n ingress-nginx
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller

# Check ingress resources
kubectl get ingress -n leanvibe-agent-hive
kubectl describe ingress agent-hive-main-ingress -n leanvibe-agent-hive

# Verify external IP
kubectl get service -n ingress-nginx ingress-nginx-controller
```

#### 3. Load Balancer Issues
```bash
# Check internal load balancer
kubectl get pods -n leanvibe-agent-hive -l app.kubernetes.io/name=nginx-load-balancer
kubectl logs -f deployment/nginx-load-balancer -n leanvibe-agent-hive

# Test internal connectivity
kubectl exec -it deployment/nginx-load-balancer -n leanvibe-agent-hive -- curl http://agent-hive-service:8000/health
```

#### 4. Rate Limiting Problems
```bash
# Check rate limit configuration
kubectl get configmap ingress-nginx-controller -n ingress-nginx -o yaml

# Monitor rate limiting
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller | grep "limiting requests"
```

### Debugging Commands

```bash
# Test specific endpoints
curl -H "Host: agent-hive.yourdomain.com" http://EXTERNAL_IP/health
curl -H "Host: api.agent-hive.yourdomain.com" http://EXTERNAL_IP/api/status

# Check SSL certificates
openssl s_client -connect agent-hive.yourdomain.com:443 -servername agent-hive.yourdomain.com

# View ingress controller configuration
kubectl exec -n ingress-nginx deployment/ingress-nginx-controller -- cat /etc/nginx/nginx.conf

# Monitor real-time logs
kubectl logs -f -n ingress-nginx deployment/ingress-nginx-controller
kubectl logs -f -n leanvibe-agent-hive deployment/nginx-load-balancer
```

## Performance Optimization

### Resource Allocation

```yaml
# Ingress controller resources
resources:
  requests:
    cpu: 100m
    memory: 90Mi
  limits:
    cpu: 1000m
    memory: 1Gi

# Load balancer resources
resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 200m
    memory: 256Mi
```

### Connection Optimization

```nginx
# Upstream keepalive
keepalive 32;
keepalive_requests 100;
keepalive_timeout 60s;

# Worker configuration
worker_processes auto;
worker_connections 4096;
```

### Caching Strategy

```nginx
# Static assets
location /static/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# API responses (if cacheable)
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m;
```

## Security Hardening

### Network Policies

```yaml
# Restrict ingress controller access
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ingress-network-policy
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: ingress-nginx
  policyTypes:
  - Ingress
  - Egress
```

### Secret Management

```bash
# Rotate TLS certificates
kubectl delete secret agent-hive-wildcard-tls -n leanvibe-agent-hive
# cert-manager will automatically recreate

# Update Cloudflare API token
kubectl create secret generic cloudflare-api-token-secret \
  --from-literal=api-token=NEW_TOKEN \
  -n cert-manager --dry-run=client -o yaml | kubectl apply -f -
```

### Audit Logging

Enable audit logging for security events:

```yaml
# In ingress controller configuration
enable-access-log-for-default-backend: "true"
access-log-params: "buffer=16k flush=5s"
```

## Backup and Disaster Recovery

### Certificate Backup

```bash
# Backup certificates
kubectl get secret -n leanvibe-agent-hive agent-hive-wildcard-tls -o yaml > cert-backup.yaml

# Backup cert-manager configuration
kubectl get clusterissuer -o yaml > cluster-issuers-backup.yaml
```

### Configuration Backup

```bash
# Backup ingress configurations
kubectl get ingress -n leanvibe-agent-hive -o yaml > ingress-backup.yaml
kubectl get configmap -n ingress-nginx -o yaml > ingress-config-backup.yaml
```

### Recovery Procedures

```bash
# Restore certificates
kubectl apply -f cert-backup.yaml

# Restore configurations
kubectl apply -f ingress-backup.yaml
kubectl apply -f ingress-config-backup.yaml

# Force certificate renewal
kubectl annotate certificate agent-hive-wildcard-cert -n leanvibe-agent-hive cert-manager.io/force-renew=$(date +%s)
```

## Advanced Features

### Custom Error Pages

```nginx
# Custom 404/50x pages
error_page 404 /custom_404.html;
error_page 500 502 503 504 /custom_50x.html;

location = /custom_404.html {
    return 404 '{"error": "Not Found"}';
    add_header Content-Type application/json;
}
```

### Geographic Load Balancing

```yaml
# GeoDNS with multiple regions
metadata:
  annotations:
    external-dns.alpha.kubernetes.io/hostname: agent-hive.yourdomain.com
    external-dns.alpha.kubernetes.io/set-identifier: us-west
    external-dns.alpha.kubernetes.io/aws-geolocation-location: "US-CA"
```

### A/B Testing Support

```nginx
# Split traffic based on headers
map $http_x_version $upstream_pool {
    "beta" agent_hive_beta;
    default agent_hive_stable;
}
```

## Future Enhancements

1. **Service Mesh Integration**: Istio/Linkerd for advanced traffic management
2. **WAF Integration**: Web Application Firewall for enhanced security
3. **CDN Integration**: CloudFlare/CloudFront for global content delivery
4. **Advanced Monitoring**: Distributed tracing and APM integration
5. **Automated Scaling**: HPA based on ingress metrics
6. **Multi-cloud Support**: Cross-cloud load balancing and failover

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review logs using the debugging commands
3. Consult Kubernetes ingress controller documentation
4. Create GitHub issues for bugs or feature requests