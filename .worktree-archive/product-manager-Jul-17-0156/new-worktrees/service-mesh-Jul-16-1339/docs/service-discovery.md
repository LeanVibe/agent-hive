# Service Discovery Component

## Overview

The Simple Service Discovery component provides basic service registration and lookup functionality for the LeanVibe Agent Hive system.

## Features

- **Service Registration**: Register services with unique IDs
- **Service Lookup**: Find services by name or ID
- **Health Tracking**: Basic health status monitoring
- **Statistics**: Service discovery metrics

## Usage

### Basic Registration

```python
from external_api.simple_discovery import SimpleServiceDiscovery, Service

# Create discovery instance
discovery = SimpleServiceDiscovery()

# Register a service
service = Service(
    service_id="user-svc-1",
    name="user-service", 
    host="localhost",
    port=8080
)
discovery.register(service)
```

### Finding Services

```python
# Find services by name
user_services = discovery.find_by_name("user-service")

# Get service by ID
service = discovery.get_service("user-svc-1")

# List all services
all_services = discovery.list_all()
```

### Management

```python
# Unregister service
discovery.unregister("user-svc-1")

# Get statistics
stats = discovery.get_stats()
print(f"Total services: {stats['total_services']}")
```

## API Reference

### Service Class

- `service_id`: Unique identifier
- `name`: Service name for grouping
- `host`: Service hostname
- `port`: Service port number
- `status`: Health status ("healthy" or "unhealthy")
- `endpoint()`: Returns HTTP endpoint URL

### SimpleServiceDiscovery Class

- `register(service)`: Register a service instance
- `unregister(service_id)`: Remove a service
- `find_by_name(name)`: Find healthy services by name
- `get_service(service_id)`: Get service by ID
- `list_all()`: List all registered services
- `get_stats()`: Get discovery statistics

## Implementation Details

- In-memory storage for simplicity
- No persistence across restarts
- Thread-safe for basic operations
- Comprehensive logging for debugging

## Testing

Run tests with:

```bash
pytest tests/external_api/test_simple_discovery.py -v
```

Coverage: 100% (13/13 tests passing)