# Deployment Guide

**📋 Implementation Status**: This guide covers deployment plans for both current and future functionality.

**✅ Currently Deployable**:
- Python API with advanced_orchestration module
- Multi-agent coordination system as a library
- Intelligence Framework with ML-based decision making
- External API Integration (WebhookServer, ApiGateway, EventStreaming)
- Enhanced ML Systems (PatternOptimizer, PredictiveAnalytics, AdaptiveLearning)
- Test suite and development environment (26 tests with 96% coverage)

**❌ Not Yet Deployable**:
- CLI interface and orchestrator service
- Configuration management system
- Monitoring and observability components
- Production-ready service wrappers

This guide covers deployment strategies for the current Python API and plans for future production deployment when CLI and service layers are implemented.

## Table of Contents

- [Overview](#overview)
- [Deployment Strategies](#deployment-strategies)
- [Docker Configuration](#docker-configuration)
- [External API Integration Deployment](#external-api-integration-deployment)
- [Production Environment Setup](#production-environment-setup)
- [Security Considerations](#security-considerations)
- [Monitoring and Observability](#monitoring-and-observability)
- [Scalability and Performance](#scalability-and-performance)
- [Backup and Recovery](#backup-and-recovery)
- [CI/CD Pipeline](#cicd-pipeline)
- [Troubleshooting Production Issues](#troubleshooting-production-issues)

## Overview

LeanVibe Agent Hive is designed for production deployment with high availability, scalability, and security. This guide covers deployment from single-instance setups to large-scale distributed environments.

### Production Readiness Checklist

**✅ Currently Ready**:
- [x] **Core Implementation**: MultiAgentCoordinator, ResourceManager, ScalingManager
- [x] **Intelligence Framework**: ML-based decision making with confidence scoring
- [x] **Task Allocation**: Intelligent task routing and agent performance profiling
- [x] **Agent Coordination**: Multi-agent collaboration protocols and coordination sessions
- [x] **Performance Monitoring**: Real-time monitoring and optimization with intelligent recommendations
- [x] **External API Integration**: WebhookServer, ApiGateway, EventStreaming with production-ready capabilities
- [x] **Enhanced ML Systems**: PatternOptimizer, PredictiveAnalytics, AdaptiveLearning
- [x] **Testing Foundation**: 26 tests with 96% coverage (comprehensive intelligence framework testing)
- [x] **Python API**: Stable import paths and data models with Phase 2 integrations

**❌ Not Yet Ready for Production**:
- [ ] **CLI Interface**: Command-line orchestrator and service wrapper
- [ ] **Configuration Management**: Centralized config and environment handling
- [ ] **Service Infrastructure**: Process management, logging, monitoring
- [ ] **Security Framework**: Authentication, authorization, access controls
- [ ] **Performance Validation**: Latency benchmarks and MTTR measurement

### Architecture Overview for Deployment

```mermaid
graph TB
    subgraph "Production Environment"
        LB[Load Balancer]
        
        subgraph "Orchestrator Cluster"
            O1[Orchestrator 1]
            O2[Orchestrator 2]
            O3[Orchestrator 3]
        end
        
        subgraph "Agent Pools"
            subgraph "Backend Agents"
                BA1[Backend Agent 1]
                BA2[Backend Agent 2]
                BA3[Backend Agent 3]
            end
            
            subgraph "Frontend Agents"
                FA1[Frontend Agent 1]
                FA2[Frontend Agent 2]
            end
            
            subgraph "iOS Agents"
                IA1[iOS Agent 1]
                IA2[iOS Agent 2]
            end
        end
        
        subgraph "Data Layer"
            DB[(SQLite Cluster)]
            FS[File Storage]
            CACHE[Redis Cache]
        end
        
        subgraph "Monitoring"
            PROM[Prometheus]
            GRAF[Grafana]
            ALERT[AlertManager]
        end
        
        LB --> O1
        LB --> O2
        LB --> O3
        
        O1 --> BA1
        O2 --> FA1
        O3 --> IA1
        
        O1 --> DB
        O2 --> CACHE
        O3 --> FS
        
        O1 --> PROM
        PROM --> GRAF
        PROM --> ALERT
    end
```

## Deployment Strategies

### Single Instance Deployment

**Use Case**: Development, testing, small teams (<5 developers)

#### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  agent-hive:
    build: .
    container_name: agent-hive
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - LEANVIBE_SYSTEM_LOG_LEVEL=INFO
      - LEANVIBE_SYSTEM_DEBUG_MODE=false
      - LEANVIBE_MULTI_AGENT_MAX_AGENTS=5
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/.claude/config
    healthcheck:
      test: ["CMD", "python", "-c", "from claude.utils.health_check import basic_health_check; basic_health_check()"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis:
    image: redis:7-alpine
    container_name: agent-hive-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  prometheus:
    image: prom/prometheus:latest
    container_name: agent-hive-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

volumes:
  redis_data:
  prometheus_data:
```

#### Quick Start

```bash
# Clone and setup
git clone https://github.com/leanvibe/agent-hive.git
cd agent-hive

# Create production configuration
cp .claude/config/config.yaml.production .claude/config/config.yaml

# Build and deploy
docker-compose up -d

# Verify deployment
docker-compose ps
docker-compose logs agent-hive
```

### High Availability Deployment

**Use Case**: Production environments, teams >10 developers, critical workloads

#### Kubernetes Configuration

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: agent-hive
  labels:
    app: agent-hive
    environment: production

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agent-hive-config
  namespace: agent-hive
data:
  config.yaml: |
    system:
      log_level: INFO
      debug_mode: false
      max_concurrent_tasks: 50
    
    multi_agent:
      enabled: true
      max_agents: 20
      min_agents: 5
      load_balancing_strategy: "least_loaded"
      health_check_interval: 30
    
    resources:
      monitoring:
        cpu: true
        memory: true
        disk: true
        network: true
      allocation:
        cpu_limit_percent: 80
        memory_limit_percent: 75
    
    scaling:
      enabled: true
      auto_scale: true
      strategies:
        scale_up:
          threshold: 0.8
          factor: 1.5
          max_instances: 20
        scale_down:
          threshold: 0.3
          factor: 0.7
          min_instances: 5

---
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-hive-orchestrator
  namespace: agent-hive
  labels:
    app: agent-hive
    component: orchestrator
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: agent-hive
      component: orchestrator
  template:
    metadata:
      labels:
        app: agent-hive
        component: orchestrator
    spec:
      containers:
      - name: orchestrator
        image: leanvibe/agent-hive:latest
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 8081
          name: metrics
        env:
        - name: LEANVIBE_SYSTEM_LOG_LEVEL
          value: "INFO"
        - name: LEANVIBE_MULTI_AGENT_MAX_AGENTS
          value: "20"
        - name: LEANVIBE_RESOURCES_CPU_LIMIT_PERCENT
          value: "80"
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2
            memory: 4Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
        volumeMounts:
        - name: config
          mountPath: /app/.claude/config
        - name: data
          mountPath: /app/data
      volumes:
      - name: config
        configMap:
          name: agent-hive-config
      - name: data
        persistentVolumeClaim:
          claimName: agent-hive-data

---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: agent-hive-service
  namespace: agent-hive
  labels:
    app: agent-hive
spec:
  selector:
    app: agent-hive
    component: orchestrator
  ports:
  - name: http
    port: 80
    targetPort: 8080
  - name: metrics
    port: 8081
    targetPort: 8081
  type: ClusterIP

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: agent-hive-ingress
  namespace: agent-hive
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - agent-hive.example.com
    secretName: agent-hive-tls
  rules:
  - host: agent-hive.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: agent-hive-service
            port:
              number: 80
```

#### Deployment Commands

```bash
# Apply Kubernetes configuration
kubectl apply -f k8s/

# Verify deployment
kubectl get pods -n agent-hive
kubectl get services -n agent-hive
kubectl logs -n agent-hive -l app=agent-hive --tail=100

# Scale deployment
kubectl scale deployment agent-hive-orchestrator --replicas=5 -n agent-hive

# Rolling update
kubectl set image deployment/agent-hive-orchestrator orchestrator=leanvibe/agent-hive:v2.1 -n agent-hive
```

## Docker Configuration

**📋 Comprehensive Guide Available**: See [Docker Deployment Guide](docs/guides/docker-deployment.md) for complete Docker setup, from single-node development to multi-node production clusters.

### Quick Docker Setup

### Multi-Stage Dockerfile

```dockerfile
# Dockerfile
FROM python:3.12-slim as builder

# Install UV for dependency management
RUN pip install uv

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.12-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r agent-hive && useradd -r -g agent-hive agent-hive

# Set work directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Make sure to use venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs \
    && chown -R agent-hive:agent-hive /app

# Switch to non-root user
USER agent-hive

# Expose ports
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "from claude.utils.health_check import basic_health_check; basic_health_check()" || exit 1

# Default command
CMD ["python", ".claude/orchestrator.py"]
```

### Docker Compose for Development

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  agent-hive:
    build:
      context: .
      target: development
    volumes:
      - .:/app
      - ~/.cache/uv:/root/.cache/uv
    environment:
      - LEANVIBE_SYSTEM_DEBUG_MODE=true
      - LEANVIBE_DEVELOPMENT_USE_MOCK_CLI=true
    ports:
      - "8080:8080"
      - "8081:8081"
    command: uv run python .claude/orchestrator.py --dev
    
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: agent_hive_dev
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data

volumes:
  postgres_dev_data:
```

### Build and Push Images

```bash
# Build multi-platform images
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 -t leanvibe/agent-hive:latest .

# Tag and push
docker tag leanvibe/agent-hive:latest leanvibe/agent-hive:v2.1
docker push leanvibe/agent-hive:latest
docker push leanvibe/agent-hive:v2.1

# Development build
docker-compose -f docker-compose.dev.yml up --build
```

## External API Integration Deployment

**✅ Status**: Production ready with comprehensive external API integration capabilities.

### External API Services Architecture

The LeanVibe Agent Hive includes three core external API services that provide comprehensive integration capabilities:

1. **WebhookServer** - HTTP endpoint handling with rate limiting and event validation
2. **ApiGateway** - RESTful API management with authentication and CORS support  
3. **EventStreaming** - Real-time event distribution with compression and batching

### Multi-Service Docker Compose Configuration

```yaml
# docker-compose.external-api.yml
version: '3.8'

services:
  agent-hive:
    build: .
    container_name: agent-hive-core
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - LEANVIBE_SYSTEM_LOG_LEVEL=INFO
      - LEANVIBE_MULTI_AGENT_MAX_AGENTS=10
      - LEANVIBE_EXTERNAL_API_WEBHOOK_ENABLED=true
      - LEANVIBE_EXTERNAL_API_GATEWAY_ENABLED=true
      - LEANVIBE_EXTERNAL_API_STREAMING_ENABLED=true
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/.claude/config
    depends_on:
      - redis
      - postgres
    networks:
      - agent-hive-network

  webhook-server:
    build: .
    container_name: agent-hive-webhook
    restart: unless-stopped
    ports:
      - "8081:8081"
    environment:
      - LEANVIBE_WEBHOOK_PORT=8081
      - LEANVIBE_WEBHOOK_HOST=0.0.0.0
      - LEANVIBE_WEBHOOK_RATE_LIMIT=100
      - LEANVIBE_WEBHOOK_AUTH_REQUIRED=true
    command: ["python", "-m", "external_api.webhook_server"]
    volumes:
      - ./logs:/app/logs
    networks:
      - agent-hive-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  api-gateway:
    build: .
    container_name: agent-hive-gateway
    restart: unless-stopped
    ports:
      - "8082:8082"
    environment:
      - LEANVIBE_GATEWAY_PORT=8082
      - LEANVIBE_GATEWAY_CORS_ENABLED=true
      - LEANVIBE_GATEWAY_AUTH_PROVIDER=jwt
      - LEANVIBE_GATEWAY_REQUEST_TIMEOUT=30
    command: ["python", "-m", "external_api.api_gateway"]
    volumes:
      - ./logs:/app/logs
    networks:
      - agent-hive-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8082/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  event-streaming:
    build: .
    container_name: agent-hive-streaming
    restart: unless-stopped
    ports:
      - "8083:8083"
    environment:
      - LEANVIBE_STREAMING_PORT=8083
      - LEANVIBE_STREAMING_COMPRESSION=true
      - LEANVIBE_STREAMING_BATCH_SIZE=10
      - LEANVIBE_STREAMING_FLUSH_INTERVAL=5.0
    command: ["python", "-m", "external_api.event_streaming"]
    volumes:
      - ./logs:/app/logs
    networks:
      - agent-hive-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8083/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    container_name: agent-hive-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - agent-hive-network

  postgres:
    image: postgres:15-alpine
    container_name: agent-hive-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: agent_hive
      POSTGRES_USER: agent_hive
      POSTGRES_PASSWORD: secure_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - agent-hive-network

  nginx:
    image: nginx:alpine
    container_name: agent-hive-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - agent-hive
      - webhook-server
      - api-gateway
      - event-streaming
    networks:
      - agent-hive-network

volumes:
  redis_data:
  postgres_data:

networks:
  agent-hive-network:
    driver: bridge
```

### Nginx Load Balancer Configuration

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream agent_hive_core {
        server agent-hive:8080;
    }

    upstream webhook_servers {
        server webhook-server:8081;
    }

    upstream api_gateways {
        server api-gateway:8082;
    }

    upstream event_streaming {
        server event-streaming:8083;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
    limit_req_zone $binary_remote_addr zone=webhook_limit:10m rate=50r/m;

    server {
        listen 80;
        server_name localhost;

        # Core API
        location /api/v1/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://agent_hive_core;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Webhook endpoints
        location /webhooks/ {
            limit_req zone=webhook_limit burst=10 nodelay;
            proxy_pass http://webhook_servers;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # API Gateway
        location /gateway/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://api_gateways;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Event Streaming
        location /stream/ {
            proxy_pass http://event_streaming;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Health checks
        location /health {
            access_log off;
            proxy_pass http://agent_hive_core;
        }
    }
}
```

### Kubernetes Deployment for External APIs

```yaml
# k8s/external-api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-hive-webhook-server
  namespace: agent-hive
  labels:
    app: agent-hive
    component: webhook-server
spec:
  replicas: 2
  selector:
    matchLabels:
      app: agent-hive
      component: webhook-server
  template:
    metadata:
      labels:
        app: agent-hive
        component: webhook-server
    spec:
      containers:
      - name: webhook-server
        image: leanvibe/agent-hive:latest
        command: ["python", "-m", "external_api.webhook_server"]
        ports:
        - containerPort: 8081
          name: webhook-port
        env:
        - name: LEANVIBE_WEBHOOK_PORT
          value: "8081"
        - name: LEANVIBE_WEBHOOK_HOST
          value: "0.0.0.0"
        - name: LEANVIBE_WEBHOOK_RATE_LIMIT
          value: "100"
        - name: LEANVIBE_WEBHOOK_AUTH_REQUIRED
          value: "true"
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 500m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8081
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8081
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-hive-api-gateway
  namespace: agent-hive
  labels:
    app: agent-hive
    component: api-gateway
spec:
  replicas: 2
  selector:
    matchLabels:
      app: agent-hive
      component: api-gateway
  template:
    metadata:
      labels:
        app: agent-hive
        component: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: leanvibe/agent-hive:latest
        command: ["python", "-m", "external_api.api_gateway"]
        ports:
        - containerPort: 8082
          name: gateway-port
        env:
        - name: LEANVIBE_GATEWAY_PORT
          value: "8082"
        - name: LEANVIBE_GATEWAY_CORS_ENABLED
          value: "true"
        - name: LEANVIBE_GATEWAY_AUTH_PROVIDER
          value: "jwt"
        - name: LEANVIBE_GATEWAY_REQUEST_TIMEOUT
          value: "30"
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 500m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8082
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8082
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-hive-event-streaming
  namespace: agent-hive
  labels:
    app: agent-hive
    component: event-streaming
spec:
  replicas: 2
  selector:
    matchLabels:
      app: agent-hive
      component: event-streaming
  template:
    metadata:
      labels:
        app: agent-hive
        component: event-streaming
    spec:
      containers:
      - name: event-streaming
        image: leanvibe/agent-hive:latest
        command: ["python", "-m", "external_api.event_streaming"]
        ports:
        - containerPort: 8083
          name: streaming-port
        env:
        - name: LEANVIBE_STREAMING_PORT
          value: "8083"
        - name: LEANVIBE_STREAMING_COMPRESSION
          value: "true"
        - name: LEANVIBE_STREAMING_BATCH_SIZE
          value: "10"
        - name: LEANVIBE_STREAMING_FLUSH_INTERVAL
          value: "5.0"
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 500m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8083
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8083
          initialDelaySeconds: 5
          periodSeconds: 5

---
# Services for External APIs
apiVersion: v1
kind: Service
metadata:
  name: agent-hive-webhook-service
  namespace: agent-hive
  labels:
    app: agent-hive
    component: webhook-server
spec:
  selector:
    app: agent-hive
    component: webhook-server
  ports:
  - name: webhook-port
    port: 8081
    targetPort: 8081
  type: ClusterIP

---
apiVersion: v1
kind: Service
metadata:
  name: agent-hive-gateway-service
  namespace: agent-hive
  labels:
    app: agent-hive
    component: api-gateway
spec:
  selector:
    app: agent-hive
    component: api-gateway
  ports:
  - name: gateway-port
    port: 8082
    targetPort: 8082
  type: ClusterIP

---
apiVersion: v1
kind: Service
metadata:
  name: agent-hive-streaming-service
  namespace: agent-hive
  labels:
    app: agent-hive
    component: event-streaming
spec:
  selector:
    app: agent-hive
    component: event-streaming
  ports:
  - name: streaming-port
    port: 8083
    targetPort: 8083
  type: ClusterIP
```

### External API Configuration

```yaml
# external-api-config.yaml
external_api:
  webhook_server:
    enabled: true
    port: 8081
    host: "0.0.0.0"
    rate_limit_per_minute: 100
    authentication_required: true
    cors_origins: ["https://example.com", "https://app.example.com"]
    endpoints:
      - path: "/github/webhook"
        methods: ["POST"]
        auth_required: true
        rate_limit: 50
      - path: "/slack/webhook"
        methods: ["POST"]
        auth_required: true
        rate_limit: 30
      - path: "/custom/webhook"
        methods: ["POST", "PUT"]
        auth_required: false
        rate_limit: 20

  api_gateway:
    enabled: true
    port: 8082
    cors_enabled: true
    cors_origins: ["*"]
    cors_methods: ["GET", "POST", "PUT", "DELETE"]
    cors_headers: ["Content-Type", "Authorization"]
    authentication_provider: "jwt"
    request_timeout: 30
    max_request_size: "10MB"
    routes:
      - path: "/api/v1/agents"
        methods: ["GET", "POST"]
        auth_required: true
        rate_limit: 100
      - path: "/api/v1/tasks"
        methods: ["GET", "POST", "PUT", "DELETE"]
        auth_required: true
        rate_limit: 200
      - path: "/api/v1/status"
        methods: ["GET"]
        auth_required: false
        rate_limit: 50

  event_streaming:
    enabled: true
    port: 8083
    compression_enabled: true
    compression_algorithm: "gzip"
    batch_size: 10
    flush_interval: 5.0
    max_connections: 1000
    heartbeat_interval: 30
    event_types:
      - "task_completed"
      - "task_failed"
      - "agent_status_changed"
      - "system_health_update"
      - "performance_metrics"
    filters:
      - type: "agent_id"
        values: ["agent_1", "agent_2"]
      - type: "priority"
        values: ["high", "critical"]
```

### External API Security Configuration

```yaml
# external-api-security.yaml
security:
  webhook_server:
    authentication:
      type: "api_key"
      header_name: "X-API-Key"
      validation_endpoint: "/auth/validate"
    rate_limiting:
      storage: "redis"
      redis_url: "redis://redis:6379"
      global_limit: 1000
      per_endpoint_limit: 100
    request_validation:
      max_payload_size: "5MB"
      required_headers: ["Content-Type", "X-API-Key"]
      allowed_content_types: ["application/json", "application/xml"]
    logging:
      log_requests: true
      log_responses: false
      log_errors: true
      sensitive_headers: ["Authorization", "X-API-Key"]

  api_gateway:
    authentication:
      jwt:
        secret_key: "${JWT_SECRET_KEY}"
        algorithm: "HS256"
        expiration: 3600
        issuer: "agent-hive"
      oauth2:
        provider: "custom"
        authorization_url: "https://auth.example.com/oauth/authorize"
        token_url: "https://auth.example.com/oauth/token"
        client_id: "${OAUTH2_CLIENT_ID}"
        client_secret: "${OAUTH2_CLIENT_SECRET}"
    cors:
      credentials: true
      max_age: 86400
      exposed_headers: ["X-Request-ID", "X-Rate-Limit"]
    request_validation:
      max_payload_size: "10MB"
      validate_json: true
      sanitize_input: true

  event_streaming:
    authentication:
      type: "token"
      token_header: "Authorization"
      token_prefix: "Bearer"
    encryption:
      enabled: true
      algorithm: "AES-256-GCM"
      key_rotation_interval: 86400
    access_control:
      subscription_auth_required: true
      publish_auth_required: true
      admin_endpoints_auth_required: true
```

### External API Monitoring and Alerts

```yaml
# external-api-monitoring.yaml
monitoring:
  webhook_server:
    metrics:
      - name: "webhook_requests_total"
        type: "counter"
        labels: ["endpoint", "method", "status_code"]
      - name: "webhook_request_duration_seconds"
        type: "histogram"
        labels: ["endpoint", "method"]
        buckets: [0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
      - name: "webhook_rate_limit_hits_total"
        type: "counter"
        labels: ["endpoint", "client_ip"]
    alerts:
      - name: "WebhookHighErrorRate"
        condition: "rate(webhook_requests_total{status_code=~'5..'}[5m]) > 0.1"
        severity: "warning"
        description: "High error rate in webhook server"
      - name: "WebhookHighLatency"
        condition: "histogram_quantile(0.95, webhook_request_duration_seconds) > 1.0"
        severity: "warning"
        description: "High latency in webhook processing"

  api_gateway:
    metrics:
      - name: "gateway_requests_total"
        type: "counter"
        labels: ["route", "method", "status_code"]
      - name: "gateway_request_duration_seconds"
        type: "histogram"
        labels: ["route", "method"]
        buckets: [0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
      - name: "gateway_concurrent_connections"
        type: "gauge"
        labels: ["route"]
    alerts:
      - name: "GatewayHighErrorRate"
        condition: "rate(gateway_requests_total{status_code=~'5..'}[5m]) > 0.1"
        severity: "critical"
        description: "High error rate in API gateway"
      - name: "GatewayConnectionLimit"
        condition: "gateway_concurrent_connections > 800"
        severity: "warning"
        description: "API gateway approaching connection limit"

  event_streaming:
    metrics:
      - name: "streaming_events_published_total"
        type: "counter"
        labels: ["event_type", "status"]
      - name: "streaming_events_consumed_total"
        type: "counter"
        labels: ["event_type", "subscriber"]
      - name: "streaming_connections_active"
        type: "gauge"
        labels: ["connection_type"]
      - name: "streaming_batch_size"
        type: "histogram"
        buckets: [1, 5, 10, 25, 50, 100]
    alerts:
      - name: "StreamingHighEventLoss"
        condition: "rate(streaming_events_published_total{status='failed'}[5m]) > 0.05"
        severity: "critical"
        description: "High event loss rate in streaming service"
      - name: "StreamingConnectionSpike"
        condition: "streaming_connections_active > 800"
        severity: "warning"
        description: "Unusually high number of streaming connections"
```

### Deployment Commands

```bash
# Deploy external API services with Docker Compose
docker-compose -f docker-compose.external-api.yml up -d

# Deploy to Kubernetes
kubectl apply -f k8s/external-api-deployment.yaml

# Scale external API services
kubectl scale deployment agent-hive-webhook-server --replicas=3 -n agent-hive
kubectl scale deployment agent-hive-api-gateway --replicas=3 -n agent-hive
kubectl scale deployment agent-hive-event-streaming --replicas=2 -n agent-hive

# Health check all external API services
curl -f http://localhost:8081/health  # Webhook server
curl -f http://localhost:8082/health  # API gateway
curl -f http://localhost:8083/health  # Event streaming

# Test external API endpoints
curl -X POST http://localhost:8081/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"action": "push", "repository": {"name": "test"}}'

curl -X GET http://localhost:8082/api/v1/agents \
  -H "Authorization: Bearer your-jwt-token"

# Test event streaming
curl -X POST http://localhost:8083/events \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{"type": "test_event", "data": {"message": "Hello World"}}'
```

## Production Environment Setup

### Environment Configuration

#### Production Configuration Template

```yaml
# .claude/config/config.production.yaml
system:
  log_level: INFO
  debug_mode: false
  max_concurrent_tasks: 100

# Multi-agent production settings
multi_agent:
  enabled: true
  max_agents: 50
  min_agents: 10
  load_balancing_strategy: "predictive"
  health_check_interval: 15
  failure_threshold: 3
  coordination_timeout: 30

# Resource management for production
resources:
  monitoring:
    cpu: true
    memory: true
    disk: true
    network: true
    interval_seconds: 5
  
  allocation:
    cpu_limit_percent: 85
    memory_limit_percent: 80
    disk_limit_percent: 90
    
  thresholds:
    warning: 75
    critical: 90

# Production scaling configuration
scaling:
  enabled: true
  auto_scale: true
  strategies:
    scale_up:
      threshold: 0.75
      factor: 1.3
      max_instances: 50
    scale_down:
      threshold: 0.25
      factor: 0.8
      min_instances: 10
  cooldown_minutes: 3

# Agent types for production
agents:
  backend:
    max_instances: 20
    capabilities: ["python", "api", "database", "microservices"]
    resource_requirements:
      cpu_cores: 2
      memory_mb: 2048
      disk_mb: 1024
  
  frontend:
    max_instances: 15
    capabilities: ["javascript", "typescript", "react", "vue", "ui"]
    resource_requirements:
      cpu_cores: 1
      memory_mb: 1024
      disk_mb: 512
      
  ios:
    max_instances: 10
    capabilities: ["swift", "mobile", "ui", "app_store"]
    resource_requirements:
      cpu_cores: 4
      memory_mb: 4096
      disk_mb: 2048
      
  infrastructure:
    max_instances: 8
    capabilities: ["docker", "kubernetes", "terraform", "monitoring"]
    resource_requirements:
      cpu_cores: 2
      memory_mb: 2048
      disk_mb: 1024

# External API Integration for production
external_api:
  enabled: true
  
  # Intelligence Framework settings
  intelligence_framework:
    enabled: true
    confidence_threshold: 0.85
    learning_rate: 0.005
    pattern_recognition_enabled: true
    adaptive_learning_enabled: true
    performance_tracking_enabled: true
    
  # Task allocation settings
  intelligent_task_allocation:
    enabled: true
    load_balancing_strategy: "performance_weighted"
    allocation_timeout: 60
    performance_tracking_enabled: true
    
  # Agent coordination settings
  agent_coordination:
    enabled: true
    session_timeout: 600
    max_participants: 10
    consensus_threshold: 0.7
    
  # Performance monitoring settings
  performance_monitoring:
    enabled: true
    monitoring_interval: 30
    optimization_enabled: true
    alert_thresholds:
      cpu_usage: 0.85
      memory_usage: 0.90
      task_queue_length: 100
      
  # Webhook server configuration
  webhook_server:
    enabled: true
    port: 8081
    host: "0.0.0.0"
    rate_limit_per_minute: 200
    authentication_required: true
    cors_origins: ["https://yourdomain.com", "https://app.yourdomain.com"]
    max_payload_size: "10MB"
    request_timeout: 60
    
  # API gateway configuration
  api_gateway:
    enabled: true
    port: 8082
    cors_enabled: true
    cors_origins: ["https://yourdomain.com"]
    cors_methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers: ["Content-Type", "Authorization", "X-API-Key"]
    authentication_provider: "jwt"
    request_timeout: 60
    max_request_size: "50MB"
    rate_limit_per_minute: 500
    
  # Event streaming configuration
  event_streaming:
    enabled: true
    port: 8083
    compression_enabled: true
    compression_algorithm: "gzip"
    batch_size: 50
    flush_interval: 3.0
    max_connections: 2000
    heartbeat_interval: 60
    event_retention_hours: 24
    
  # Enhanced ML systems
  ml_enhancements:
    pattern_optimizer:
      enabled: true
      pattern_detection_sensitivity: 0.8
      optimization_aggressiveness: 0.6
      learning_window_size: 5000
      
    predictive_analytics:
      enabled: true
      prediction_accuracy_threshold: 0.9
      forecast_horizon_days: 60
      model_update_frequency: "daily"
      
    adaptive_learning:
      enabled: true
      learning_rate: 0.005
      adaptation_threshold: 0.15
      model_update_frequency: "hourly"

# Production database settings
database:
  connection_pool_size: 20
  max_overflow: 30
  pool_timeout: 30
  pool_recycle: 3600
  echo: false

# Logging configuration
logging:
  level: INFO
  format: json
  handlers:
    - console
    - file
    - syslog
  file:
    path: /app/logs/orchestrator.log
    max_size: 100MB
    backup_count: 10
  syslog:
    facility: local0
    address: ['localhost', 514]

# Monitoring and metrics
monitoring:
  enabled: true
  metrics_port: 8081
  health_check_port: 8080
  prometheus:
    enabled: true
    path: /metrics
  alerts:
    enabled: true
    webhook_url: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
```

#### Environment Variables

```bash
# Production environment variables
export LEANVIBE_SYSTEM_LOG_LEVEL=INFO
export LEANVIBE_SYSTEM_DEBUG_MODE=false

# Multi-agent settings
export LEANVIBE_MULTI_AGENT_MAX_AGENTS=50
export LEANVIBE_MULTI_AGENT_LOAD_BALANCING_STRATEGY=predictive

# Resource limits
export LEANVIBE_RESOURCES_CPU_LIMIT_PERCENT=85
export LEANVIBE_RESOURCES_MEMORY_LIMIT_PERCENT=80

# Database settings
export LEANVIBE_DATABASE_URL=postgresql://user:pass@db:5432/agent_hive
export LEANVIBE_DATABASE_POOL_SIZE=20

# Security settings
export LEANVIBE_SECURITY_SECRET_KEY=your-secret-key-here
export LEANVIBE_SECURITY_API_KEY=your-api-key-here

# External service URLs
export CLAUDE_API_URL=https://api.anthropic.com
export GEMINI_API_URL=https://generativelanguage.googleapis.com

# External API Integration settings
export LEANVIBE_EXTERNAL_API_ENABLED=true

# Intelligence Framework settings
export LEANVIBE_INTELLIGENCE_FRAMEWORK_ENABLED=true
export LEANVIBE_INTELLIGENCE_FRAMEWORK_CONFIDENCE_THRESHOLD=0.85
export LEANVIBE_INTELLIGENCE_FRAMEWORK_LEARNING_RATE=0.005

# Task allocation settings
export LEANVIBE_INTELLIGENT_TASK_ALLOCATION_ENABLED=true
export LEANVIBE_INTELLIGENT_TASK_ALLOCATION_STRATEGY=performance_weighted
export LEANVIBE_INTELLIGENT_TASK_ALLOCATION_TIMEOUT=60

# Agent coordination settings
export LEANVIBE_AGENT_COORDINATION_ENABLED=true
export LEANVIBE_AGENT_COORDINATION_SESSION_TIMEOUT=600
export LEANVIBE_AGENT_COORDINATION_MAX_PARTICIPANTS=10

# Performance monitoring settings
export LEANVIBE_PERFORMANCE_MONITORING_ENABLED=true
export LEANVIBE_PERFORMANCE_MONITORING_INTERVAL=30
export LEANVIBE_PERFORMANCE_MONITORING_OPTIMIZATION_ENABLED=true

# Webhook server settings
export LEANVIBE_WEBHOOK_SERVER_ENABLED=true
export LEANVIBE_WEBHOOK_SERVER_PORT=8081
export LEANVIBE_WEBHOOK_SERVER_HOST=0.0.0.0
export LEANVIBE_WEBHOOK_SERVER_RATE_LIMIT=200
export LEANVIBE_WEBHOOK_SERVER_AUTH_REQUIRED=true

# API gateway settings
export LEANVIBE_API_GATEWAY_ENABLED=true
export LEANVIBE_API_GATEWAY_PORT=8082
export LEANVIBE_API_GATEWAY_CORS_ENABLED=true
export LEANVIBE_API_GATEWAY_AUTH_PROVIDER=jwt
export LEANVIBE_API_GATEWAY_REQUEST_TIMEOUT=60
export LEANVIBE_API_GATEWAY_RATE_LIMIT=500

# Event streaming settings
export LEANVIBE_EVENT_STREAMING_ENABLED=true
export LEANVIBE_EVENT_STREAMING_PORT=8083
export LEANVIBE_EVENT_STREAMING_COMPRESSION_ENABLED=true
export LEANVIBE_EVENT_STREAMING_BATCH_SIZE=50
export LEANVIBE_EVENT_STREAMING_MAX_CONNECTIONS=2000

# Enhanced ML systems settings
export LEANVIBE_ML_PATTERN_OPTIMIZER_ENABLED=true
export LEANVIBE_ML_PATTERN_OPTIMIZER_SENSITIVITY=0.8
export LEANVIBE_ML_PREDICTIVE_ANALYTICS_ENABLED=true
export LEANVIBE_ML_PREDICTIVE_ANALYTICS_THRESHOLD=0.9
export LEANVIBE_ML_ADAPTIVE_LEARNING_ENABLED=true
export LEANVIBE_ML_ADAPTIVE_LEARNING_RATE=0.005
```

### Performance Tuning

#### System Optimization

```bash
# Linux system tuning for high performance
# /etc/sysctl.conf additions

# Network optimization
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 16384 16777216
net.ipv4.tcp_wmem = 4096 16384 16777216

# File descriptor limits
fs.file-max = 1000000

# Memory optimization
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
```

#### Application Tuning

```python
# Production performance settings
import asyncio
import gc

# Optimize asyncio event loop
asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())  # Windows
# OR
asyncio.set_event_loop_policy(asyncio.UnixDefaultEventLoopPolicy())     # Unix/Linux

# Garbage collection optimization
gc.set_threshold(700, 10, 10)

# Python optimization
import sys
sys.dont_write_bytecode = True  # Reduce I/O in containerized environments
```

## Security Considerations

### Authentication and Authorization

#### API Security

```python
# Security configuration
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

app = FastAPI()
security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token for API access."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=["HS256"]
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.get("/orchestrator/status")
async def get_status(current_user: str = Depends(verify_token)):
    """Get orchestrator status (authenticated endpoint)."""
    # Implementation
    pass
```

#### Network Security

```yaml
# Network policies for Kubernetes
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: agent-hive-network-policy
  namespace: agent-hive
spec:
  podSelector:
    matchLabels:
      app: agent-hive
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 443  # HTTPS
    - protocol: TCP
      port: 53   # DNS
    - protocol: UDP
      port: 53   # DNS
```

### Secrets Management

#### Kubernetes Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: agent-hive-secrets
  namespace: agent-hive
type: Opaque
data:
  secret-key: <base64-encoded-secret>
  api-key: <base64-encoded-api-key>
  database-password: <base64-encoded-password>
```

#### External Secrets Integration

```yaml
# external-secrets.yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-backend
  namespace: agent-hive
spec:
  provider:
    vault:
      server: "https://vault.example.com"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "agent-hive"
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: agent-hive-external-secrets
  namespace: agent-hive
spec:
  refreshInterval: 15s
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: agent-hive-secrets
    creationPolicy: Owner
  data:
  - secretKey: secret-key
    remoteRef:
      key: agent-hive
      property: secret_key
```

### Security Hardening

#### Container Security

```dockerfile
# Security-hardened Dockerfile
FROM python:3.12-slim

# Install security updates
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        curl \
        sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with minimal privileges
RUN groupadd -r -g 1001 agent-hive \
    && useradd -r -g agent-hive -u 1001 -m -d /app agent-hive

# Set secure file permissions
COPY --chown=agent-hive:agent-hive . /app
WORKDIR /app

# Remove unnecessary files
RUN find /app -name "*.pyc" -delete \
    && find /app -name "__pycache__" -delete

# Switch to non-root user
USER 1001:1001

# Security labels
LABEL security.contact="security@leanvibe.com"
LABEL security.scan-policy="scan-on-build"
```

## Monitoring and Observability

### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "agent_hive_rules.yml"

scrape_configs:
  - job_name: 'agent-hive'
    static_configs:
      - targets: ['agent-hive:8081']
    metrics_path: /metrics
    scrape_interval: 10s
    
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
```

### Grafana Dashboards

```json
{
  "dashboard": {
    "title": "LeanVibe Agent Hive - Production Dashboard",
    "panels": [
      {
        "title": "Agent Coordination Latency",
        "type": "graph",
        "targets": [
          {
            "expr": "agent_hive_coordination_latency_ms"
          }
        ],
        "yAxes": [
          {
            "label": "Milliseconds",
            "max": 500
          }
        ]
      },
      {
        "title": "Resource Utilization",
        "type": "singlestat",
        "targets": [
          {
            "expr": "agent_hive_resource_utilization_percent"
          }
        ],
        "thresholds": "75,90"
      },
      {
        "title": "Active Agents",
        "type": "graph",
        "targets": [
          {
            "expr": "agent_hive_active_agents_total"
          }
        ]
      },
      {
        "title": "Task Throughput",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(agent_hive_tasks_completed_total[5m])"
          }
        ]
      }
    ]
  }
}
```

### Custom Metrics

```python
# Prometheus metrics integration
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Define custom metrics
COORDINATION_LATENCY = Histogram(
    'agent_hive_coordination_latency_seconds',
    'Time spent coordinating agents',
    buckets=(0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float('inf'))
)

ACTIVE_AGENTS = Gauge(
    'agent_hive_active_agents_total',
    'Number of active agents'
)

TASKS_COMPLETED = Counter(
    'agent_hive_tasks_completed_total',
    'Total number of completed tasks',
    ['agent_type', 'status']
)

RESOURCE_UTILIZATION = Gauge(
    'agent_hive_resource_utilization_percent',
    'Current resource utilization percentage'
)

# Instrument code
@COORDINATION_LATENCY.time()
async def coordinate_agents(self, tasks):
    # Implementation
    pass

def update_metrics(self):
    """Update Prometheus metrics."""
    ACTIVE_AGENTS.set(len(self.active_agents))
    RESOURCE_UTILIZATION.set(self.get_resource_utilization())
```

### Alerting Rules

```yaml
# monitoring/agent_hive_rules.yml
groups:
  - name: agent_hive_alerts
    rules:
      - alert: HighCoordinationLatency
        expr: agent_hive_coordination_latency_ms > 500
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Agent coordination latency is high"
          description: "Coordination latency has been above 500ms for more than 2 minutes"
          
      - alert: LowResourceUtilization
        expr: agent_hive_resource_utilization_percent < 30
        for: 5m
        labels:
          severity: info
        annotations:
          summary: "Resource utilization is low"
          description: "System may be over-provisioned"
          
      - alert: AgentFailure
        expr: increase(agent_hive_agent_failures_total[5m]) > 5
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Multiple agent failures detected"
          description: "{{ $value }} agent failures in the last 5 minutes"
          
      - alert: SystemOverload
        expr: agent_hive_resource_utilization_percent > 90
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "System resource utilization critical"
          description: "Resource utilization has been above 90% for more than 1 minute"
```

## Scalability and Performance

### Horizontal Scaling

#### Auto-scaling Configuration

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agent-hive-hpa
  namespace: agent-hive
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agent-hive-orchestrator
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: agent_hive_coordination_latency_ms
      target:
        type: AverageValue
        averageValue: 300m
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 25
        periodSeconds: 60
```

#### Cluster Auto-scaling

```yaml
# cluster-autoscaler.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  template:
    spec:
      containers:
      - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.21.0
        name: cluster-autoscaler
        command:
        - ./cluster-autoscaler
        - --v=4
        - --stderrthreshold=info
        - --cloud-provider=aws
        - --skip-nodes-with-local-storage=false
        - --expander=least-waste
        - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/agent-hive
        - --balance-similar-node-groups
        - --scale-down-enabled=true
        - --scale-down-delay-after-add=10m
        - --scale-down-unneeded-time=10m
```

### Performance Optimization

#### Database Optimization

```python
# Database connection pooling and optimization
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

# SQLite optimizations for single-instance deployments
def optimize_sqlite(connection):
    """Apply SQLite performance optimizations."""
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA cache_size=10000")
    connection.execute("PRAGMA temp_store=MEMORY")
    connection.execute("PRAGMA mmap_size=268435456")  # 256MB
```

#### Caching Strategy

```python
# Redis caching for improved performance
import redis
import json
from typing import Optional, Any

class CacheManager:
    """Production-ready caching manager."""
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        try:
            value = self.redis.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None
            
    async def set(self, key: str, value: Any, ttl: int = 300):
        """Set cached value with TTL."""
        try:
            self.redis.setex(key, ttl, json.dumps(value))
        except Exception:
            pass  # Graceful degradation
            
    async def invalidate_pattern(self, pattern: str):
        """Invalidate cache keys matching pattern."""
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)
```

## Backup and Recovery

### Data Backup Strategy

#### Database Backup

```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/app/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATABASE_FILE="/app/data/agent_hive.db"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# SQLite backup
sqlite3 "$DATABASE_FILE" ".backup $BACKUP_DIR/agent_hive_$TIMESTAMP.db"

# Compress backup
gzip "$BACKUP_DIR/agent_hive_$TIMESTAMP.db"

# Upload to cloud storage (example with AWS S3)
aws s3 cp "$BACKUP_DIR/agent_hive_$TIMESTAMP.db.gz" "s3://agent-hive-backups/database/"

# Clean up old local backups (keep last 7 days)
find "$BACKUP_DIR" -name "agent_hive_*.db.gz" -mtime +7 -delete

echo "Database backup completed: agent_hive_$TIMESTAMP.db.gz"
```

#### Configuration Backup

```bash
#!/bin/bash
# backup_config.sh

BACKUP_DIR="/app/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CONFIG_DIR="/app/.claude/config"

# Create backup
tar -czf "$BACKUP_DIR/config_$TIMESTAMP.tar.gz" -C "$CONFIG_DIR" .

# Upload to cloud storage
aws s3 cp "$BACKUP_DIR/config_$TIMESTAMP.tar.gz" "s3://agent-hive-backups/config/"

echo "Configuration backup completed: config_$TIMESTAMP.tar.gz"
```

### Disaster Recovery

#### Recovery Procedures

```bash
#!/bin/bash
# disaster_recovery.sh

# 1. Restore database
LATEST_DB_BACKUP=$(aws s3 ls s3://agent-hive-backups/database/ | sort | tail -n 1 | awk '{print $4}')
aws s3 cp "s3://agent-hive-backups/database/$LATEST_DB_BACKUP" /tmp/
gunzip "/tmp/$LATEST_DB_BACKUP"
cp "/tmp/${LATEST_DB_BACKUP%.gz}" /app/data/agent_hive.db

# 2. Restore configuration
LATEST_CONFIG_BACKUP=$(aws s3 ls s3://agent-hive-backups/config/ | sort | tail -n 1 | awk '{print $4}')
aws s3 cp "s3://agent-hive-backups/config/$LATEST_CONFIG_BACKUP" /tmp/
tar -xzf "/tmp/$LATEST_CONFIG_BACKUP" -C /app/.claude/config/

# 3. Restart services
kubectl rollout restart deployment/agent-hive-orchestrator -n agent-hive

echo "Disaster recovery completed"
```

#### Health Verification

```python
# health_verification.py
async def verify_system_health():
    """Comprehensive health verification after recovery."""
    
    health_checks = []
    
    # Database connectivity
    try:
        config = ConfigLoader()
        health_checks.append(("Database", "OK"))
    except Exception as e:
        health_checks.append(("Database", f"FAILED: {e}"))
    
    # Agent coordination
    try:
        coordinator = MultiAgentCoordinator()
        status = await coordinator.get_status()
        health_checks.append(("Coordination", "OK"))
    except Exception as e:
        health_checks.append(("Coordination", f"FAILED: {e}"))
    
    # Resource management
    try:
        resource_manager = ResourceManager()
        resources = await resource_manager.get_system_resources()
        health_checks.append(("Resources", "OK"))
    except Exception as e:
        health_checks.append(("Resources", f"FAILED: {e}"))
    
    return health_checks
```

## CI/CD Pipeline

**📋 Comprehensive Guide Available**: See [CI/CD Operations Guide](docs/guides/cicd-operations.md) for complete pipeline setup, quality gates, security scanning, and deployment automation.

### Quick CI/CD Overview

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]
    tags: ['v*']

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: leanvibe/agent-hive

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
        
    - name: Install UV
      run: |
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source ~/.bashrc
        
    - name: Install dependencies
      run: uv sync
      
    - name: Run tests
      run: uv run pytest --cov=.claude --cov-report=xml
      
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    outputs:
      image: ${{ steps.image.outputs.image }}
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
      
    - name: Log in to registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
        
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=semver,pattern={{version}}
          type=semver,pattern={{major}}.{{minor}}
          
    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        context: .
        platforms: linux/amd64,linux/arm64
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
        
    - name: Output image
      id: image
      run: echo "image=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.meta.outputs.version }}" >> $GITHUB_OUTPUT

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up kubectl
      uses: azure/setup-kubectl@v3
      
    - name: Configure kubectl
      run: |
        echo "${{ secrets.KUBECONFIG }}" | base64 -d > /tmp/kubeconfig
        export KUBECONFIG=/tmp/kubeconfig
        
    - name: Deploy to Kubernetes
      run: |
        sed -i 's|image: leanvibe/agent-hive:latest|image: ${{ needs.build.outputs.image }}|' k8s/deployment.yaml
        kubectl apply -f k8s/
        kubectl rollout status deployment/agent-hive-orchestrator -n agent-hive --timeout=300s
        
    - name: Verify deployment
      run: |
        kubectl get pods -n agent-hive
        kubectl logs -n agent-hive -l app=agent-hive --tail=50
```

### Deployment Validation

```python
# deployment_validation.py
import asyncio
import aiohttp
import time

async def validate_deployment(base_url: str, timeout: int = 300):
    """Validate deployment health and readiness."""
    
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        while time.time() - start_time < timeout:
            try:
                # Health check
                async with session.get(f"{base_url}/health") as response:
                    if response.status == 200:
                        health_data = await response.json()
                        print(f"✅ Health check passed: {health_data}")
                        
                        # Readiness check
                        async with session.get(f"{base_url}/ready") as ready_response:
                            if ready_response.status == 200:
                                ready_data = await ready_response.json()
                                print(f"✅ Readiness check passed: {ready_data}")
                                
                                # Performance validation
                                if ready_data.get('coordination_latency_ms', 0) < 500:
                                    print("✅ Deployment validation successful")
                                    return True
                                    
            except Exception as e:
                print(f"⏳ Waiting for deployment: {e}")
                
            await asyncio.sleep(10)
    
    print("❌ Deployment validation failed")
    return False

if __name__ == "__main__":
    asyncio.run(validate_deployment("https://agent-hive.example.com"))
```

## Troubleshooting Production Issues

### Common Production Problems

#### High Memory Usage

```bash
# Investigate memory usage
kubectl top pods -n agent-hive
kubectl describe pod <pod-name> -n agent-hive

# Check for memory leaks
kubectl exec -it <pod-name> -n agent-hive -- python -c "
import gc
import psutil
import os

process = psutil.Process(os.getpid())
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB')
print(f'Open files: {process.num_fds()}')
print(f'Threads: {process.num_threads()}')

# Force garbage collection
gc.collect()
print('Garbage collection completed')
"
```

#### Database Performance Issues

```bash
# Check database performance
kubectl exec -it <pod-name> -n agent-hive -- sqlite3 /app/data/agent_hive.db -cmd "
.timer on
.explain query plan SELECT * FROM tasks WHERE status = 'pending';
EXPLAIN QUERY PLAN SELECT * FROM tasks WHERE status = 'pending';
"

# Optimize database
kubectl exec -it <pod-name> -n agent-hive -- sqlite3 /app/data/agent_hive.db -cmd "
VACUUM;
REINDEX;
ANALYZE;
PRAGMA optimize;
"
```

#### Agent Coordination Failures

```bash
# Check coordination status
kubectl exec -it <pod-name> -n agent-hive -- python -c "
from claude.advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
coordinator = MultiAgentCoordinator()
status = coordinator.get_status()
print(f'Total agents: {status.total_agents}')
print(f'Healthy agents: {status.healthy_agents}')
print(f'Performance score: {status.performance_score}')

# List unhealthy agents
for agent_id in coordinator.get_unhealthy_agents():
    agent_status = coordinator.get_agent_status(agent_id)
    print(f'Unhealthy agent {agent_id}: {agent_status.status}')
"

# Restart coordination
kubectl exec -it <pod-name> -n agent-hive -- python -c "
from claude.advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
coordinator = MultiAgentCoordinator()
coordinator.reset_all_agents()
print('Coordination reset completed')
"
```

#### External API Integration Issues

```bash
# Check webhook server status
curl -f http://localhost:8081/health || echo "Webhook server down"
kubectl logs -n agent-hive -l component=webhook-server --tail=50

# Check API gateway status
curl -f http://localhost:8082/health || echo "API gateway down"
kubectl logs -n agent-hive -l component=api-gateway --tail=50

# Check event streaming status
curl -f http://localhost:8083/health || echo "Event streaming down"
kubectl logs -n agent-hive -l component=event-streaming --tail=50

# Test webhook endpoint functionality
curl -X POST http://localhost:8081/webhooks/test \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key" \
  -d '{"test": "webhook"}' \
  --max-time 10

# Test API gateway functionality
curl -X GET http://localhost:8082/api/v1/status \
  -H "Authorization: Bearer test-token" \
  --max-time 10

# Test event streaming functionality
curl -X POST http://localhost:8083/events \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{"type": "test", "data": {"message": "test"}}' \
  --max-time 10

# Check external API service resources
kubectl top pods -n agent-hive -l component=webhook-server
kubectl top pods -n agent-hive -l component=api-gateway
kubectl top pods -n agent-hive -l component=event-streaming

# Check external API service connectivity
kubectl exec -it <webhook-pod> -n agent-hive -- netstat -tlnp
kubectl exec -it <gateway-pod> -n agent-hive -- netstat -tlnp
kubectl exec -it <streaming-pod> -n agent-hive -- netstat -tlnp
```

#### Intelligence Framework Debugging

```bash
# Check intelligence framework status
kubectl exec -it <pod-name> -n agent-hive -- python -c "
from intelligence_framework import IntelligenceFramework
from intelligence_framework.models import IntelligenceConfig

config = IntelligenceConfig()
framework = IntelligenceFramework(config)

# Test decision making
decision = framework.make_decision(
    context={'task_type': 'test', 'complexity': 'low'},
    options=[{'approach': 'test', 'confidence': 0.9}]
)
print(f'Decision made: {decision}')

# Check learning status
insights = framework.get_learning_insights(time_period='last_hour')
print(f'Learning insights: {insights}')
"

# Check task allocation status
kubectl exec -it <pod-name> -n agent-hive -- python -c "
from intelligent_task_allocation import IntelligentTaskAllocator
from intelligent_task_allocation.models import AllocationConfig

config = AllocationConfig()
allocator = IntelligentTaskAllocator(config)

# Test task allocation
allocation = allocator.allocate_task(
    task={'type': 'test', 'complexity': 5},
    available_agents=['test_agent_1', 'test_agent_2']
)
print(f'Task allocation: {allocation}')

# Check agent performance profiles
for agent_id in ['test_agent_1', 'test_agent_2']:
    profile = allocator.get_agent_profile(agent_id)
    print(f'Agent {agent_id} profile: {profile}')
"

# Check performance monitoring
kubectl exec -it <pod-name> -n agent-hive -- python -c "
from performance_monitoring_optimization import PerformanceMonitoringOptimization
from performance_monitoring_optimization.models import MonitoringConfig

config = MonitoringConfig()
monitor = PerformanceMonitoringOptimization(config)

# Get current metrics
metrics = monitor.get_current_metrics()
print(f'Performance metrics: {metrics}')

# Check optimization recommendations
recommendations = monitor.get_optimization_recommendations()
print(f'Optimization recommendations: {recommendations}')
"
```

#### ML Enhancement Systems Debugging

```bash
# Check pattern optimizer status
kubectl exec -it <pod-name> -n agent-hive -- python -c "
from ml_enhancements import PatternOptimizer
from ml_enhancements.models import MLConfig

config = MLConfig()
optimizer = PatternOptimizer(config)

# Test pattern analysis
patterns = optimizer.analyze_patterns(
    data_source='test_data',
    time_window='last_hour'
)
print(f'Pattern analysis: {patterns}')
"

# Check predictive analytics status
kubectl exec -it <pod-name> -n agent-hive -- python -c "
from ml_enhancements import PredictiveAnalytics

analytics = PredictiveAnalytics()

# Test performance prediction
prediction = analytics.predict_performance(
    task_type='test',
    context={'complexity': 'medium'},
    forecast_horizon='1_hour'
)
print(f'Performance prediction: {prediction}')
"

# Check adaptive learning status
kubectl exec -it <pod-name> -n agent-hive -- python -c "
from ml_enhancements import AdaptiveLearning

learning = AdaptiveLearning()

# Check learning insights
insights = learning.get_learning_insights(
    time_period='last_hour',
    focus_areas=['performance', 'optimization']
)
print(f'Learning insights: {insights}')

# Check model performance
evaluation = learning.evaluate_model_performance()
print(f'Model evaluation: {evaluation}')
"
```

#### External API Rate Limiting Issues

```bash
# Check rate limiting status
curl -I http://localhost:8081/webhooks/test
curl -I http://localhost:8082/api/v1/status
curl -I http://localhost:8083/events

# Check Redis rate limiting backend
kubectl exec -it <redis-pod> -n agent-hive -- redis-cli info keyspace
kubectl exec -it <redis-pod> -n agent-hive -- redis-cli keys "rate_limit:*"

# Reset rate limiting for specific client
kubectl exec -it <redis-pod> -n agent-hive -- redis-cli del "rate_limit:client_ip:192.168.1.100"

# Check rate limiting configuration
kubectl exec -it <webhook-pod> -n agent-hive -- python -c "
import os
print(f'Rate limit: {os.getenv(\"LEANVIBE_WEBHOOK_SERVER_RATE_LIMIT\", \"default\")}')
print(f'Auth required: {os.getenv(\"LEANVIBE_WEBHOOK_SERVER_AUTH_REQUIRED\", \"default\")}')
"
```

#### External API Security Issues

```bash
# Check authentication status
curl -X POST http://localhost:8081/webhooks/test \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}' \
  -w "HTTP Status: %{http_code}\n"

# Test with valid API key
curl -X POST http://localhost:8081/webhooks/test \
  -H "Content-Type: application/json" \
  -H "X-API-Key: valid-key" \
  -d '{"test": "data"}' \
  -w "HTTP Status: %{http_code}\n"

# Check CORS configuration
curl -X OPTIONS http://localhost:8082/api/v1/status \
  -H "Origin: https://example.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type,Authorization" \
  -v

# Check JWT token validation
curl -X GET http://localhost:8082/api/v1/agents \
  -H "Authorization: Bearer invalid-token" \
  -w "HTTP Status: %{http_code}\n"

# Check SSL/TLS configuration
openssl s_client -connect localhost:8081 -servername localhost -verify_hostname
openssl s_client -connect localhost:8082 -servername localhost -verify_hostname
```

### Emergency Procedures

#### System Recovery

```bash
#!/bin/bash
# emergency_recovery.sh

echo "Starting emergency recovery procedure..."

# 1. Scale down to single instance
kubectl scale deployment agent-hive-orchestrator --replicas=1 -n agent-hive

# 2. Wait for scale down
kubectl rollout status deployment/agent-hive-orchestrator -n agent-hive --timeout=120s

# 3. Clear cache and temporary data
kubectl exec -it $(kubectl get pods -n agent-hive -l app=agent-hive -o jsonpath='{.items[0].metadata.name}') -n agent-hive -- sh -c "
rm -rf /tmp/*
find /app/logs -name '*.log' -mtime +1 -delete
"

# 4. Restart with fresh configuration
kubectl rollout restart deployment/agent-hive-orchestrator -n agent-hive

# 5. Scale back up gradually
sleep 60
kubectl scale deployment agent-hive-orchestrator --replicas=3 -n agent-hive

echo "Emergency recovery completed"
```

---

**Deployment Guide Version**: Phase 2.0  
**Last Updated**: July 14, 2025  
**Status**: Production-ready for Phase 1-2 | Ready for Phase 2.2-2.5 deployment enhancements

This deployment guide covers comprehensive production deployment strategies from single-instance to large-scale distributed environments. Regular updates will be provided as new features and deployment patterns are developed.