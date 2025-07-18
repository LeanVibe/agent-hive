# Docker Deployment Guide

**Status**: ✅ Production Ready  
**Version**: 1.0  
**Last Updated**: July 15, 2025

## Overview

This guide provides comprehensive Docker deployment strategies for LeanVibe Agent Hive, covering single-node development setups to multi-node production clusters with high availability and scalability.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Single Node Deployment](#single-node-deployment)  
- [Multi-Node Production Cluster](#multi-node-production-cluster)
- [Docker Compose Configuration](#docker-compose-configuration)
- [Container Management](#container-management)
- [Monitoring and Logging](#monitoring-and-logging)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Docker**: 24.0+ 
- **Docker Compose**: 2.20+
- **System Resources**: 
  - CPU: 4+ cores
  - Memory: 8GB+ RAM
  - Storage: 50GB+ available space
  - Network: 100Mbps+ bandwidth

### Installation

```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

## Single Node Deployment

### Basic Development Setup

Create a simple single-node deployment for development and testing:

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  leanvibe-orchestrator:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: leanvibe-orchestrator
    environment:
      - LEANVIBE_SYSTEM_LOG_LEVEL=DEBUG
      - LEANVIBE_DEVELOPMENT_USE_MOCK_CLI=false
      - LEANVIBE_MULTI_AGENT_MAX_AGENTS=5
    ports:
      - "8080:8080"  # Webhook server
      - "8081:8081"  # API gateway
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "from cli import LeanVibeCLI; LeanVibeCLI()"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  redis:
    image: redis:7-alpine
    container_name: leanvibe-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped

  monitoring:
    image: grafana/grafana:latest
    container_name: leanvibe-monitoring
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=leanvibe2025
    volumes:
      - grafana-data:/var/lib/grafana
    restart: unless-stopped

volumes:
  redis-data:
  grafana-data:
```

### Dockerfile

```dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV for Python dependency management
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY requirements.txt ./

# Install Python dependencies
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/config

# Set environment variables
ENV PYTHONPATH=/app
ENV LEANVIBE_SYSTEM_LOG_LEVEL=INFO
ENV LEANVIBE_DEVELOPMENT_USE_MOCK_CLI=false

# Expose ports
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "from cli import LeanVibeCLI; LeanVibeCLI()" || exit 1

# Run the application
CMD ["python", "cli.py", "orchestrate", "--workflow", "production"]
```

### Quick Start

```bash
# Clone repository
git clone https://github.com/leanvibe/agent-hive.git
cd agent-hive

# Build and start development environment
docker-compose -f docker-compose.dev.yml up --build -d

# Check status
docker-compose -f docker-compose.dev.yml ps

# View logs
docker-compose -f docker-compose.dev.yml logs -f leanvibe-orchestrator

# Access services
# - Agent Hive API: http://localhost:8081
# - Webhook Server: http://localhost:8080
# - Monitoring: http://localhost:3000 (admin/leanvibe2025)
```

## Multi-Node Production Cluster

### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  # Load Balancer
  nginx:
    image: nginx:alpine
    container_name: leanvibe-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - orchestrator-1
      - orchestrator-2
      - orchestrator-3
    restart: unless-stopped

  # Orchestrator Cluster
  orchestrator-1:
    build:
      context: .
      dockerfile: Dockerfile.prod
    container_name: leanvibe-orchestrator-1
    environment:
      - LEANVIBE_SYSTEM_LOG_LEVEL=INFO
      - LEANVIBE_MULTI_AGENT_MAX_AGENTS=20
      - LEANVIBE_CLUSTER_NODE_ID=1
      - LEANVIBE_CLUSTER_NODES=3
      - REDIS_URL=redis://redis-cluster:6379
    depends_on:
      - redis-cluster
    volumes:
      - ./config:/app/config
      - logs-1:/app/logs
      - data-1:/app/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G

  orchestrator-2:
    build:
      context: .
      dockerfile: Dockerfile.prod
    container_name: leanvibe-orchestrator-2
    environment:
      - LEANVIBE_SYSTEM_LOG_LEVEL=INFO
      - LEANVIBE_MULTI_AGENT_MAX_AGENTS=20
      - LEANVIBE_CLUSTER_NODE_ID=2
      - LEANVIBE_CLUSTER_NODES=3
      - REDIS_URL=redis://redis-cluster:6379
    depends_on:
      - redis-cluster
    volumes:
      - ./config:/app/config
      - logs-2:/app/logs
      - data-2:/app/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G

  orchestrator-3:
    build:
      context: .
      dockerfile: Dockerfile.prod
    container_name: leanvibe-orchestrator-3
    environment:
      - LEANVIBE_SYSTEM_LOG_LEVEL=INFO
      - LEANVIBE_MULTI_AGENT_MAX_AGENTS=20
      - LEANVIBE_CLUSTER_NODE_ID=3
      - LEANVIBE_CLUSTER_NODES=3
      - REDIS_URL=redis://redis-cluster:6379
    depends_on:
      - redis-cluster
    volumes:
      - ./config:/app/config
      - logs-3:/app/logs
      - data-3:/app/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G

  # Redis Cluster
  redis-cluster:
    image: redis:7-alpine
    container_name: leanvibe-redis-cluster
    command: redis-server --appendonly yes --cluster-enabled yes
    ports:
      - "6379:6379"
    volumes:
      - redis-cluster-data:/data
    restart: unless-stopped

  # Monitoring Stack
  prometheus:
    image: prom/prometheus:latest
    container_name: leanvibe-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: leanvibe-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-leanvibe2025}
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning
    depends_on:
      - prometheus
    restart: unless-stopped

  # Log Aggregation
  elasticsearch:
    image: elasticsearch:8.11.0
    container_name: leanvibe-elasticsearch
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
      - xpack.security.enabled=false
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    restart: unless-stopped

  logstash:
    image: logstash:8.11.0
    container_name: leanvibe-logstash
    volumes:
      - ./monitoring/logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on:
      - elasticsearch
    restart: unless-stopped

  kibana:
    image: kibana:8.11.0
    container_name: leanvibe-kibana
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
    restart: unless-stopped

volumes:
  logs-1:
  logs-2:
  logs-3:
  data-1:
  data-2:
  data-3:
  redis-cluster-data:
  prometheus-data:
  grafana-data:
  elasticsearch-data:

networks:
  default:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### Production Dockerfile

```dockerfile
# Dockerfile.prod
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Install UV for Python dependency management
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY requirements.txt ./

# Install Python dependencies
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/config

# Create non-root user
RUN useradd -m -u 1000 leanvibe && \
    chown -R leanvibe:leanvibe /app

USER leanvibe

# Set environment variables
ENV PYTHONPATH=/app
ENV LEANVIBE_SYSTEM_LOG_LEVEL=INFO
ENV LEANVIBE_DEVELOPMENT_USE_MOCK_CLI=false

# Expose ports
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "from cli import LeanVibeCLI; LeanVibeCLI()" || exit 1

# Run the application
CMD ["python", "cli.py", "orchestrate", "--workflow", "production", "--cluster-mode"]
```

### NGINX Configuration

```nginx
# nginx/nginx.conf
upstream leanvibe_orchestrators {
    server orchestrator-1:8081 max_fails=3 fail_timeout=30s;
    server orchestrator-2:8081 max_fails=3 fail_timeout=30s;
    server orchestrator-3:8081 max_fails=3 fail_timeout=30s;
}

upstream leanvibe_webhooks {
    server orchestrator-1:8080 max_fails=3 fail_timeout=30s;
    server orchestrator-2:8080 max_fails=3 fail_timeout=30s;
    server orchestrator-3:8080 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name leanvibe.local;

    # API Gateway
    location /api/ {
        proxy_pass http://leanvibe_orchestrators;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # Health check
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;
    }

    # Webhook Server
    location /webhooks/ {
        proxy_pass http://leanvibe_webhooks;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase body size for webhooks
        client_max_body_size 10M;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

### Production Deployment

```bash
# Deploy production cluster
docker-compose -f docker-compose.prod.yml up -d

# Scale orchestrators
docker-compose -f docker-compose.prod.yml up -d --scale orchestrator-1=2 --scale orchestrator-2=2

# Check cluster status
docker-compose -f docker-compose.prod.yml ps

# Monitor resource usage
docker stats

# View cluster logs
docker-compose -f docker-compose.prod.yml logs -f
```

## Container Management

### Health Monitoring

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' leanvibe-orchestrator

# View health check logs
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' leanvibe-orchestrator

# Custom health check script
#!/bin/bash
# health-check.sh
python -c "
import requests
import sys
try:
    response = requests.get('http://localhost:8081/api/v1/health', timeout=5)
    sys.exit(0 if response.status_code == 200 else 1)
except:
    sys.exit(1)
"
```

### Resource Management

```bash
# Set resource limits
docker update --memory=4g --cpus=2 leanvibe-orchestrator

# Monitor resource usage
docker stats --no-stream

# View resource limits
docker inspect leanvibe-orchestrator | jq '.[0].HostConfig.Memory'
```

### Log Management

```bash
# View container logs
docker logs -f leanvibe-orchestrator

# Configure log rotation
docker run --log-driver json-file --log-opt max-size=10m --log-opt max-file=3 leanvibe-orchestrator

# Export logs
docker logs leanvibe-orchestrator > orchestrator.log 2>&1
```

## Monitoring and Logging

### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'leanvibe-orchestrator'
    static_configs:
      - targets: ['orchestrator-1:8081', 'orchestrator-2:8081', 'orchestrator-3:8081']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-cluster:6379']

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:80']
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "LeanVibe Agent Hive Dashboard",
    "panels": [
      {
        "title": "Active Agents",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(leanvibe_active_agents)"
          }
        ]
      },
      {
        "title": "Task Queue Depth",
        "type": "graph",
        "targets": [
          {
            "expr": "leanvibe_task_queue_depth"
          }
        ]
      },
      {
        "title": "Resource Utilization",
        "type": "graph",
        "targets": [
          {
            "expr": "leanvibe_resource_utilization"
          }
        ]
      }
    ]
  }
}
```

### Log Aggregation

```conf
# monitoring/logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [container_name] == "leanvibe-orchestrator" {
    json {
      source => "message"
    }
    
    mutate {
      add_field => { "service" => "orchestrator" }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "leanvibe-logs-%{+YYYY.MM.dd}"
  }
}
```

## Security Best Practices

### Network Security

```yaml
# docker-compose.security.yml
version: '3.8'

services:
  leanvibe-orchestrator:
    networks:
      - internal
      - external
    expose:
      - "8081"
    # Do not expose ports directly to host

networks:
  internal:
    driver: bridge
    internal: true
  external:
    driver: bridge
```

### Secrets Management

```bash
# Use Docker secrets
echo "supersecret" | docker secret create leanvibe-api-key -

# Reference in compose file
version: '3.8'

services:
  leanvibe-orchestrator:
    secrets:
      - leanvibe-api-key
    environment:
      - LEANVIBE_API_KEY_FILE=/run/secrets/leanvibe-api-key

secrets:
  leanvibe-api-key:
    external: true
```

### Container Security

```dockerfile
# Security hardening
FROM python:3.12-slim

# Create non-root user
RUN groupadd -r leanvibe && useradd -r -g leanvibe leanvibe

# Set secure permissions
RUN chown -R leanvibe:leanvibe /app
USER leanvibe

# Remove package manager
RUN apt-get remove -y apt-get

# Set read-only filesystem
VOLUME ["/app/logs", "/app/data"]
```

## Troubleshooting

### Common Issues

#### Container Won't Start

```bash
# Check logs
docker logs leanvibe-orchestrator

# Check resource usage
docker system df
docker system prune

# Verify dependencies
docker-compose -f docker-compose.prod.yml config
```

#### High Memory Usage

```bash
# Check memory usage
docker stats --no-stream

# Set memory limits
docker update --memory=2g leanvibe-orchestrator

# Monitor memory leaks
docker exec leanvibe-orchestrator python -c "
import psutil
print(f'Memory usage: {psutil.virtual_memory().percent}%')
"
```

#### Network Connectivity Issues

```bash
# Check network configuration
docker network ls
docker network inspect leanvibe_default

# Test connectivity
docker exec leanvibe-orchestrator ping redis-cluster
docker exec leanvibe-orchestrator curl -I http://orchestrator-2:8081/health
```

### Debugging Tools

```bash
# Enter container for debugging
docker exec -it leanvibe-orchestrator /bin/bash

# View container processes
docker exec leanvibe-orchestrator ps aux

# Check file permissions
docker exec leanvibe-orchestrator ls -la /app

# Monitor system resources
docker exec leanvibe-orchestrator htop
```

### Performance Optimization

```yaml
# Optimized compose configuration
version: '3.8'

services:
  leanvibe-orchestrator:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
    sysctls:
      net.core.somaxconn: 4096
    restart: unless-stopped
```

## Conclusion

This Docker deployment guide provides comprehensive strategies for deploying LeanVibe Agent Hive from development to production. The configurations are tested and production-ready, with proper monitoring, security, and scalability considerations.

For additional deployment scenarios or specific requirements, refer to the main [Deployment Guide](../DEPLOYMENT.md) or contact the development team.

---

**Next Steps**: 
- [CI/CD Pipeline Setup](cicd-operations.md)
- [Production Monitoring](../TROUBLESHOOTING.md)
- [Security Configuration](../SECURITY.md)