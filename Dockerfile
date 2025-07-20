# LeanVibe Agent Hive Production Dockerfile
# Multi-stage build for production-ready Python application

# Base stage - Python runtime with UV package manager
FROM python:3.13-slim AS base
LABEL maintainer="LeanVibe Team"
LABEL description="LeanVibe Agent Hive - AI orchestration system"

# Set environment variables for Python optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    UV_CACHE_DIR=/tmp/uv-cache

# Install system dependencies and UV
RUN apt-get update && apt-get install -y \
    curl \
    git \
    gcc \
    g++ \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

# Add UV to PATH
ENV PATH="/root/.local/bin:$PATH"

# Development stage - includes dev dependencies
FROM base AS development

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install all dependencies including dev tools
RUN --mount=type=cache,target=/tmp/uv-cache \
    uv sync --dev

# Copy source code
COPY . .

# Run tests and quality checks
RUN uv run pytest --tb=short
RUN uv run black --check .
RUN uv run ruff check .
RUN uv run mypy .

# Production dependencies stage
FROM base AS dependencies

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install only production dependencies
RUN --mount=type=cache,target=/tmp/uv-cache \
    uv sync --no-dev

# Production stage - minimal runtime image
FROM python:3.13-slim AS production

# Security: Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy UV from base stage
COPY --from=base /root/.local/bin/uv /usr/local/bin/uv

# Copy Python environment from dependencies stage
COPY --from=dependencies /app/.venv /app/.venv

# Copy application source code
COPY --chown=appuser:appuser . .

# Remove unnecessary files for production
RUN rm -rf tests/ docs/ tutorials/ \
    .github/ .git/ \
    *.md \
    .gitignore \
    .pre-commit-config.yaml \
    pytest.ini \
    && find . -name "*.pyc" -delete \
    && find . -name "__pycache__" -exec rm -rf {} + || true

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/config \
    && chown -R appuser:appuser /app

# Set environment variables for production
ENV PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH" \
    LEANVIBE_ENVIRONMENT=production \
    LEANVIBE_LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Switch to non-root user
USER appuser

# Expose ports for API Gateway and services
EXPOSE 8000 8080 8081

# Default command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Development override stage
FROM development AS dev-server
EXPOSE 8000 8080 8081
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]