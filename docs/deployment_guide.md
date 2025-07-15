# Integration Agent Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Integration Agent in various environments, from development to production. The Integration Agent provides external API integration capabilities including GitHub, Slack, and other third-party services.

## Prerequisites

### System Requirements

- **Python**: 3.9 or higher
- **Memory**: Minimum 2GB RAM, recommended 4GB+
- **CPU**: 2+ cores recommended
- **Storage**: 10GB+ available space
- **Network**: Outbound HTTPS access for external APIs

### Dependencies

- `aiohttp` >= 3.8.0
- `asyncio` (built-in)
- `pytest` >= 7.0.0 (for testing)
- `python-dotenv` (for environment management)

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/LeanVibe/agent-hive.git
cd agent-hive
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Development Dependencies (Optional)

```bash
pip install -r requirements-dev.txt
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# API Gateway Configuration
API_GATEWAY_HOST=0.0.0.0
API_GATEWAY_PORT=8080
API_GATEWAY_PREFIX=/api/v1
API_GATEWAY_AUTH_REQUIRED=true
API_GATEWAY_CORS_ENABLED=true

# GitHub Integration
GITHUB_TOKEN=ghp_your_token_here
GITHUB_WEBHOOK_SECRET=your_webhook_secret
GITHUB_DEFAULT_OWNER=your_org
GITHUB_DEFAULT_REPO=your_repo

# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_SIGNING_SECRET=your_signing_secret
SLACK_DEFAULT_CHANNEL=#general

# Service Discovery
SERVICE_DISCOVERY_STRATEGY=dynamic
SERVICE_DISCOVERY_CLEANUP_ENABLED=true
SERVICE_DISCOVERY_CLEANUP_INTERVAL=300
SERVICE_DISCOVERY_TTL=600

# Rate Limiting
RATE_LIMIT_STRATEGY=token_bucket
RATE_LIMIT_DEFAULT_LIMIT=1000
RATE_LIMIT_WINDOW_SIZE=3600
RATE_LIMIT_ADAPTIVE_ENABLED=true

# Monitoring
MONITORING_ENABLED=true
MONITORING_PORT=9090
HEALTH_CHECK_INTERVAL=60

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/integration-agent.log
```

### Configuration Files

#### `config/integration.yaml`

```yaml
integration:
  github:
    token: ${GITHUB_TOKEN}
    webhook_secret: ${GITHUB_WEBHOOK_SECRET}
    default_owner: ${GITHUB_DEFAULT_OWNER}
    default_repo: ${GITHUB_DEFAULT_REPO}
    timeout: 30
    max_retries: 3
    
  slack:
    bot_token: ${SLACK_BOT_TOKEN}
    webhook_url: ${SLACK_WEBHOOK_URL}
    signing_secret: ${SLACK_SIGNING_SECRET}
    default_channel: ${SLACK_DEFAULT_CHANNEL}
    timeout: 30
    max_retries: 3
    
  api_gateway:
    host: ${API_GATEWAY_HOST}
    port: ${API_GATEWAY_PORT}
    api_prefix: ${API_GATEWAY_PREFIX}
    auth_required: ${API_GATEWAY_AUTH_REQUIRED}
    enable_cors: ${API_GATEWAY_CORS_ENABLED}
    cors_origins: ["*"]
    request_timeout: 30
    
  service_discovery:
    strategy: ${SERVICE_DISCOVERY_STRATEGY}
    cleanup_enabled: ${SERVICE_DISCOVERY_CLEANUP_ENABLED}
    cleanup_interval: ${SERVICE_DISCOVERY_CLEANUP_INTERVAL}
    service_ttl: ${SERVICE_DISCOVERY_TTL}
    
  rate_limiting:
    strategy: ${RATE_LIMIT_STRATEGY}
    default_limit: ${RATE_LIMIT_DEFAULT_LIMIT}
    window_size: ${RATE_LIMIT_WINDOW_SIZE}
    enable_adaptive: ${RATE_LIMIT_ADAPTIVE_ENABLED}
    
  monitoring:
    enabled: ${MONITORING_ENABLED}
    port: ${MONITORING_PORT}
    health_check_interval: ${HEALTH_CHECK_INTERVAL}
    
  logging:
    level: ${LOG_LEVEL}
    format: ${LOG_FORMAT}
    file: ${LOG_FILE}
```

## Deployment Options

### 1. Development Deployment

#### Quick Start

```bash
# Install and configure
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration

# Run integration agent
python -m external_api.integration_manager
```

#### With Docker

```bash
# Build image
docker build -t integration-agent .

# Run container
docker run -d \
  --name integration-agent \
  --env-file .env \
  -p 8080:8080 \
  -p 9090:9090 \
  integration-agent
```

### 2. Production Deployment

#### Using Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  integration-agent:
    build: .
    restart: unless-stopped
    environment:
      - API_GATEWAY_HOST=0.0.0.0
      - API_GATEWAY_PORT=8080
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - LOG_LEVEL=INFO
    ports:
      - "8080:8080"
      - "9090:9090"
    volumes:
      - ./logs:/var/log
      - ./config:/app/config
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    depends_on:
      - redis
      - postgres
      
  redis:
    image: redis:alpine
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      
  postgres:
    image: postgres:13
    restart: unless-stopped
    environment:
      - POSTGRES_DB=integration_agent
      - POSTGRES_USER=integration
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - integration-agent

volumes:
  redis_data:
  postgres_data:
```

#### Using Kubernetes

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: integration-agent
  namespace: agent-hive
spec:
  replicas: 3
  selector:
    matchLabels:
      app: integration-agent
  template:
    metadata:
      labels:
        app: integration-agent
    spec:
      containers:
      - name: integration-agent
        image: integration-agent:latest
        ports:
        - containerPort: 8080
        - containerPort: 9090
        env:
        - name: API_GATEWAY_HOST
          value: "0.0.0.0"
        - name: API_GATEWAY_PORT
          value: "8080"
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: integration-secrets
              key: github-token
        - name: SLACK_BOT_TOKEN
          valueFrom:
            secretKeyRef:
              name: integration-secrets
              key: slack-bot-token
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
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: logs
          mountPath: /var/log
      volumes:
      - name: config
        configMap:
          name: integration-config
      - name: logs
        persistentVolumeClaim:
          claimName: integration-logs
---
apiVersion: v1
kind: Service
metadata:
  name: integration-agent-service
  namespace: agent-hive
spec:
  selector:
    app: integration-agent
  ports:
  - name: api
    port: 8080
    targetPort: 8080
  - name: metrics
    port: 9090
    targetPort: 9090
  type: LoadBalancer
```

### 3. Cloud Deployment

#### AWS ECS

Create `aws/task-definition.json`:

```json
{
  "family": "integration-agent",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "integration-agent",
      "image": "your-ecr-repo/integration-agent:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        },
        {
          "containerPort": 9090,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "API_GATEWAY_HOST",
          "value": "0.0.0.0"
        },
        {
          "name": "API_GATEWAY_PORT",
          "value": "8080"
        }
      ],
      "secrets": [
        {
          "name": "GITHUB_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:github-token"
        },
        {
          "name": "SLACK_BOT_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:slack-bot-token"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/integration-agent",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

#### Google Cloud Run

Create `gcp/service.yaml`:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: integration-agent
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/execution-environment: gen2
        run.googleapis.com/cpu-throttling: "false"
    spec:
      containerConcurrency: 1000
      timeoutSeconds: 300
      containers:
      - image: gcr.io/your-project/integration-agent:latest
        ports:
        - containerPort: 8080
        env:
        - name: API_GATEWAY_HOST
          value: "0.0.0.0"
        - name: API_GATEWAY_PORT
          value: "8080"
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: integration-secrets
              key: github-token
        - name: SLACK_BOT_TOKEN
          valueFrom:
            secretKeyRef:
              name: integration-secrets
              key: slack-bot-token
        resources:
          limits:
            cpu: 2000m
            memory: 4Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        startupProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
          failureThreshold: 30
```

## SSL/TLS Configuration

### Using Let's Encrypt with Nginx

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream integration_agent {
        server integration-agent:8080;
    }
    
    server {
        listen 80;
        server_name api.yourdomain.com;
        
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        
        location / {
            return 301 https://$server_name$request_uri;
        }
    }
    
    server {
        listen 443 ssl http2;
        server_name api.yourdomain.com;
        
        ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
        
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
        ssl_prefer_server_ciphers off;
        
        location / {
            proxy_pass http://integration_agent;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

## Monitoring and Logging

### Prometheus Configuration

Create `prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'integration-agent'
    static_configs:
      - targets: ['integration-agent:9090']
    scrape_interval: 5s
    metrics_path: /metrics
    
  - job_name: 'integration-agent-health'
    static_configs:
      - targets: ['integration-agent:8080']
    scrape_interval: 30s
    metrics_path: /health
```

### Grafana Dashboard

Create `grafana/dashboard.json`:

```json
{
  "dashboard": {
    "title": "Integration Agent Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(integration_agent_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, integration_agent_request_duration_seconds_bucket)",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(integration_agent_errors_total[5m])",
            "legendFormat": "Errors/sec"
          }
        ]
      },
      {
        "title": "Service Health",
        "type": "stat",
        "targets": [
          {
            "expr": "integration_agent_service_health",
            "legendFormat": "{{service}}"
          }
        ]
      }
    ]
  }
}
```

### Log Configuration

Create `logging/logging.yaml`:

```yaml
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  json:
    format: '{"timestamp": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: standard
    stream: ext://sys.stdout
    
  file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: json
    filename: /var/log/integration-agent.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
    
  error_file:
    class: logging.handlers.RotatingFileHandler
    level: ERROR
    formatter: json
    filename: /var/log/integration-agent-errors.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

loggers:
  external_api:
    level: INFO
    handlers: [console, file]
    propagate: false
    
  advanced_orchestration:
    level: INFO
    handlers: [console, file]
    propagate: false

root:
  level: INFO
  handlers: [console, file, error_file]
```

## Security Considerations

### API Keys and Secrets

1. **Environment Variables**: Never commit secrets to version control
2. **Secret Management**: Use AWS Secrets Manager, Azure Key Vault, or similar
3. **Token Rotation**: Implement regular token rotation
4. **Least Privilege**: Use minimal required permissions

### Network Security

1. **HTTPS Only**: Always use HTTPS in production
2. **Firewall Rules**: Restrict access to necessary ports only
3. **VPC/Private Networks**: Deploy in private subnets when possible
4. **WAF**: Use Web Application Firewall for external APIs

### Authentication

1. **Multi-Factor Authentication**: Enable MFA for all admin accounts
2. **API Key Management**: Implement proper API key lifecycle management
3. **Rate Limiting**: Configure appropriate rate limits
4. **Request Validation**: Validate all incoming requests

## Backup and Recovery

### Database Backups

```bash
# PostgreSQL backup
pg_dump -h localhost -U integration -d integration_agent > backup.sql

# Restore
psql -h localhost -U integration -d integration_agent < backup.sql
```

### Configuration Backups

```bash
# Backup configuration
tar -czf config-backup-$(date +%Y%m%d).tar.gz config/ .env

# Restore
tar -xzf config-backup-20230715.tar.gz
```

### Disaster Recovery

1. **Regular Backups**: Automate daily backups
2. **Cross-Region Replication**: Use multiple regions for critical data
3. **Recovery Testing**: Regularly test recovery procedures
4. **Documentation**: Maintain updated recovery procedures

## Scaling

### Horizontal Scaling

```yaml
# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: integration-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: integration-agent
  minReplicas: 3
  maxReplicas: 10
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
```

### Load Testing

```bash
# Using Apache Bench
ab -n 1000 -c 10 http://localhost:8080/api/v1/health

# Using Artillery
artillery quick --count 10 --num 100 http://localhost:8080/api/v1/health
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Check what's using the port
   lsof -i :8080
   
   # Kill the process
   kill -9 <PID>
   ```

2. **Memory Issues**
   ```bash
   # Check memory usage
   docker stats integration-agent
   
   # Increase memory limit
   docker run -m 4g integration-agent
   ```

3. **SSL Certificate Issues**
   ```bash
   # Check certificate validity
   openssl x509 -in cert.pem -text -noout
   
   # Renew Let's Encrypt certificate
   certbot renew
   ```

### Debugging Commands

```bash
# Check logs
docker logs integration-agent

# Enter container
docker exec -it integration-agent /bin/bash

# Check configuration
curl http://localhost:8080/config

# Health check
curl http://localhost:8080/health

# Metrics
curl http://localhost:9090/metrics
```

## Maintenance

### Regular Tasks

1. **Update Dependencies**: Monthly security updates
2. **Log Rotation**: Ensure logs don't fill disk
3. **Certificate Renewal**: Automate SSL certificate renewal
4. **Backup Verification**: Test backup integrity
5. **Performance Review**: Monthly performance analysis

### Automated Maintenance

Create `maintenance/update.sh`:

```bash
#!/bin/bash

# Update system packages
apt update && apt upgrade -y

# Update Python packages
pip install --upgrade -r requirements.txt

# Restart services
systemctl restart integration-agent

# Verify health
curl -f http://localhost:8080/health || exit 1

echo "Maintenance completed successfully"
```

## Performance Optimization

### Configuration Tuning

```yaml
# Optimized configuration
api_gateway:
  worker_processes: 4
  keep_alive_timeout: 30
  max_connections: 1000
  
rate_limiting:
  strategy: token_bucket
  burst_capacity: 100
  
service_discovery:
  cache_ttl: 300
  health_check_interval: 30
```

### Database Optimization

```sql
-- Index optimization
CREATE INDEX idx_service_name ON services(name);
CREATE INDEX idx_service_status ON services(status);
CREATE INDEX idx_request_timestamp ON requests(timestamp);

-- Connection pooling
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
```

## Support and Maintenance

### Health Check Endpoints

- `/health` - Basic health check
- `/ready` - Readiness check
- `/metrics` - Prometheus metrics
- `/config` - Configuration status

### Monitoring Alerts

Set up alerts for:
- High error rates (>5%)
- High response times (>1s)
- Service unavailability
- Memory usage (>80%)
- CPU usage (>70%)

### Documentation Updates

Keep the following documentation updated:
- API documentation
- Deployment procedures
- Configuration changes
- Security updates
- Performance tuning

For additional support, contact the development team or refer to the project documentation.