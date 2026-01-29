# Agent Hive - Deployment Checklist

**Generated:** 2026-01-20T02:50:44.233420
**Project:** Agent Hive
**Location:** `leanvibe-dev/agent-hive/`

---

## Pre-Deployment Requirements

### Infrastructure
- [ ] **PostgreSQL Database** - Version 14+ recommended
- [ ] **Redis** - Version 6+ for caching and queues
- [ ] **Docker & Docker Compose** - For containerized deployment
- [ ] **Domain/Subdomain** - For API access (e.g., `api.agenthive.com`)

### Environment Variables
- [ ] **Database Connection** - `DATABASE_URL` or `POSTGRES_URL`
- [ ] **Redis Connection** - `REDIS_URL`
- [ ] **API Keys** - Anthropic/OpenAI for AI agents
- [ ] **JWT Secret** - For authentication
- [ ] **Environment** - `ENV=production`

### Configuration Files
- [ ] Review `config/base.yaml`
- [ ] Review `config/environments/production.yaml`
- [ ] Review `docker-compose.yml`
- [ ] Review `.env.example` for required variables

---

## Deployment Steps

### Step 1: Infrastructure Setup
```bash
# Start infrastructure services
docker-compose up -d postgres redis

# Verify services are running
docker-compose ps
```

### Step 2: Database Setup
```bash
# Run migrations (if applicable)
# Check for alembic or migration scripts
# Example: alembic upgrade head
```

### Step 3: Application Deployment
```bash
# Build production image
docker-compose build agent-hive

# Start application
docker-compose up -d agent-hive

# Or use Makefile
make up
```

### Step 4: Health Checks
```bash
# Check health endpoint
curl http://localhost:8000/health

# Check all services
make health
```

---

## Post-Deployment Verification

### Health Endpoints
- [ ] **API Health:** `GET /health` returns 200
- [ ] **Service Discovery:** Verify service registration
- [ ] **API Gateway:** Verify routing works
- [ ] **Database:** Verify connectivity
- [ ] **Redis:** Verify connectivity

### Functional Tests
- [ ] **Multi-Agent Coordination:** Test agent orchestration
- [ ] **Service Discovery:** Test service registration/discovery
- [ ] **API Gateway:** Test API routing and auth
- [ ] **Performance Monitoring:** Verify metrics collection

### Monitoring Setup
- [ ] **Logs:** Configure log aggregation
- [ ] **Metrics:** Set up Prometheus/Grafana (if applicable)
- [ ] **Alerts:** Configure alerting rules
- [ ] **Dashboards:** Set up monitoring dashboards

---

## Rollback Procedures

If deployment fails:
1. Stop new deployment: `docker-compose down`
2. Restore previous version: `git checkout <previous-tag>`
3. Rebuild and deploy: `docker-compose up -d`
4. Verify health: `make health`

---

## Environment Variables Reference

Based on `.env.example` and configuration files:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/agenthive
POSTGRES_URL=postgresql://user:pass@host:5432/agenthive

# Redis
REDIS_URL=redis://host:6379/0

# API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# JWT
JWT_SECRET=your-secret-key-here

# Environment
ENV=production
LOG_LEVEL=INFO
```

---

## Service URLs (Default)

- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/health
- **Dashboard:** http://localhost:8000/dashboard (if applicable)

---

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Verify DATABASE_URL is correct
   - Check PostgreSQL is running
   - Verify network connectivity

2. **Redis Connection Failed**
   - Verify REDIS_URL is correct
   - Check Redis is running
   - Verify network connectivity

3. **Services Not Starting**
   - Check logs: `docker-compose logs`
   - Verify environment variables
   - Check port conflicts

---

**Last Updated:** 2026-01-20T02:50:44.233422
