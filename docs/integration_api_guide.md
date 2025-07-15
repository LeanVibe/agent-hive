# Integration Agent API Documentation

## Overview

The Integration Agent provides a comprehensive API layer for external service integration, including GitHub, Slack, and other third-party services. This documentation covers all available endpoints, authentication methods, and usage examples.

## Table of Contents

1. [Authentication](#authentication)
2. [API Gateway](#api-gateway)
3. [Service Discovery](#service-discovery)
4. [GitHub Integration](#github-integration)
5. [Slack Integration](#slack-integration)
6. [Rate Limiting](#rate-limiting)
7. [Usage Examples](#usage-examples)
8. [Error Handling](#error-handling)
9. [Monitoring](#monitoring)

## Authentication

### Supported Authentication Methods

The Integration Agent supports multiple authentication methods:

#### 1. API Key Authentication
```bash
curl -H "X-API-Key: your_api_key" \
     -H "Content-Type: application/json" \
     https://api.agent-hive.com/v1/integrations
```

#### 2. JWT Token Authentication
```bash
curl -H "Authorization: Bearer your_jwt_token" \
     -H "Content-Type: application/json" \
     https://api.agent-hive.com/v1/integrations
```

#### 3. Request Signature Authentication
```bash
curl -H "X-Client-ID: your_client_id" \
     -H "X-Signature: your_request_signature" \
     -H "Content-Type: application/json" \
     https://api.agent-hive.com/v1/integrations
```

### Creating API Keys

```python
from external_api.auth_middleware import AuthenticationMiddleware
from external_api.auth_middleware import Permission

# Initialize auth middleware
auth_config = {
    "enabled_methods": ["api_key"],
    "max_auth_attempts": 5,
    "auth_window_minutes": 15
}
auth_middleware = AuthenticationMiddleware(auth_config)

# Create API key
api_key = auth_middleware.create_api_key(
    user_id="user_123",
    permissions=[Permission.READ, Permission.WRITE],
    expires_in_hours=24
)
```

## API Gateway

### Configuration

```python
from external_api.api_gateway import ApiGateway
from external_api.models import ApiGatewayConfig

# Configure API Gateway
config = ApiGatewayConfig(
    host="0.0.0.0",
    port=8080,
    api_prefix="/api/v1",
    auth_required=True,
    enable_cors=True,
    cors_origins=["*"],
    rate_limit_requests=1000,
    rate_limit_window=3600,
    request_timeout=30
)

# Initialize gateway
gateway = ApiGateway(config)
await gateway.start_server()
```

### Route Registration

```python
# Register unversioned route
async def get_status(request):
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

gateway.register_route("/status", "GET", get_status)

# Register versioned route
async def get_status_v2(request):
    return {
        "status": "healthy",
        "version": "2.0",
        "timestamp": datetime.now().isoformat(),
        "uptime": gateway.get_uptime()
    }

gateway.register_route("/status", "GET", get_status_v2, version="v2")
```

### Service Registration

```python
# Register service with load balancing
gateway.register_service("user_service", ["user_agent_1", "user_agent_2"])

# Select agent for service
selected_agent = await gateway.select_agent_for_service("user_service")
```

## Service Discovery

### Configuration

```python
from external_api.service_discovery import ServiceDiscovery, ServiceInfo, ServiceStatus

# Configure service discovery
discovery_config = {
    "strategy": "dynamic",
    "cleanup_enabled": True,
    "cleanup_interval": 300,
    "service_ttl": 600
}

discovery = ServiceDiscovery(discovery_config)
await discovery.start()
```

### Service Registration

```python
# Register a service
service_info = ServiceInfo(
    service_id="payment_service_1",
    service_name="payment_service",
    service_type="api",
    host="payment.internal",
    port=8080,
    endpoints=["/payments", "/refunds"],
    metadata={"version": "1.2.3", "region": "us-east-1"},
    tags=["payment", "financial", "critical"],
    status=ServiceStatus.HEALTHY
)

await discovery.register_service(service_info)
```

### Service Discovery

```python
# Discover services by name
services = await discovery.discover_services(
    service_name="payment_service",
    status=ServiceStatus.HEALTHY
)

# Discover services by type
api_services = await discovery.discover_services(
    service_type="api",
    tags=["critical"]
)
```

### Health Monitoring

```python
from external_api.service_discovery import HealthCheckConfig

# Configure health checks
health_config = HealthCheckConfig(
    enabled=True,
    interval=30,
    timeout=5,
    retries=3,
    endpoint="/health"
)

await discovery.register_service(service_info, health_config)
```

## GitHub Integration

### Configuration

```python
from external_api.github_client import GitHubClient, GitHubConfig

# Configure GitHub client
github_config = GitHubConfig(
    token="ghp_your_token_here",
    webhook_secret="your_webhook_secret",
    default_owner="your_org",
    default_repo="your_repo"
)

github_client = GitHubClient(github_config)
```

### Repository Operations

```python
# Get repository information
async with github_client:
    repo_info = await github_client.get_repository("owner", "repo")
    print(f"Repository: {repo_info['full_name']}")
    print(f"Stars: {repo_info['stargazers_count']}")
    
    # List repositories
    repos = await github_client.list_repositories("owner")
    
    # Create new repository
    new_repo = await github_client.create_repository(
        name="new_project",
        description="A new project created via API",
        private=False
    )
```

### Issue Management

```python
# Create an issue
issue = await github_client.create_issue(
    owner="owner",
    repo="repo",
    title="Bug: API returns 500 error",
    body="The API endpoint returns 500 when processing large requests.",
    labels=["bug", "high-priority"],
    assignees=["developer1"]
)

# Get issue details
issue_details = await github_client.get_issue("owner", "repo", issue["number"])

# Update issue
updated_issue = await github_client.update_issue(
    owner="owner",
    repo="repo",
    issue_number=issue["number"],
    state="closed",
    labels=["bug", "resolved"]
)

# Add comment to issue
comment = await github_client.add_issue_comment(
    owner="owner",
    repo="repo",
    issue_number=issue["number"],
    body="Fixed in commit abc123"
)
```

### Pull Request Management

```python
# Create pull request
pr = await github_client.create_pull_request(
    owner="owner",
    repo="repo",
    title="Feature: Add new API endpoint",
    head="feature/new-endpoint",
    base="main",
    body="This PR adds a new API endpoint for user management."
)

# List pull requests
open_prs = await github_client.list_pull_requests("owner", "repo", state="open")

# Merge pull request
merge_result = await github_client.merge_pull_request(
    owner="owner",
    repo="repo",
    pr_number=pr["number"],
    commit_title="Merge feature/new-endpoint",
    merge_method="squash"
)
```

### Webhook Handling

```python
# Register webhook event handler
def handle_push_event(event):
    payload = event.payload
    commits = payload.get("commits", [])
    print(f"Received {len(commits)} commits")

github_client.register_webhook_handler(GitHubEventType.PUSH, handle_push_event)

# Process webhook event
headers = {
    "x-github-event": "push",
    "x-github-delivery": "12345-67890",
    "x-hub-signature-256": "sha256=signature"
}
payload = b'{"ref": "refs/heads/main", "commits": [...]}'

event = await github_client.process_webhook_event(headers, payload)
```

## Slack Integration

### Configuration

```python
from external_api.slack_client import SlackClient, SlackConfig

# Configure Slack client
slack_config = SlackConfig(
    bot_token="xoxb-your-bot-token",
    webhook_url="https://hooks.slack.com/services/...",
    signing_secret="your_signing_secret",
    default_channel="#general"
)

slack_client = SlackClient(slack_config)
```

### Messaging

```python
# Send simple message
async with slack_client:
    message = await slack_client.send_message(
        channel="#general",
        text="Hello from Agent Hive!"
    )
    
    # Send formatted message
    formatted_msg = await slack_client.send_formatted_message(
        channel="#alerts",
        title="System Alert",
        message="High CPU usage detected on server-01",
        color="warning",
        fields=[
            {"title": "CPU Usage", "value": "85%", "short": True},
            {"title": "Memory Usage", "value": "67%", "short": True}
        ]
    )
    
    # Send notification
    notification = await slack_client.send_notification(
        message="Deployment completed successfully",
        channel="#deployments",
        level="success"
    )
```

### Advanced Messaging

```python
# Send message with blocks
blocks = [
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "New deployment ready for approval"
        }
    },
    {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Approve"},
                "style": "primary",
                "action_id": "approve_deployment"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Reject"},
                "style": "danger",
                "action_id": "reject_deployment"
            }
        ]
    }
]

await slack_client.send_message("#deployments", "", blocks=blocks)
```

### Event Handling

```python
# Register event handlers
async def handle_message(event):
    event_data = event.event_data
    user = event_data.get("user")
    text = event_data.get("text")
    print(f"User {user} said: {text}")

async def handle_mention(event):
    event_data = event.event_data
    channel = event_data.get("channel")
    await slack_client.send_message(
        channel,
        "Hello! How can I help you today?"
    )

slack_client.register_event_handler(SlackEventType.MESSAGE, handle_message)
slack_client.register_event_handler(SlackEventType.APP_MENTION, handle_mention)
```

## Rate Limiting

### Configuration

```python
from external_api.rate_limiter import AdvancedRateLimiter, RateLimitStrategy

# Configure rate limiter
rate_config = {
    "strategy": "token_bucket",
    "default_limit": 1000,
    "window_size": 3600,
    "enable_adaptive": True
}

rate_limiter = AdvancedRateLimiter(rate_config)
```

### Custom Rate Limits

```python
# Set custom rate limit for specific client
rate_limiter.set_client_limit("user_123", 5000, RateLimitStrategy.SLIDING_WINDOW)

# Add client to bypass list
rate_limiter.add_bypass_client("admin_client")

# Check rate limit
result = await rate_limiter.check_rate_limit(request)
if not result.allowed:
    print(f"Rate limit exceeded. Retry after {result.retry_after} seconds")
```

## Usage Examples

### Complete Integration Setup

```python
import asyncio
from external_api.integration_manager import IntegrationManager, IntegrationConfig
from external_api.github_client import GitHubConfig
from external_api.slack_client import SlackConfig

async def main():
    # Configure integrations
    github_config = GitHubConfig(
        token="your_github_token",
        webhook_secret="your_webhook_secret"
    )
    
    slack_config = SlackConfig(
        bot_token="your_slack_bot_token",
        default_channel="#general"
    )
    
    integration_config = IntegrationConfig(
        github=github_config,
        slack=slack_config,
        notification_channels=["slack:#alerts"]
    )
    
    # Initialize integration manager
    manager = IntegrationManager(integration_config)
    
    # Register event handlers
    async def handle_github_pr(event):
        pr_data = event.payload.get("pull_request", {})
        await manager.send_notification(
            f"New PR opened: {pr_data.get('title')}",
            level="info"
        )
    
    manager.register_event_handler("github_pull_request", handle_github_pr)
    
    # Start integration manager
    await manager.start()
    
    # Send test notification
    await manager.send_notification(
        "Integration system started successfully",
        level="success"
    )
    
    # Get integration status
    status = manager.get_integration_status()
    print(f"Integration status: {status}")
    
    # Keep running
    await asyncio.sleep(3600)  # Run for 1 hour
    
    # Stop integration manager
    await manager.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### API Gateway with Custom Middleware

```python
from external_api.api_gateway import ApiGateway
from external_api.models import ApiGatewayConfig

async def logging_middleware(request):
    print(f"Request: {request.method} {request.path}")
    return {"continue": True}

async def cors_middleware(request):
    if request.method == "OPTIONS":
        return {
            "stop_processing": True,
            "status_code": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE"
            }
        }
    return {"continue": True}

# Setup API Gateway
config = ApiGatewayConfig(host="0.0.0.0", port=8080)
gateway = ApiGateway(config)

# Add middleware
gateway.add_middleware(logging_middleware)
gateway.add_middleware(cors_middleware)

# Register routes
async def health_check(request):
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

gateway.register_route("/health", "GET", health_check)

# Start server
await gateway.start_server()
```

## Error Handling

### Common Error Responses

```json
{
    "error": "Authentication failed",
    "error_code": "AUTH_001",
    "request_id": "req_123456",
    "timestamp": "2023-07-15T10:30:00Z",
    "details": {
        "message": "Invalid API key provided",
        "documentation_url": "https://docs.agent-hive.com/auth"
    }
}
```

### Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| AUTH_001 | Invalid authentication credentials | 401 |
| AUTH_002 | Authentication token expired | 401 |
| RATE_001 | Rate limit exceeded | 429 |
| RATE_002 | Rate limit quota exhausted | 429 |
| SERV_001 | Service not found | 404 |
| SERV_002 | Service unhealthy | 503 |
| GITHUB_001 | GitHub API error | 502 |
| SLACK_001 | Slack API error | 502 |

### Error Handling Example

```python
from external_api.github_client import GitHubAPIError

try:
    repo = await github_client.get_repository("owner", "repo")
except GitHubAPIError as e:
    if e.status_code == 404:
        print("Repository not found")
    elif e.status_code == 403:
        print("Rate limit exceeded")
    else:
        print(f"API error: {e.message}")
```

## Monitoring

### Health Checks

```python
# API Gateway health check
gateway_health = await gateway.health_check()
print(f"Gateway status: {gateway_health['status']}")

# Service discovery health check
discovery_health = await discovery.health_check()
print(f"Discovery status: {discovery_health['status']}")

# GitHub client health check
github_health = await github_client.health_check()
print(f"GitHub status: {github_health['status']}")

# Slack client health check
slack_health = await slack_client.health_check()
print(f"Slack status: {slack_health['status']}")
```

### Metrics Collection

```python
# Get API Gateway metrics
gateway_info = gateway.get_gateway_info()
print(f"Total requests: {gateway_info['total_requests']}")
print(f"Rate limiting stats: {gateway_info['rate_limiting']}")

# Get service discovery metrics
discovery_stats = discovery.get_discovery_stats()
print(f"Total services: {discovery_stats['total_services']}")
print(f"Healthy services: {discovery_stats['healthy_services']}")

# Get GitHub client stats
github_stats = github_client.get_client_stats()
print(f"GitHub requests: {github_stats['stats']['total_requests']}")
print(f"Rate limit remaining: {github_stats['rate_limit']['remaining']}")
```

### Monitoring Endpoints

```python
# Register monitoring endpoints
async def metrics_handler(request):
    return {
        "gateway": gateway.get_gateway_info(),
        "discovery": discovery.get_discovery_stats(),
        "github": github_client.get_client_stats() if github_client else None,
        "slack": slack_client.get_client_stats() if slack_client else None
    }

gateway.register_route("/metrics", "GET", metrics_handler)

async def health_handler(request):
    return {
        "status": "healthy",
        "components": {
            "gateway": await gateway.health_check(),
            "discovery": await discovery.health_check(),
            "github": await github_client.health_check() if github_client else None,
            "slack": await slack_client.health_check() if slack_client else None
        }
    }

gateway.register_route("/health", "GET", health_handler)
```

## Best Practices

### 1. Authentication Security

- Use environment variables for sensitive credentials
- Implement token rotation for production systems
- Use HTTPS for all API communications
- Implement proper CORS policies

### 2. Rate Limiting

- Configure appropriate rate limits based on usage patterns
- Use adaptive rate limiting for better performance
- Monitor rate limit usage and adjust as needed
- Implement proper retry logic with exponential backoff

### 3. Error Handling

- Always handle API errors gracefully
- Implement proper logging for debugging
- Use structured error responses
- Provide meaningful error messages to users

### 4. Monitoring

- Set up comprehensive health checks
- Monitor API performance metrics
- Implement alerting for critical failures
- Track rate limit usage and authentication metrics

### 5. Performance

- Use connection pooling for HTTP clients
- Implement caching where appropriate
- Use asynchronous operations for better concurrency
- Monitor and optimize database queries

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Check API key validity and permissions
   - Verify token hasn't expired
   - Ensure proper headers are included

2. **Rate Limiting**
   - Check current rate limit status
   - Implement proper retry logic
   - Consider using different rate limiting strategies

3. **Service Discovery Issues**
   - Verify service health check endpoints
   - Check service registration status
   - Monitor service cleanup logs

4. **GitHub Integration Problems**
   - Verify GitHub token permissions
   - Check webhook signature verification
   - Monitor GitHub API rate limits

5. **Slack Integration Issues**
   - Verify bot token scopes
   - Check webhook URL accessibility
   - Monitor Slack API rate limits

### Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Get detailed error information
try:
    result = await github_client.get_repository("owner", "repo")
except Exception as e:
    logging.error(f"Detailed error: {e}", exc_info=True)
```

## API Reference

For complete API reference documentation, visit:
- [API Gateway Reference](./api_gateway_reference.md)
- [Service Discovery Reference](./service_discovery_reference.md)
- [GitHub Integration Reference](./github_integration_reference.md)
- [Slack Integration Reference](./slack_integration_reference.md)

## Support

For support and questions:
- GitHub Issues: https://github.com/LeanVibe/agent-hive/issues
- Documentation: https://docs.agent-hive.com
- Email: support@leanvibe.com