# LeanVibe Agent Hive - Configuration Management

Comprehensive configuration management system for handling environment-specific settings, deployment configurations, and operational parameters across development, staging, and production environments.

## Overview

The configuration management system provides:
- **Environment-specific configurations** with inheritance from base settings
- **Template-based generation** for Docker Compose and Kubernetes manifests
- **Configuration validation** to ensure consistency and correctness
- **Automated configuration generation** for different deployment targets

## Directory Structure

```
config/
├── base.yaml                          # Base configuration (shared across environments)
├── environments/                      # Environment-specific configurations
│   ├── development.yaml              # Development environment overrides
│   ├── staging.yaml                  # Staging environment overrides
│   └── production.yaml               # Production environment overrides
├── templates/                        # Configuration templates
│   ├── docker-compose.yml.template  # Docker Compose template
│   └── k8s-configmap.yaml.template  # Kubernetes ConfigMap template
├── scripts/                          # Configuration management tools
│   ├── config-manager.py            # Main configuration management script
│   └── validate-config.sh           # Configuration validation script
├── generated/                        # Auto-generated configurations (git-ignored)
└── README.md                         # This file
```

## Configuration Hierarchy

The configuration system uses a hierarchical approach:

1. **Base Configuration** (`base.yaml`): Common settings shared across all environments
2. **Environment Configuration** (`environments/{env}.yaml`): Environment-specific overrides
3. **Merged Configuration**: Runtime combination of base + environment settings

### Base Configuration

Contains default values for:
- Application metadata (name, version, description)
- Server settings (ports, workers, timeouts)
- Database and cache configurations
- Security settings (CORS, JWT, rate limiting)
- Logging configuration
- Monitoring and health check settings
- Agent coordination parameters

### Environment-Specific Configurations

#### Development (`development.yaml`)
- Debug mode enabled
- Reduced resource limits
- Local database connections
- Relaxed security settings
- Detailed logging
- Hot reload enabled

#### Staging (`staging.yaml`)
- Production-like settings
- Testing features enabled
- Moderate resource allocation
- Staging-specific endpoints
- Enhanced monitoring

#### Production (`production.yaml`)
- Optimized for performance
- Maximum security settings
- High resource allocation
- Audit logging enabled
- Comprehensive monitoring
- Backup and disaster recovery

## Usage

### Configuration Management Script

The `config-manager.py` script provides comprehensive configuration management:

```bash
# List available environments
python3 config/scripts/config-manager.py list

# Validate configuration for specific environment
python3 config/scripts/config-manager.py validate -e development

# Generate all configuration files for environment
python3 config/scripts/config-manager.py generate -e production

# Export merged configuration
python3 config/scripts/config-manager.py export -e staging -f yaml
python3 config/scripts/config-manager.py export -e staging -f json -o staging-config.json
```

### Configuration Validation

Validate configurations for all environments:

```bash
# Validate all environments
./config/scripts/validate-config.sh

# Validate specific environment
./config/scripts/validate-config.sh production
```

### Generated Configurations

The system generates deployment-ready configurations:

```bash
# Generate configurations for development
python3 config/scripts/config-manager.py generate -e development

# Generated files:
# - config/generated/docker-compose.development.yml
# - config/generated/configmap.development.yaml
# - config/generated/config.development.yaml
```

## Configuration Examples

### Server Configuration

```yaml
# Base configuration
server:
  host: "0.0.0.0"
  ports:
    main: 8000
    webhook: 8080
    gateway: 8081
  workers: 4
  max_connections: 100

# Development override
server:
  workers: 2
  max_connections: 50
  reload: true

# Production override
server:
  workers: 8
  max_connections: 200
  worker_class: "uvicorn.workers.UvicornWorker"
```

### Database Configuration

```yaml
# Base configuration
database:
  type: "postgresql"
  host: "postgres-service"
  port: 5432
  pool_size: 20

# Development override
database:
  host: "localhost"
  name: "agent_hive_dev"
  echo: true  # Enable SQL logging

# Production override
database:
  pool_size: 50
  max_overflow: 100
  pool_pre_ping: true
```

### Security Configuration

```yaml
# Base configuration
security:
  jwt:
    algorithm: "HS256"
    expire_minutes: 1440
  cors:
    allow_credentials: true

# Development override
security:
  cors:
    allow_origins: ["*"]
  rate_limiting:
    requests_per_minute: 1000

# Production override
security:
  cors:
    allow_origins:
      - "https://agent-hive.yourdomain.com"
      - "https://api.agent-hive.yourdomain.com"
  rate_limiting:
    requests_per_minute: 100
```

## Template System

### Docker Compose Template

The Docker Compose template generates environment-specific compose files:

```yaml
# Template variables are replaced based on configuration
services:
  agent-hive:
    environment:
      - LEANVIBE_ENVIRONMENT={{ENVIRONMENT}}
      - LEANVIBE_LOG_LEVEL={{LOG_LEVEL}}
      - WORKERS={{SERVER_WORKERS}}
```

### Kubernetes ConfigMap Template

Generates Kubernetes ConfigMaps with environment-specific values:

```yaml
data:
  LEANVIBE_ENVIRONMENT: "{{ENVIRONMENT}}"
  WORKERS: "{{SERVER_WORKERS}}"
  MAX_CONNECTIONS: "{{SERVER_MAX_CONNECTIONS}}"
```

## Configuration Validation

The validation system checks:

1. **YAML Syntax**: Ensures all configuration files are valid YAML
2. **Required Fields**: Validates presence of mandatory configuration sections
3. **Type Checking**: Verifies data types for configuration values
4. **Environment Rules**: Ensures environment-specific requirements are met
5. **Template Generation**: Tests that templates can be generated successfully

### Validation Rules

#### Development Environment
- Debug mode must be enabled
- Relaxed security settings allowed
- Local database connections preferred

#### Production Environment
- Debug mode must be disabled
- Strict security settings required
- CORS origins must be explicitly configured
- Backup and monitoring must be enabled

#### Staging Environment
- Testing mode should be enabled
- Production-like security settings
- Monitoring enabled for validation

## Integration with Deployment

### Docker Compose Integration

```bash
# Generate and use Docker Compose configuration
python3 config/scripts/config-manager.py generate -e development
docker-compose -f config/generated/docker-compose.development.yml up
```

### Kubernetes Integration

```bash
# Generate Kubernetes ConfigMap
python3 config/scripts/config-manager.py generate -e production

# Apply to cluster
kubectl apply -f config/generated/configmap.production.yaml
```

### CI/CD Integration

Add to your CI/CD pipeline:

```yaml
# Example GitHub Actions step
- name: Validate Configuration
  run: ./config/scripts/validate-config.sh

- name: Generate Production Config
  run: python3 config/scripts/config-manager.py generate -e production
```

## Environment Variables

Configuration values can be overridden using environment variables:

```bash
# Override database host
export LEANVIBE_DATABASE_HOST="custom-postgres-host"

# Override log level
export LEANVIBE_LOG_LEVEL="DEBUG"

# Override server workers
export WORKERS="16"
```

Environment variable naming convention:
- Prefix: `LEANVIBE_` (optional for some values)
- Nested values: Use underscores (`DATABASE_HOST`)
- All uppercase

## Security Considerations

### Secrets Management

**Never store secrets in configuration files!**

Instead, use:
- Kubernetes Secrets for sensitive values
- Environment variables for runtime secrets
- External secret management systems (Vault, AWS Secrets Manager)

```yaml
# ❌ Don't do this
database:
  password: "my-secret-password"

# ✅ Do this instead
database:
  password: "${DATABASE_PASSWORD}"  # From environment variable
```

### Production Security

Production configurations enforce:
- Disabled debug mode
- Restricted CORS origins
- Rate limiting enabled
- Security headers configured
- Audit logging enabled

## Troubleshooting

### Common Issues

1. **Validation Fails**
   ```bash
   # Check YAML syntax
   python3 -c "import yaml; yaml.safe_load(open('config/environments/production.yaml'))"
   
   # Run specific validation
   python3 config/scripts/config-manager.py validate -e production
   ```

2. **Template Generation Fails**
   ```bash
   # Check template syntax
   python3 config/scripts/config-manager.py generate -e development
   
   # Check missing variables
   grep -r "{{" config/templates/
   ```

3. **Missing Configuration Values**
   ```bash
   # Export merged configuration to debug
   python3 config/scripts/config-manager.py export -e production -f yaml
   ```

### Debugging Commands

```bash
# List all available environments
python3 config/scripts/config-manager.py list

# Export configuration for debugging
python3 config/scripts/config-manager.py export -e development

# Validate specific environment
./config/scripts/validate-config.sh staging

# Check generated files
ls -la config/generated/
```

## Best Practices

1. **Keep Base Configuration Minimal**: Only include truly common settings
2. **Use Environment Overrides**: Leverage inheritance for environment-specific changes
3. **Validate Early**: Run validation in development and CI/CD pipelines
4. **Document Changes**: Update this README when adding new configuration options
5. **Version Control**: Track configuration changes carefully
6. **Test Configurations**: Generate and test configurations before deployment
7. **Security First**: Never commit secrets, use environment variables instead

## Future Enhancements

1. **Configuration Schema**: JSON Schema validation for configurations
2. **Secret Integration**: Direct integration with secret management systems
3. **Configuration UI**: Web interface for configuration management
4. **A/B Testing**: Support for feature flag configurations
5. **Configuration Drift Detection**: Monitor live vs. configured settings
6. **Automated Rollback**: Configuration version management and rollback capabilities

## Contributing

When adding new configuration options:

1. Add to `base.yaml` with sensible defaults
2. Add environment-specific overrides as needed
3. Update validation rules in `config-manager.py`
4. Update templates if needed
5. Document the new options in this README
6. Test with all environments