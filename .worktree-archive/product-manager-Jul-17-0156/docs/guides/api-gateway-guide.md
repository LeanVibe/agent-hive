# API Gateway Configuration Guide

This guide provides comprehensive instructions for configuring and managing the LeanVibe Agent Hive API Gateway.

## Overview

The API Gateway serves as the single entry point for all client requests, providing:
- Request routing and load balancing
- Authentication and authorization
- Rate limiting and throttling
- Request/response transformation
- Monitoring and logging
- Security enforcement

## Architecture

```
Client → API Gateway → Service Discovery → Microservices
          ↓
       Monitoring & Logging
```

### Components
- **Gateway Router**: Routes requests to appropriate services
- **Load Balancer**: Distributes requests across service instances
- **Auth Handler**: Manages authentication and authorization
- **Rate Limiter**: Enforces rate limiting policies
- **Circuit Breaker**: Handles service failures gracefully
- **Middleware Chain**: Processes requests and responses

## Installation and Setup

### Prerequisites
- Python 3.12+
- Redis (for rate limiting and caching)
- Service Discovery service running
- TLS certificates for HTTPS

### Installation
```bash
# Install dependencies
uv add fastapi uvicorn redis python-multipart

# Install gateway package
pip install leanvibe-api-gateway

# Or from source
git clone https://github.com/leanvibe/agent-hive.git
cd agent-hive/src/api-gateway
uv sync
```

### Basic Configuration
```yaml
# config/gateway.yaml
gateway:
  host: "0.0.0.0"
  port: 8080
  workers: 4
  
  # Service Discovery
  service_discovery:
    backend: "consul"
    host: "localhost"
    port: 8500
    
  # Authentication
  auth:
    provider: "jwt"
    secret_key: "${JWT_SECRET_KEY}"
    algorithm: "HS256"
    expire_minutes: 30
    
  # Rate Limiting
  rate_limiting:
    backend: "redis"
    redis_url: "redis://localhost:6379"
    default_limit: "100/minute"
    
  # CORS
  cors:
    allow_origins: ["https://app.leanvibe.com"]
    allow_methods: ["GET", "POST", "PUT", "DELETE"]
    allow_headers: ["Authorization", "Content-Type"]
    
  # TLS
  tls:
    cert_file: "/etc/ssl/certs/gateway.crt"
    key_file: "/etc/ssl/private/gateway.key"
```

## Configuration Reference

### Gateway Settings
```yaml
gateway:
  # Server Configuration
  host: "0.0.0.0"           # Bind address
  port: 8080                # Listen port
  workers: 4                # Number of worker processes
  worker_class: "uvicorn.workers.UvicornWorker"
  max_requests: 1000        # Max requests per worker
  max_requests_jitter: 100  # Jitter for max_requests
  timeout: 30               # Request timeout
  
  # Request Handling
  max_request_size: 16777216  # 16MB
  client_timeout: 60          # Client connection timeout
  keep_alive: 2               # Keep-alive timeout
  
  # Performance
  enable_compression: true
  compression_threshold: 1024
  enable_caching: true
  cache_ttl: 300
```

### Routing Configuration
```yaml
routes:
  # Agent Management Service
  - path: "/api/v1/agents"
    service: "agent-service"
    methods: ["GET", "POST", "PUT", "DELETE"]
    auth_required: true
    rate_limit: "50/minute"
    timeout: 30
    
  # Workflow Service
  - path: "/api/v1/workflows"
    service: "workflow-service"
    methods: ["GET", "POST", "PUT", "DELETE"]
    auth_required: true
    rate_limit: "30/minute"
    timeout: 60
    
  # Public Health Check
  - path: "/health"
    service: "gateway-health"
    methods: ["GET"]
    auth_required: false
    rate_limit: "1000/minute"
    timeout: 5
    
  # WebSocket Routes
  - path: "/ws/agent-events"
    service: "event-service"
    protocol: "websocket"
    auth_required: true
    rate_limit: "10/minute"
```

### Load Balancing
```yaml
load_balancing:
  # Strategy: round_robin, least_connections, least_response_time, ip_hash
  strategy: "least_connections"
  
  # Health Checks
  health_check:
    enabled: true
    interval: 30          # seconds
    timeout: 5            # seconds
    healthy_threshold: 2  # consecutive successes
    unhealthy_threshold: 3 # consecutive failures
    path: "/health"
    expected_status: [200, 204]
    
  # Circuit Breaker
  circuit_breaker:
    enabled: true
    failure_threshold: 5    # failures before opening
    recovery_timeout: 60    # seconds
    test_request_volume: 10 # test requests during half-open
```

## Authentication and Authorization

### JWT Authentication
```python
# Authentication configuration
auth_config = {
    "provider": "jwt",
    "secret_key": os.getenv("JWT_SECRET_KEY"),
    "algorithm": "HS256",
    "expire_minutes": 30,
    "refresh_expire_days": 7,
    "issuer": "leanvibe-api-gateway",
    "audience": "leanvibe-services"
}

# Custom claims
custom_claims = {
    "user_id": "required",
    "roles": "required",
    "permissions": "optional",
    "tenant_id": "optional"
}
```

### OAuth 2.0 Integration
```yaml
auth:
  provider: "oauth2"
  oauth2:
    # Authorization Server
    authorization_url: "https://auth.leanvibe.com/oauth/authorize"
    token_url: "https://auth.leanvibe.com/oauth/token"
    userinfo_url: "https://auth.leanvibe.com/oauth/userinfo"
    
    # Client Configuration
    client_id: "${OAUTH_CLIENT_ID}"
    client_secret: "${OAUTH_CLIENT_SECRET}"
    redirect_uri: "https://gateway.leanvibe.com/auth/callback"
    
    # Scopes
    scopes: ["openid", "profile", "email", "agents:read", "agents:write"]
    
    # Token Validation
    verify_signature: true
    verify_audience: true
    verify_issuer: true
    leeway: 30  # seconds
```

### Role-Based Access Control
```yaml
rbac:
  roles:
    admin:
      permissions: ["*"]
      
    developer:
      permissions:
        - "agents:read"
        - "agents:write"
        - "workflows:read"
        - "workflows:write"
        - "logs:read"
        
    viewer:
      permissions:
        - "agents:read"
        - "workflows:read"
        - "logs:read"
  
  # Route-level permissions
  route_permissions:
    "/api/v1/agents": ["agents:read", "agents:write"]
    "/api/v1/workflows": ["workflows:read", "workflows:write"]
    "/api/v1/admin/*": ["admin"]
```

## Rate Limiting

### Configuration
```yaml
rate_limiting:
  backend: "redis"
  redis_url: "redis://localhost:6379"
  key_prefix: "ratelimit"
  
  # Default limits
  default_limit: "100/minute"
  
  # Per-route limits
  route_limits:
    "/api/v1/agents": "50/minute"
    "/api/v1/workflows": "30/minute"
    "/health": "1000/minute"
    
  # Per-user limits
  user_limits:
    premium: "1000/hour"
    standard: "100/hour"
    free: "50/hour"
    
  # IP-based limits
  ip_limits:
    default: "200/minute"
    whitelist:
      - "192.168.1.0/24"
      - "10.0.0.0/8"
```

### Rate Limiting Strategies
```python
# Time window strategies
strategies = {
    "fixed_window": {
        "window_size": 60,  # seconds
        "max_requests": 100
    },
    
    "sliding_window": {
        "window_size": 60,  # seconds
        "max_requests": 100,
        "precision": 10     # sub-windows
    },
    
    "token_bucket": {
        "capacity": 100,    # bucket size
        "refill_rate": 10,  # tokens per second
        "initial_tokens": 100
    }
}
```

## Request/Response Transformation

### Request Transformation
```yaml
transformations:
  request:
    # Add headers
    add_headers:
      "X-Gateway-Version": "1.0"
      "X-Request-ID": "{{request_id}}"
      "X-Forwarded-By": "leanvibe-gateway"
      
    # Remove headers
    remove_headers:
      - "X-Internal-Token"
      - "X-Debug-Info"
      
    # Modify path
    path_rewrite:
      "^/api/v1/": "/internal/api/"
      
    # Query parameter transformation
    query_transform:
      rename:
        "q": "query"
        "p": "page"
      add:
        "source": "gateway"
```

### Response Transformation
```yaml
transformations:
  response:
    # Add headers
    add_headers:
      "X-Gateway-Response": "true"
      "X-Response-Time": "{{response_time}}"
      
    # CORS headers
    cors_headers:
      "Access-Control-Allow-Origin": "*"
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE"
      "Access-Control-Allow-Headers": "Authorization, Content-Type"
      
    # Security headers
    security_headers:
      "X-Content-Type-Options": "nosniff"
      "X-Frame-Options": "DENY"
      "X-XSS-Protection": "1; mode=block"
      "Strict-Transport-Security": "max-age=31536000"
```

## Monitoring and Logging

### Metrics Collection
```yaml
monitoring:
  metrics:
    enabled: true
    endpoint: "/metrics"
    format: "prometheus"
    
    # Custom metrics
    custom_metrics:
      - name: "gateway_requests_total"
        type: "counter"
        labels: ["method", "route", "status"]
        
      - name: "gateway_request_duration"
        type: "histogram"
        labels: ["method", "route"]
        buckets: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
        
      - name: "gateway_active_connections"
        type: "gauge"
        labels: ["protocol"]
```

### Logging Configuration
```yaml
logging:
  level: "INFO"
  format: "json"
  
  # Access logs
  access_log:
    enabled: true
    format: "combined"
    file: "/var/log/gateway/access.log"
    rotation: "daily"
    retention: 30  # days
    
  # Error logs
  error_log:
    enabled: true
    file: "/var/log/gateway/error.log"
    rotation: "daily"
    retention: 30  # days
    
  # Structured logging
  structured:
    enabled: true
    fields:
      - "timestamp"
      - "level"
      - "request_id"
      - "user_id"
      - "method"
      - "path"
      - "status_code"
      - "response_time"
      - "user_agent"
      - "ip_address"
```

## Security Configuration

### TLS/SSL Setup
```yaml
tls:
  enabled: true
  cert_file: "/etc/ssl/certs/gateway.crt"
  key_file: "/etc/ssl/private/gateway.key"
  ca_file: "/etc/ssl/certs/ca.crt"
  
  # TLS Version
  min_version: "TLSv1.2"
  max_version: "TLSv1.3"
  
  # Cipher Suites
  ciphers: "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"
  
  # HSTS
  hsts:
    enabled: true
    max_age: 31536000
    include_subdomains: true
    preload: true
```

### Security Headers
```yaml
security:
  headers:
    # Content Security Policy
    content_security_policy: "default-src 'self'; script-src 'self' 'unsafe-inline'"
    
    # CORS
    cors:
      enabled: true
      allow_origins: ["https://app.leanvibe.com"]
      allow_methods: ["GET", "POST", "PUT", "DELETE"]
      allow_headers: ["Authorization", "Content-Type"]
      expose_headers: ["X-Request-ID"]
      allow_credentials: true
      max_age: 86400
      
    # Additional headers
    x_content_type_options: "nosniff"
    x_frame_options: "DENY"
    x_xss_protection: "1; mode=block"
    referrer_policy: "strict-origin-when-cross-origin"
```

## Deployment

### Docker Deployment
```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Kubernetes Deployment
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: leanvibe
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: gateway
        image: leanvibe/api-gateway:latest
        ports:
        - containerPort: 8080
        env:
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: gateway-secrets
              key: jwt-secret
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway-service
  namespace: leanvibe
spec:
  selector:
    app: api-gateway
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

### Service Configuration
```yaml
# service.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: gateway-config
  namespace: leanvibe
data:
  gateway.yaml: |
    gateway:
      host: "0.0.0.0"
      port: 8080
      workers: 4
    service_discovery:
      backend: "kubernetes"
      namespace: "leanvibe"
    auth:
      provider: "jwt"
      secret_key: "${JWT_SECRET_KEY}"
    rate_limiting:
      backend: "redis"
      redis_url: "redis://redis-service:6379"
```

## Troubleshooting

### Common Issues

**Service Discovery Connection Failed**
```bash
# Check service discovery health
curl http://consul:8500/v1/status/leader

# Check DNS resolution
nslookup consul
dig consul.service.consul

# Check network connectivity
telnet consul 8500
```

**Authentication Failures**
```bash
# Validate JWT token
python -c "
import jwt
import os
token = 'your-token-here'
secret = os.getenv('JWT_SECRET_KEY')
decoded = jwt.decode(token, secret, algorithms=['HS256'])
print(decoded)
"

# Check token expiration
date -d @$(echo 'your-token' | base64 -d | jq -r '.exp')
```

**Rate Limiting Issues**
```bash
# Check Redis connection
redis-cli ping

# Check rate limit keys
redis-cli keys "ratelimit:*"

# Reset rate limits
redis-cli del "ratelimit:user:123"
```

**Load Balancing Problems**
```bash
# Check service health
curl -f http://service-instance:port/health

# Check service registration
curl http://consul:8500/v1/health/service/agent-service

# Test direct connection
curl http://service-instance:port/api/v1/agents
```

### Debug Commands
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Test gateway health
curl -v http://gateway:8080/health

# Check metrics
curl http://gateway:8080/metrics

# View access logs
tail -f /var/log/gateway/access.log

# Monitor connections
netstat -an | grep :8080
```

### Performance Tuning

**Connection Pool Settings**
```yaml
connection_pool:
  max_connections: 100
  max_connections_per_host: 20
  keepalive_timeout: 30
  connection_timeout: 10
  read_timeout: 30
  write_timeout: 30
```

**Worker Configuration**
```yaml
workers:
  count: 4  # CPU cores * 2
  worker_class: "uvicorn.workers.UvicornWorker"
  max_requests: 1000
  max_requests_jitter: 100
  worker_timeout: 30
  graceful_timeout: 30
```

**Memory and CPU Optimization**
```yaml
performance:
  # Memory settings
  max_memory_usage: "1GB"
  garbage_collection:
    enabled: true
    threshold: [700, 10, 10]
    
  # CPU settings
  enable_async: true
  async_pool_size: 10
  
  # Caching
  enable_response_cache: true
  cache_ttl: 300
  cache_max_size: "100MB"
```

## API Reference

### Gateway Management API

**Health Check**
```http
GET /health
Content-Type: application/json

{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0",
  "services": {
    "agent-service": "healthy",
    "workflow-service": "healthy"
  }
}
```

**Metrics Endpoint**
```http
GET /metrics
Content-Type: text/plain

# HELP gateway_requests_total Total number of requests
# TYPE gateway_requests_total counter
gateway_requests_total{method="GET",route="/api/v1/agents",status="200"} 100

# HELP gateway_request_duration Request duration in seconds
# TYPE gateway_request_duration histogram
gateway_request_duration_bucket{method="GET",route="/api/v1/agents",le="0.1"} 50
```

**Configuration Reload**
```http
POST /admin/reload
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "component": "routes"  # or "all"
}
```

### Route Management

**List Routes**
```http
GET /admin/routes
Authorization: Bearer <admin-token>

{
  "routes": [
    {
      "path": "/api/v1/agents",
      "service": "agent-service",
      "methods": ["GET", "POST"],
      "auth_required": true
    }
  ]
}
```

**Add Route**
```http
POST /admin/routes
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "path": "/api/v1/new-service",
  "service": "new-service",
  "methods": ["GET", "POST"],
  "auth_required": true,
  "rate_limit": "100/minute"
}
```

## Best Practices

### Configuration Management
- Use environment variables for sensitive data
- Implement configuration validation
- Use configuration versioning
- Test configurations in staging environment
- Implement gradual rollouts

### Security Best Practices
- Always use HTTPS in production
- Implement proper authentication
- Use strong JWT secrets
- Enable rate limiting
- Monitor for security threats
- Regular security audits

### Performance Optimization
- Use connection pooling
- Implement proper caching
- Monitor response times
- Optimize worker configuration
- Use load balancing
- Implement circuit breakers

### Monitoring and Alerting
- Monitor all key metrics
- Set up proper alerting
- Implement health checks
- Use structured logging
- Monitor downstream services
- Track error rates and patterns

## Conclusion

The API Gateway is a critical component that requires careful configuration and monitoring. Follow this guide to ensure proper setup, security, and performance of your gateway deployment.

Regular monitoring, maintenance, and updates are essential for optimal operation and security.