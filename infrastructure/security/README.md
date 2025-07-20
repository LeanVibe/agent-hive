# LeanVibe Agent Hive - Security Infrastructure

Comprehensive security implementation including SSL/TLS certificate management, pod security policies, network isolation, secret management, and security monitoring for production-ready deployment.

## Overview

This security infrastructure provides:
- **SSL/TLS Certificate Management**: Automated certificate provisioning and renewal
- **Pod Security Standards**: Restrictive security policies and controls
- **Network Security**: Network policies for traffic isolation
- **Secret Management**: Secure handling of sensitive data
- **Security Monitoring**: Real-time threat detection and alerting
- **Access Control**: RBAC and principle of least privilege

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                         │
├─────────────────────────────────────────────────────────────┤
│ 🔒 Network Security                                        │
│   • Network Policies (Default Deny)                       │
│   • Ingress/Egress Filtering                             │
│   • Service Mesh Ready                                    │
├─────────────────────────────────────────────────────────────┤
│ 🛡️ Pod Security                                           │
│   • Pod Security Standards (Restricted)                   │
│   • Security Contexts (Non-root, Read-only FS)           │
│   • Capability Dropping (ALL)                            │
├─────────────────────────────────────────────────────────────┤
│ 🔑 Secret Management                                       │
│   • Kubernetes Secrets (Encrypted at Rest)               │
│   • Secret Rotation Automation                           │
│   • External Secret Integration Ready                     │
├─────────────────────────────────────────────────────────────┤
│ 📊 Security Monitoring                                     │
│   • Falco Runtime Security                               │
│   • Prometheus Security Metrics                          │
│   • Audit Logging and Alerting                          │
├─────────────────────────────────────────────────────────────┤
│ 🌐 TLS/SSL Security                                       │
│   • cert-manager Automation                              │
│   • Let's Encrypt Integration                            │
│   • TLS 1.2/1.3 Enforcement                             │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
infrastructure/security/
├── policies/
│   ├── pod-security-standards.yaml       # Pod Security Policies
│   └── network-policies.yaml             # Network isolation rules
├── secrets/
│   └── secret-management.yaml            # Secret templates and rotation
├── monitoring/
│   └── security-monitoring.yaml          # Falco and security alerts
├── rbac/                                 # (Additional RBAC configs)
├── deploy-security.sh                   # Security deployment script
└── README.md                            # This file
```

## Quick Start

### 1. Deploy Complete Security Stack

```bash
# Deploy all security components
./deploy-security.sh -e production

# Deploy with secret templates (requires manual configuration)
./deploy-security.sh --deploy-secrets

# Dry run to see what would be deployed
./deploy-security.sh --dry-run
```

### 2. Update Secret Templates

⚠️ **CRITICAL**: If you deployed secrets, update them immediately:

```bash
# List deployed secrets
kubectl get secrets -n leanvibe-agent-hive

# Update each secret with secure values
kubectl edit secret agent-hive-secrets -n leanvibe-agent-hive
kubectl edit secret grafana-admin-credentials -n leanvibe-agent-hive
```

### 3. Verify Security Deployment

```bash
# Check security policies
kubectl get podsecuritypolicy
kubectl get networkpolicy -n leanvibe-agent-hive

# Check security monitoring
kubectl get pods -n leanvibe-agent-hive -l app.kubernetes.io/name=security-monitoring

# Run security assessment
kubectl get pods -n leanvibe-agent-hive -o custom-columns='NAME:.metadata.name,ROOT:.spec.securityContext.runAsNonRoot'
```

## Security Components

### Pod Security Standards

**Implementation**: Kubernetes Pod Security Standards at `restricted` level

**Enforced Controls:**
- **Non-root execution**: All containers run as non-root users
- **Read-only root filesystem**: Prevents runtime modifications
- **Capability dropping**: Removes ALL Linux capabilities
- **Privilege escalation**: Prevented at container level
- **Host access**: No host network, PID, or IPC access

```yaml
# Pod Security Labels
labels:
  pod-security.kubernetes.io/enforce: restricted
  pod-security.kubernetes.io/audit: restricted
  pod-security.kubernetes.io/warn: restricted
```

### Network Security

**Default Deny Policy**: All traffic blocked by default, explicit allow rules required

**Network Policies:**
- **Application Isolation**: Agent Hive pods can only communicate with authorized services
- **Database Protection**: PostgreSQL/Redis only accessible from application pods
- **Monitoring Access**: Prometheus can scrape metrics from authorized endpoints
- **Ingress Control**: External traffic only through NGINX Ingress Controller

```bash
# Check network policies
kubectl get networkpolicy -n leanvibe-agent-hive
kubectl describe networkpolicy agent-hive-app-policy -n leanvibe-agent-hive
```

### SSL/TLS Certificate Management

**Automated Certificate Management**: cert-manager with Let's Encrypt integration

**Features:**
- **Automatic Provisioning**: Certificates issued automatically via ACME
- **Wildcard Support**: DNS challenge for `*.agent-hive.yourdomain.com`
- **Automatic Renewal**: Certificates renewed 15 days before expiry
- **Multiple Domains**: Support for multiple subdomains and SAN certificates

**Certificate Types:**
- **Production**: Let's Encrypt production CA
- **Staging**: Let's Encrypt staging CA for testing
- **Self-signed**: Development and testing environments

```bash
# Check certificate status
kubectl get certificates -n leanvibe-agent-hive
kubectl describe certificate agent-hive-wildcard-cert -n leanvibe-agent-hive

# Check certificate expiry
openssl s_client -connect agent-hive.yourdomain.com:443 -servername agent-hive.yourdomain.com | openssl x509 -noout -dates
```

### Secret Management

**Kubernetes Native**: Encrypted at rest with automatic rotation monitoring

**Secret Categories:**
- **Database Credentials**: PostgreSQL and Redis passwords
- **API Keys**: JWT secrets, webhook secrets, API keys
- **TLS Certificates**: Managed by cert-manager
- **External Services**: Cloudflare API tokens, monitoring credentials

**Rotation Policy:**
- **Database passwords**: Every 90 days
- **JWT secrets**: Every 30 days
- **API keys**: Every 60 days
- **Emergency rotation**: Immediate if compromised

```bash
# Check secret rotation status
kubectl get cronjob secret-rotation-check -n leanvibe-agent-hive
kubectl logs job/$(kubectl get jobs -n leanvibe-agent-hive -l job-name=secret-rotation-check -o name | head -1 | cut -d/ -f2) -n leanvibe-agent-hive
```

### Security Monitoring

**Runtime Security**: Falco for real-time threat detection

**Monitored Events:**
- **Suspicious network activity**: Unexpected connections
- **File access violations**: Access to sensitive files
- **Privilege escalation**: Attempts to gain elevated privileges
- **Shell activity**: Unexpected shell spawning in containers

**Alerting Rules:**
- **Failed authentication**: High rate of 401/403 responses
- **Certificate expiry**: SSL certificates expiring soon
- **Security violations**: Pod security policy violations
- **Network anomalies**: Unusual traffic patterns

```bash
# Check security monitoring
kubectl logs -f daemonset/security-monitoring-agent -n leanvibe-agent-hive

# View security alerts
kubectl logs -n leanvibe-agent-hive -l app.kubernetes.io/name=prometheus | grep security
```

## Configuration

### Environment-Specific Security

#### Development
```bash
./deploy-security.sh -e development --skip-monitoring
```
- Relaxed policies for development productivity
- Self-signed certificates
- Simplified network policies
- Basic secret management

#### Production
```bash
./deploy-security.sh -e production
```
- Strict security policies enforced
- Let's Encrypt certificates
- Comprehensive network isolation
- Full security monitoring
- Secret rotation automation

### Custom Security Policies

#### Custom Pod Security Policy
```yaml
apiVersion: policy/v1
kind: PodSecurityPolicy
metadata:
  name: custom-psp
spec:
  # Customize based on your requirements
  privileged: false
  runAsUser:
    rule: 'MustRunAsNonRoot'
  readOnlyRootFilesystem: true
```

#### Custom Network Policy
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: custom-network-policy
spec:
  podSelector:
    matchLabels:
      app: your-app
  policyTypes:
  - Ingress
  - Egress
  # Define custom rules
```

## Security Hardening

### Container Security

**Security Context Configuration:**
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 65534
  runAsGroup: 65534
  fsGroup: 65534
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
    - ALL
```

**Resource Limits:**
```yaml
resources:
  limits:
    memory: "1Gi"
    cpu: "1000m"
  requests:
    memory: "256Mi"
    cpu: "250m"
```

### Network Hardening

**Ingress Security:**
- Rate limiting: 100 req/s with burst protection
- Security headers: HSTS, CSP, X-Frame-Options
- CORS configuration: Restricted origins
- SSL/TLS: TLS 1.2+ with secure ciphers

**Network Segmentation:**
- Default deny all traffic
- Explicit allow rules for required communication
- Monitoring traffic allowed to specific endpoints
- DNS resolution allowed for all pods

### Secret Security

**Best Practices:**
- Never store secrets in container images
- Use Kubernetes secrets with encryption at rest
- Implement regular secret rotation
- Monitor secret access and usage
- Use external secret management for sensitive workloads

## Monitoring and Alerting

### Security Metrics

**Prometheus Metrics:**
```bash
# Authentication failures
rate(http_requests_total{status=~"401|403"}[5m])

# Network traffic anomalies
rate(container_network_transmit_bytes_total[5m])

# Certificate expiry
probe_ssl_earliest_cert_expiry - time()
```

### Security Alerts

**Critical Alerts:**
- Pod security policy violations
- Privilege escalation attempts
- Certificate expiry warnings
- High authentication failure rates

**Alert Configuration:**
```yaml
- alert: SecurityViolation
  expr: increase(security_violations_total[5m]) > 0
  labels:
    severity: critical
```

### Log Analysis

**Security Logs:**
- Falco security events
- Audit logs from Kubernetes API
- Application authentication logs
- Network policy enforcement logs

```bash
# View security events
kubectl logs -n leanvibe-agent-hive -l app.kubernetes.io/name=security-monitoring

# Check audit logs (if enabled)
kubectl logs -n kube-system kube-apiserver-* | grep audit
```

## Compliance and Auditing

### Security Standards

**Compliance Frameworks:**
- **CIS Kubernetes Benchmark**: Pod security, network policies, RBAC
- **PCI DSS**: If handling payment data
- **GDPR**: Data protection and privacy
- **SOX**: If publicly traded company

### Audit Checklist

**Monthly Security Review:**
- [ ] Certificate expiry dates
- [ ] Secret rotation status
- [ ] Security policy compliance
- [ ] Network policy effectiveness
- [ ] Security monitoring alerts
- [ ] Access control reviews

**Quarterly Security Assessment:**
- [ ] Penetration testing
- [ ] Vulnerability scanning
- [ ] Security policy updates
- [ ] Incident response testing
- [ ] Compliance validation

### Documentation Requirements

**Security Documentation:**
- Incident response procedures
- Security policy documentation
- Access control matrices
- Change management procedures
- Disaster recovery plans

## Troubleshooting

### Common Security Issues

#### 1. Pod Security Policy Violations
```bash
# Check PSP violations
kubectl get events -n leanvibe-agent-hive --field-selector reason=FailedCreate

# Check pod security context
kubectl describe pod <pod-name> -n leanvibe-agent-hive
```

#### 2. Network Policy Blocking Traffic
```bash
# Check network policies
kubectl get networkpolicy -n leanvibe-agent-hive
kubectl describe networkpolicy <policy-name> -n leanvibe-agent-hive

# Test connectivity
kubectl exec -it <pod-name> -n leanvibe-agent-hive -- curl <target-service>
```

#### 3. Certificate Issues
```bash
# Check certificate status
kubectl describe certificate <cert-name> -n leanvibe-agent-hive

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Test certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

#### 4. Secret Access Issues
```bash
# Check secret existence
kubectl get secrets -n leanvibe-agent-hive

# Check RBAC permissions
kubectl auth can-i get secrets --as=system:serviceaccount:leanvibe-agent-hive:agent-hive-service-account

# Check secret mounting
kubectl describe pod <pod-name> -n leanvibe-agent-hive
```

### Debugging Commands

```bash
# Security assessment
kubectl get pods -n leanvibe-agent-hive -o custom-columns='NAME:.metadata.name,ROOT:.spec.securityContext.runAsNonRoot,READONLY:.spec.containers[*].securityContext.readOnlyRootFilesystem'

# Network connectivity test
kubectl run network-test --image=busybox --rm -it --restart=Never -- /bin/sh

# Certificate validation
kubectl exec -it deployment/agent-hive -n leanvibe-agent-hive -- openssl s_client -connect postgres:5432

# Security monitoring logs
kubectl logs -f daemonset/security-monitoring-agent -n leanvibe-agent-hive
```

## Emergency Procedures

### Security Incident Response

**Immediate Actions:**
1. Isolate affected pods/services
2. Collect logs and forensic data
3. Notify security team
4. Apply emergency patches
5. Rotate compromised credentials

**Network Isolation:**
```bash
# Emergency network isolation
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: emergency-isolation
  namespace: leanvibe-agent-hive
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: leanvibe-agent-hive
  policyTypes:
  - Ingress
  - Egress
EOF
```

**Emergency Secret Rotation:**
```bash
# Generate new JWT secret
NEW_JWT_SECRET=$(openssl rand -base64 32)

# Update secret
kubectl patch secret agent-hive-secrets -n leanvibe-agent-hive -p='{"data":{"jwt-secret":"'$(echo -n $NEW_JWT_SECRET | base64)'"}}'

# Restart application
kubectl rollout restart deployment/agent-hive -n leanvibe-agent-hive
```

## Future Enhancements

1. **Advanced Threat Detection**: ML-based anomaly detection
2. **Zero Trust Architecture**: Service mesh with mTLS
3. **Hardware Security**: TPM and secure boot integration
4. **Compliance Automation**: Automated compliance scanning
5. **Advanced Secret Management**: Vault integration with dynamic secrets
6. **Security Automation**: Automated incident response

## Support

For security issues:
1. **Non-critical**: Create GitHub issue with security label
2. **Critical**: Contact security team immediately
3. **Emergency**: Follow incident response procedures
4. **Compliance**: Consult with legal/compliance team

**Security Contacts:**
- Security Team: security@leanvibe.com
- Incident Response: incident@leanvibe.com
- Compliance: compliance@leanvibe.com