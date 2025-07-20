# LeanVibe Agent Hive Infrastructure Makefile
# Production infrastructure management commands

.PHONY: help build up down dev logs clean test deploy health

# Default target
help: ## Show this help message
	@echo "LeanVibe Agent Hive Infrastructure Commands"
	@echo "==========================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development commands
dev: ## Start development environment
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

dev-detached: ## Start development environment in background
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

dev-logs: ## Show development logs
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# Production commands
build: ## Build production images
	docker-compose build --no-cache

up: ## Start production environment
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

# Monitoring and debugging
logs: ## Show logs for all services
	docker-compose logs -f

logs-app: ## Show application logs only
	docker-compose logs -f agent-hive

health: ## Check health of all services
	@echo "Checking service health..."
	@docker-compose ps
	@echo ""
	@echo "Health checks:"
	@curl -s http://localhost:8000/health || echo "❌ Agent Hive API not responding"
	@curl -s http://localhost:9090/-/healthy || echo "❌ Prometheus not responding"
	@curl -s http://localhost:3000/api/health || echo "❌ Grafana not responding"

status: ## Show status of all containers
	docker-compose ps

# Database operations
db-init: ## Initialize database with schema
	docker-compose exec postgres psql -U postgres -d agent_hive -f /docker-entrypoint-initdb.d/init.sql

db-shell: ## Connect to database shell
	docker-compose exec postgres psql -U postgres -d agent_hive

# Testing
test: ## Run tests in production environment
	docker-compose exec agent-hive uv run pytest

test-build: ## Test build process
	docker build --target production -t leanvibe-agent-hive:test .
	docker run --rm leanvibe-agent-hive:test python -c "import sys; print('✅ Production build successful')"

# Maintenance and cleanup
clean: ## Remove all containers, volumes, and images
	docker-compose down -v --remove-orphans
	docker system prune -f
	docker volume prune -f

clean-volumes: ## Remove all volumes (WARNING: destroys data)
	docker-compose down -v
	docker volume rm $$(docker volume ls -q | grep leanvibe) 2>/dev/null || true

reset: clean build up ## Complete reset: clean, build, and restart

# Security and updates
security-scan: ## Run security scan on images
	docker scout cves leanvibe-agent-hive:latest || echo "Docker Scout not available"

update-deps: ## Update dependencies in containers
	docker-compose exec agent-hive uv sync

# Production deployment
deploy: ## Deploy to production (requires environment setup)
	@echo "🚀 Deploying to production..."
	@make build
	@make test-build
	@make up
	@make health
	@echo "✅ Deployment complete"

# Backup and restore
backup: ## Backup database and volumes
	@echo "📦 Creating backup..."
	@mkdir -p backups
	@docker-compose exec postgres pg_dump -U postgres agent_hive > backups/db_backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database backup created"

# Monitoring shortcuts
metrics: ## Open Prometheus metrics
	@echo "📊 Opening Prometheus at http://localhost:9090"
	@open http://localhost:9090 || echo "Open http://localhost:9090 manually"

dashboard: ## Open Grafana dashboard
	@echo "📈 Opening Grafana at http://localhost:3000"
	@echo "Default credentials: admin/admin"
	@open http://localhost:3000 || echo "Open http://localhost:3000 manually"

traces: ## Open Jaeger tracing UI
	@echo "🔍 Opening Jaeger at http://localhost:16686"
	@open http://localhost:16686 || echo "Open http://localhost:16686 manually"

# SSL certificate management
ssl-generate: ## Generate SSL certificates for development
	cd infrastructure/nginx && ./generate-ssl.sh

# Quick access
shell: ## Get shell access to main container
	docker-compose exec agent-hive /bin/bash

redis-cli: ## Connect to Redis CLI
	docker-compose exec redis redis-cli

# Performance testing
load-test: ## Run basic load test (requires curl)
	@echo "🔥 Running basic load test..."
	@for i in {1..100}; do curl -s http://localhost:8000/health > /dev/null && echo -n "."; done
	@echo ""
	@echo "✅ Load test complete"

# Documentation
docs: ## Generate infrastructure documentation
	@echo "📚 Infrastructure setup complete!"
	@echo ""
	@echo "🔗 Service URLs:"
	@echo "  • Main API:      http://localhost:8000"
	@echo "  • Webhook:       http://localhost:8080"
	@echo "  • API Gateway:   http://localhost:8081"
	@echo "  • Prometheus:    http://localhost:9090"
	@echo "  • Grafana:       http://localhost:3000 (admin/admin)"
	@echo "  • Jaeger:        http://localhost:16686"
	@echo ""
	@echo "🐳 Docker Commands:"
	@echo "  make dev         - Start development environment"
	@echo "  make up          - Start production environment"
	@echo "  make logs        - View logs"
	@echo "  make health      - Check service health"
	@echo "  make clean       - Clean up everything"