# RBAC Framework Implementation Guide

## Overview

The Role-Based Access Control (RBAC) framework provides comprehensive authorization capabilities for the LeanVibe Agent Hive infrastructure. This implementation features hierarchical roles, granular permissions, dynamic authorization evaluation, and high-performance Redis caching.

## Architecture

### Core Components

1. **RBAC Framework** (`rbac_framework.py`)
   - `Permission`: Granular permission with resource, action, and scope
   - `Role`: Hierarchical role with permission inheritance
   - `User`: User with role assignments and direct permissions
   - `RBACManager`: Central management of roles and users
   - `AuthorizationEvaluator`: High-performance permission evaluation

2. **Permission Manager** (`permission_manager.py`)
   - `PermissionCacheManager`: Redis-based caching layer
   - `PermissionManager`: Enhanced permission operations
   - `PermissionQueryBuilder`: SQL-like permission queries

3. **Authorization Middleware** (`rbac_middleware.py`)
   - `RBACMiddleware`: Request-level authorization
   - `ResourceMapper`: Endpoint-to-resource mapping
   - `AuditLogger`: Comprehensive audit logging

## Quick Start

### Basic Setup

```python
import redis
from external_api.rbac_framework import RBACManager
from external_api.permission_manager import PermissionManager
from external_api.rbac_middleware import RBACMiddleware

# Initialize Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Initialize RBAC components
rbac_manager = RBACManager(redis_client)
permission_manager = PermissionManager(rbac_manager, redis_client)
rbac_middleware = RBACMiddleware(
    rbac_manager, 
    permission_manager, 
    auth_middleware,
    redis_client
)
```

### Creating Users and Roles

```python
# Create a custom role
custom_role = rbac_manager.create_role(
    name="api_developer",
    description="API development permissions",
    permissions=[
        Permission(ResourceType.API_ENDPOINT, ActionType.READ, PermissionScope.PROJECT),
        Permission(ResourceType.API_ENDPOINT, ActionType.CREATE, PermissionScope.PROJECT),
        Permission(ResourceType.DATABASE, ActionType.READ, PermissionScope.PROJECT)
    ],
    parent_roles=["developer"]  # Inherits from developer role
)

# Create a user with roles
user = rbac_manager.create_user(
    user_id="john.doe@company.com",
    roles=["api_developer"]
)

# Add direct permission to user
user.add_direct_permission(
    Permission(ResourceType.SERVICE, ActionType.DEPLOY, PermissionScope.RESOURCE, "my-service")
)
```

### Permission Checking

```python
# Check if user has permission
has_permission = rbac_manager.check_permission(
    user_id="john.doe@company.com",
    resource_type=ResourceType.API_ENDPOINT,
    action=ActionType.READ
)

# Check permission with context
has_permission_with_context = rbac_manager.check_permission(
    user_id="john.doe@company.com",
    resource_type=ResourceType.DATABASE,
    action=ActionType.READ,
    resource_id="user_database",
    context={"environment": "production"}
)
```

## Advanced Usage

### Bulk Permission Operations

```python
# Check multiple permissions efficiently
permission_requests = [
    {
        "user_id": "john.doe@company.com",
        "resource_type": "api_endpoint",
        "action": "read"
    },
    {
        "user_id": "jane.smith@company.com",
        "resource_type": "service",
        "action": "deploy"
    }
]

results = await permission_manager.bulk_check_permissions(permission_requests)
```

### Permission Matrix Generation

```python
# Generate permission matrix for multiple users
users = ["john.doe@company.com", "jane.smith@company.com"]
permissions = [
    (ResourceType.API_ENDPOINT, ActionType.READ, None),
    (ResourceType.SERVICE, ActionType.DEPLOY, None),
    (ResourceType.DATABASE, ActionType.UPDATE, None)
]

matrix = await permission_manager.get_permission_matrix(users, permissions)
```

### Dynamic Permission Queries

```python
# Query permissions using builder pattern
from external_api.permission_manager import PermissionQueryBuilder

query = PermissionQueryBuilder(permission_manager)
api_permissions = await query.for_user("john.doe@company.com") \
                           .for_resource_type(ResourceType.API_ENDPOINT) \
                           .for_action(ActionType.READ) \
                           .execute()
```

## Resource Types and Actions

### Resource Types

| Type | Description | Examples |
|------|-------------|----------|
| `API_ENDPOINT` | REST API endpoints | `/api/v1/users`, `/api/v1/services` |
| `SERVICE` | Microservices | `user-service`, `payment-service` |
| `AGENT` | AI agents | `coordination-agent`, `quality-agent` |
| `WORKFLOW` | Business workflows | `deployment-workflow`, `approval-workflow` |
| `DATABASE` | Database resources | `user_db`, `analytics_db` |
| `FILE_SYSTEM` | File system resources | `/data/uploads`, `/logs/application` |
| `MONITORING` | Monitoring resources | `metrics`, `alerts`, `dashboards` |
| `CONFIGURATION` | Configuration resources | `app-config`, `secrets` |

### Action Types

| Action | Description | Use Cases |
|--------|-------------|-----------|
| `CREATE` | Create new resources | POST requests, new records |
| `READ` | Read existing resources | GET requests, view data |
| `UPDATE` | Modify existing resources | PUT/PATCH requests, edit data |
| `DELETE` | Remove resources | DELETE requests, remove data |
| `EXECUTE` | Execute operations | Run workflows, trigger actions |
| `ADMIN` | Administrative operations | System administration |
| `CONFIGURE` | Configure resources | Change settings, update config |
| `MONITOR` | Monitor resources | View metrics, access logs |
| `DEPLOY` | Deploy resources | Service deployment, releases |
| `SCALE` | Scale resources | Auto-scaling, resource allocation |

### Permission Scopes

| Scope | Description | Example |
|-------|-------------|---------|
| `GLOBAL` | System-wide access | Super admin permissions |
| `ORGANIZATION` | Organization-level access | Company-wide resources |
| `PROJECT` | Project-level access | Team project resources |
| `RESOURCE` | Specific resource access | Single service or endpoint |
| `INSTANCE` | Instance-level access | Specific resource instance |

## Role Hierarchy

### System Roles

The framework includes pre-defined system roles with inheritance:

```
super_admin (Global access to all resources)
    ↓
admin (Most resources with some restrictions)
    ↓
developer (Development-focused permissions)
    ↓
viewer (Read-only access)

admin (Administrative permissions)
    ↓
operator (Operations and deployment)
    ↓
viewer (Read-only access)
```

### Custom Role Creation

```python
# Create role with inheritance
backend_dev = rbac_manager.create_role(
    name="backend_developer",
    description="Backend development permissions",
    parent_roles=["developer"],
    permissions=[
        Permission(ResourceType.DATABASE, ActionType.READ, PermissionScope.PROJECT),
        Permission(ResourceType.DATABASE, ActionType.UPDATE, PermissionScope.PROJECT),
        Permission(ResourceType.SERVICE, ActionType.DEPLOY, PermissionScope.PROJECT)
    ]
)

# Create specialized role
api_specialist = rbac_manager.create_role(
    name="api_specialist",
    description="API-focused development",
    parent_roles=["backend_developer"],
    permissions=[
        Permission(ResourceType.API_ENDPOINT, ActionType.ADMIN, PermissionScope.PROJECT)
    ]
)
```

## Caching Strategy

### Redis Cache Structure

```
rbac:user_perms:{user_id}          # User permissions
rbac:role_perms:{role_name}        # Role permissions
rbac:check:{cache_key}             # Permission check results
rbac:hierarchy:{role_name}         # Role hierarchy
rbac:bulk:{bulk_id}                # Bulk operation results
```

### Cache Management

```python
# Clear cache for specific user
await permission_manager.cache.invalidate_user_cache("john.doe@company.com")

# Clear cache for specific role
await permission_manager.cache.invalidate_role_cache("developer")

# Clear all caches
await permission_manager.clear_cache()

# Get cache statistics
cache_stats = await permission_manager.get_cache_stats()
```

## Middleware Integration

### Request Authorization

```python
from external_api.models import ApiRequest

# Create API request
request = ApiRequest(
    method="GET",
    path="/api/v1/services/user-service",
    headers={"Authorization": "Bearer jwt-token"},
    client_ip="192.168.1.100"
)

# Authorize request
auth_result = await rbac_middleware.authorize_request(request)

if auth_result.authorized:
    # Process request
    process_api_request(request)
else:
    # Return authorization error
    return {"error": auth_result.reason, "code": 403}
```

### Custom Resource Mapping

```python
# Add custom endpoint mapping
rbac_middleware.resource_mapper.add_endpoint_mapping(
    "/api/v1/custom/execute",
    ResourceType.WORKFLOW,
    ActionType.EXECUTE
)

# Remove endpoint mapping
rbac_middleware.resource_mapper.remove_endpoint_mapping("/api/v1/old-endpoint")
```

## Security Best Practices

### 1. Default Deny Policy

```python
# Framework uses default deny - explicitly grant permissions
rbac_manager.default_deny = True
```

### 2. Permission Expiration

```python
# Create time-limited permissions
temp_permission = Permission(
    resource_type=ResourceType.DATABASE,
    action=ActionType.UPDATE,
    scope=PermissionScope.RESOURCE,
    resource_id="temp_data",
    expires_at=datetime.now() + timedelta(hours=1)
)
```

### 3. Context-Aware Permissions

```python
# Environment-specific permissions
prod_permission = Permission(
    resource_type=ResourceType.SERVICE,
    action=ActionType.DEPLOY,
    scope=PermissionScope.GLOBAL,
    conditions={"environment": "production", "approval_required": True}
)
```

### 4. Audit Logging

```python
# Get audit logs for security analysis
audit_logs = await rbac_middleware.audit_logger.get_audit_logs(
    user_id="john.doe@company.com",
    resource_type=ResourceType.DATABASE,
    authorized=False  # Get denied access attempts
)

# Get audit statistics
audit_stats = await rbac_middleware.get_audit_summary()
```

## Performance Optimization

### 1. Cache Configuration

```python
# Configure cache TTL
cache_manager = PermissionCacheManager(redis_client, cache_ttl=600)  # 10 minutes

# Bulk cache operations
bulk_id = "user_permissions_bulk"
await cache_manager.set_bulk_permissions(bulk_id, results)
```

### 2. Bulk Operations

```python
# Batch permission checks
batch_requests = [
    (ResourceType.API_ENDPOINT, ActionType.READ, None),
    (ResourceType.SERVICE, ActionType.DEPLOY, "my-service"),
    (ResourceType.DATABASE, ActionType.UPDATE, "user_db")
]

batch_results = await permission_manager.check_batch_permissions(
    "john.doe@company.com", 
    batch_requests
)
```

### 3. Performance Monitoring

```python
# Get performance metrics
metrics = rbac_middleware.get_metrics()
print(f"Authorization rate: {metrics['authorization_rate']:.2%}")
print(f"Average response time: {metrics['avg_response_time']:.2f}ms")
print(f"Cache hit rate: {metrics['cache_hit_rate']:.2%}")
```

## Analytics and Reporting

### Permission Analytics

```python
# Get comprehensive analytics
analytics = await permission_manager.get_permission_analytics()

print(f"Total users: {analytics['total_users']}")
print(f"Cache hit rate: {analytics['cache_performance']['hit_rate']:.2%}")
print(f"Most used permissions: {analytics['permission_types']}")
```

### Role Distribution

```python
# Get role distribution
stats = rbac_manager.get_stats()
print(f"Role distribution: {stats['role_distribution']}")
```

## Error Handling

### Common Exceptions

```python
try:
    user = rbac_manager.create_user("existing_user", roles=["admin"])
except ValueError as e:
    print(f"User creation failed: {e}")

try:
    has_permission = rbac_manager.check_permission(
        "non_existent_user", 
        ResourceType.API_ENDPOINT, 
        ActionType.READ
    )
except Exception as e:
    print(f"Permission check failed: {e}")
```

### Authorization Errors

```python
# Handle authorization failures
auth_result = await rbac_middleware.authorize_request(request)

if not auth_result.authorized:
    if "Authentication failed" in auth_result.reason:
        return {"error": "Invalid credentials", "code": 401}
    elif "Insufficient permissions" in auth_result.reason:
        return {"error": "Access denied", "code": 403}
    else:
        return {"error": "Authorization error", "code": 500}
```

## Testing

### Unit Tests

```python
import pytest
from external_api.rbac_framework import RBACManager, Permission, ResourceType, ActionType

@pytest.fixture
def rbac_manager():
    return RBACManager()

def test_permission_creation(rbac_manager):
    permission = Permission(
        resource_type=ResourceType.API_ENDPOINT,
        action=ActionType.READ,
        scope=PermissionScope.PROJECT
    )
    assert permission.is_valid()

def test_role_hierarchy(rbac_manager):
    # Test role inheritance
    developer = rbac_manager.get_role("developer")
    assert "admin" in developer.parent_roles
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_middleware_authorization():
    # Test complete authorization flow
    request = create_mock_request()
    result = await rbac_middleware.authorize_request(request)
    assert result.authorized
```

## Deployment

### Production Configuration

```python
# Production RBAC configuration
rbac_config = {
    "redis_host": "redis-cluster.company.com",
    "redis_port": 6379,
    "cache_ttl": 300,
    "max_auth_attempts": 5,
    "auth_window_minutes": 15,
    "audit_retention_days": 90
}

# Initialize with production config
rbac_manager = RBACManager(config=rbac_config)
```

### Monitoring Setup

```python
# Set up monitoring
from external_api.rbac_middleware import RBACMiddleware

# Enable detailed logging
import logging
logging.getLogger('external_api.rbac_framework').setLevel(logging.INFO)
logging.getLogger('external_api.permission_manager').setLevel(logging.INFO)

# Monitor metrics
metrics = rbac_middleware.get_metrics()
# Send metrics to monitoring system
```

## Troubleshooting

### Common Issues

1. **High Cache Miss Rate**
   - Check Redis connection
   - Verify cache TTL settings
   - Monitor cache invalidation frequency

2. **Slow Authorization**
   - Check Redis latency
   - Optimize role hierarchy depth
   - Use bulk operations for multiple checks

3. **Permission Denied Errors**
   - Verify user role assignments
   - Check permission conditions
   - Review audit logs for details

### Debug Mode

```python
# Enable debug logging
logging.getLogger('external_api.rbac_framework').setLevel(logging.DEBUG)

# Check permission evaluation details
result = rbac_manager.check_permission(
    "user_id", 
    ResourceType.API_ENDPOINT, 
    ActionType.READ
)
# Debug logs will show evaluation steps
```

## Migration and Upgrades

### Data Migration

```python
# Export current roles and permissions
roles_data = {}
for role_name, role in rbac_manager.roles.items():
    roles_data[role_name] = {
        "description": role.description,
        "permissions": [asdict(p) for p in role.permissions],
        "parent_roles": role.parent_roles
    }

# Import to new system
for role_name, role_data in roles_data.items():
    rbac_manager.create_role(
        name=role_name,
        description=role_data["description"],
        permissions=[Permission(**p) for p in role_data["permissions"]],
        parent_roles=role_data["parent_roles"]
    )
```

This comprehensive RBAC framework provides enterprise-grade authorization capabilities with high performance, security, and scalability. The modular design allows for easy extension and customization to meet specific requirements.