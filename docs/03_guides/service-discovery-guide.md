# Service Discovery Setup Guide

This guide provides comprehensive instructions for configuring and managing service discovery in LeanVibe Agent Hive.

## Overview

Service Discovery enables dynamic service registration and discovery in distributed agent systems, providing:
- **Automatic Service Registration**: Services register themselves on startup
- **Health Monitoring**: Continuous health checking of registered services
- **Load Balancing**: Intelligent distribution of requests across healthy instances
- **Fault Tolerance**: Circuit breaking and failover mechanisms
- **Service Mesh Integration**: Compatible with modern service mesh architectures

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Service Discovery Architecture                │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Service   │  │   Service   │  │   Service   │            │
│  │ Instance A  │  │ Instance B  │  │ Instance C  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│         │               │               │                     │
│         │ (register)    │ (register)    │ (register)          │
│         ▼               ▼               ▼                     │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Service Registry                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│  │  │Service Mesh │  │Health Check │  │Load Balancer    │  │  │
│  │  │Integration  │  │Engine       │  │                 │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │  │
│  └─────────────────────────────────────────────────────────┘  │
│                           │                                   │
│                           ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                API Gateway                              │  │
│  │         (Service Discovery Client)                     │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Supported Backends

### 1. Consul (Recommended for Production)

HashiCorp Consul provides robust service discovery with advanced features:

```yaml
service_discovery:
  backend: "consul"
  consul:
    host: "localhost"
    port: 8500
    datacenter: "dc1"
    token: "${CONSUL_TOKEN}"
    
    # Service configuration
    service:
      name: "agent-hive"
      tags: ["api", "v2"]
      port: 8080
      
    # Health check
    health_check:
      http: "http://localhost:8080/health"
      interval: "30s"
      timeout: "10s"
      deregister_critical_service_after: "1m"
      
    # Connect (Service Mesh)
    connect:
      enabled: true
      sidecar_service: {}
```

### 2. Kubernetes Native

For Kubernetes deployments, use native service discovery:

```yaml
service_discovery:
  backend: "kubernetes"
  kubernetes:
    namespace: "leanvibe"
    label_selector: "app=agent-hive"
    
    # Service configuration
    service_account: "agent-hive-sa"
    cluster_domain: "cluster.local"
    
    # Endpoints configuration
    endpoints:
      watch: true
      resync_period: "30s"
```

### 3. Etcd

For etcd-based service discovery:

```yaml
service_discovery:
  backend: "etcd"
  etcd:
    endpoints: ["localhost:2379"]
    username: "${ETCD_USERNAME}"
    password: "${ETCD_PASSWORD}"
    
    # TLS configuration
    tls:
      cert_file: "/etc/ssl/certs/etcd-client.crt"
      key_file: "/etc/ssl/private/etcd-client.key"
      ca_file: "/etc/ssl/certs/etcd-ca.crt"
      
    # Service TTL
    service_ttl: "30s"
    key_prefix: "/leanvibe/services"
```

### 4. Redis (Simple Setup)

For development and simple deployments:

```yaml
service_discovery:
  backend: "redis"
  redis:
    host: "localhost"
    port: 6379
    password: "${REDIS_PASSWORD}"
    db: 0
    
    # Service configuration
    key_prefix: "services:"
    service_ttl: 60  # seconds
    refresh_interval: 30  # seconds
```

## Installation and Setup

### Consul Setup

#### Using Docker

```bash
# Start Consul in development mode
docker run -d --name consul \
  -p 8500:8500 \
  -p 8600:8600/udp \
  consul:latest agent -dev -client=0.0.0.0

# Check Consul UI
open http://localhost:8500
```

#### Production Consul Cluster

```yaml
# docker-compose.yml
version: '3.8'
services:
  consul1:
    image: consul:latest
    command: agent -server -bootstrap-expect=3 -node=consul1 -bind=0.0.0.0 -client=0.0.0.0 -retry-join=consul2 -ui
    volumes:
      - consul1-data:/consul/data
    ports:
      - "8500:8500"
      - "8600:8600/udp"
    
  consul2:
    image: consul:latest
    command: agent -server -node=consul2 -bind=0.0.0.0 -retry-join=consul1
    volumes:
      - consul2-data:/consul/data
    
  consul3:
    image: consul:latest
    command: agent -server -node=consul3 -bind=0.0.0.0 -retry-join=consul1
    volumes:
      - consul3-data:/consul/data

volumes:
  consul1-data:
  consul2-data:
  consul3-data:
```

### Kubernetes Setup

```yaml
# service-discovery-rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: agent-hive-sa
  namespace: leanvibe
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: agent-hive-service-discovery
rules:
- apiGroups: [""]
  resources: ["endpoints", "services"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: agent-hive-service-discovery
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: agent-hive-service-discovery
subjects:
- kind: ServiceAccount
  name: agent-hive-sa
  namespace: leanvibe
```

## Configuration

### Service Registration Configuration

```python
# Service registration configuration
from leanvibe.discovery import ServiceRegistry, ServiceInstance

class ServiceRegistrationConfig:
    """Configuration for service registration."""
    
    def __init__(self):
        self.service_name = "agent-hive-api"
        self.service_id = f"{self.service_name}-{uuid.uuid4().hex[:8]}"
        self.host = self._get_host_ip()
        self.port = 8080
        self.tags = ["api", "v2", "production"]
        self.metadata = {
            "version": "2.0.0",
            "environment": "production",
            "capabilities": ["agent-management", "workflow-execution"]
        }
    
    def to_service_instance(self) -> ServiceInstance:
        """Convert to ServiceInstance."""
        return ServiceInstance(
            service_id=self.service_id,
            service_name=self.service_name,
            host=self.host,
            port=self.port,
            tags=self.tags,
            metadata=self.metadata,
            health_check_url=f"http://{self.host}:{self.port}/health"
        )
```

### Health Check Configuration

```yaml
health_checks:
  # HTTP health check
  http:
    enabled: true
    endpoint: "/health"
    interval: "30s"
    timeout: "10s"
    expected_status: [200, 204]
    
  # TCP health check
  tcp:
    enabled: true
    port: 8080
    interval: "10s"
    timeout: "3s"
    
  # Custom script health check
  script:
    enabled: false
    command: ["/bin/sh", "-c", "curl -f http://localhost:8080/health"]
    interval: "30s"
    timeout: "5s"
    
  # Lifecycle management
  lifecycle:
    deregister_critical_after: "1m"
    initial_status: "passing"
    notes: "Agent Hive API health check"
```

### Load Balancing Configuration

```yaml
load_balancing:
  strategy: "least_connections"  # Options: round_robin, least_connections, weighted_round_robin, ip_hash
  
  # Health-based load balancing
  health_based:
    enabled: true
    healthy_threshold: 2    # consecutive health checks
    unhealthy_threshold: 3  # consecutive failures
    
  # Weighted load balancing
  weighted:
    enabled: false
    weights:
      "agent-hive-1": 100
      "agent-hive-2": 200
      "agent-hive-3": 150
      
  # Circuit breaker
  circuit_breaker:
    enabled: true
    failure_threshold: 5      # failures before opening
    recovery_timeout: "60s"   # time before attempting recovery
    test_request_volume: 10   # test requests during half-open
```

## Implementation

### Service Registry Implementation

```python
import asyncio
import json
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

@dataclass
class ServiceInstance:
    """Represents a service instance."""
    service_id: str
    service_name: str
    host: str
    port: int
    tags: List[str]
    metadata: Dict[str, str]
    health_check_url: str
    last_seen: datetime = None
    status: str = "unknown"  # passing, warning, critical

class ServiceRegistry:
    """Core service registry implementation."""
    
    def __init__(self, backend_config: Dict):
        self.backend_config = backend_config
        self.backend = self._create_backend()
        self.services: Dict[str, Set[ServiceInstance]] = {}
        self.health_checker = HealthChecker()
        self.load_balancer = LoadBalancer()
        
    async def register_service(self, instance: ServiceInstance) -> bool:
        """Register a service instance."""
        try:
            # Register with backend
            await self.backend.register(instance)
            
            # Add to local cache
            if instance.service_name not in self.services:
                self.services[instance.service_name] = set()
            self.services[instance.service_name].add(instance)
            
            # Start health checking
            await self.health_checker.start_monitoring(instance)
            
            print(f"✅ Registered service: {instance.service_name} ({instance.service_id})")
            return True
            
        except Exception as e:
            print(f"❌ Failed to register service {instance.service_id}: {e}")
            return False
    
    async def deregister_service(self, service_id: str) -> bool:
        """Deregister a service instance."""
        try:
            # Remove from backend
            await self.backend.deregister(service_id)
            
            # Remove from local cache
            for service_name, instances in self.services.items():
                self.services[service_name] = {
                    inst for inst in instances if inst.service_id != service_id
                }
            
            # Stop health checking
            await self.health_checker.stop_monitoring(service_id)
            
            print(f"✅ Deregistered service: {service_id}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to deregister service {service_id}: {e}")
            return False
    
    async def discover_services(self, service_name: str, tags: List[str] = None) -> List[ServiceInstance]:
        """Discover healthy instances of a service."""
        try:
            # Get from backend
            instances = await self.backend.discover(service_name, tags)
            
            # Filter by health status
            healthy_instances = [
                inst for inst in instances 
                if inst.status == "passing"
            ]
            
            return healthy_instances
            
        except Exception as e:
            print(f"❌ Failed to discover services {service_name}: {e}")
            return []
    
    async def get_service_instance(self, service_name: str, tags: List[str] = None) -> Optional[ServiceInstance]:
        """Get a single healthy service instance using load balancing."""
        instances = await self.discover_services(service_name, tags)
        
        if not instances:
            return None
            
        return await self.load_balancer.select_instance(instances)

class HealthChecker:
    """Health checking system for service instances."""
    
    def __init__(self):
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.health_status: Dict[str, str] = {}
        
    async def start_monitoring(self, instance: ServiceInstance):
        """Start health monitoring for an instance."""
        if instance.service_id in self.monitoring_tasks:
            return
            
        task = asyncio.create_task(self._monitor_instance(instance))
        self.monitoring_tasks[instance.service_id] = task
        
    async def stop_monitoring(self, service_id: str):
        """Stop health monitoring for an instance."""
        if service_id in self.monitoring_tasks:
            self.monitoring_tasks[service_id].cancel()
            del self.monitoring_tasks[service_id]
            
    async def _monitor_instance(self, instance: ServiceInstance):
        """Monitor health of a single instance."""
        consecutive_failures = 0
        
        while True:
            try:
                # Perform health check
                is_healthy = await self._check_health(instance)
                
                if is_healthy:
                    consecutive_failures = 0
                    self.health_status[instance.service_id] = "passing"
                    instance.status = "passing"
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        self.health_status[instance.service_id] = "critical"
                        instance.status = "critical"
                    else:
                        self.health_status[instance.service_id] = "warning"
                        instance.status = "warning"
                
                instance.last_seen = datetime.now()
                
                # Update in registry
                await self._update_instance_status(instance)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Health check error for {instance.service_id}: {e}")
                consecutive_failures += 1
                
            await asyncio.sleep(30)  # Health check interval
    
    async def _check_health(self, instance: ServiceInstance) -> bool:
        """Perform actual health check."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    instance.health_check_url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status in [200, 204]
        except Exception:
            return False
    
    async def _update_instance_status(self, instance: ServiceInstance):
        """Update instance status in the registry."""
        # Implementation depends on backend
        pass

class LoadBalancer:
    """Load balancing for service instances."""
    
    def __init__(self, strategy: str = "least_connections"):
        self.strategy = strategy
        self.connection_counts: Dict[str, int] = {}
        self.round_robin_index: Dict[str, int] = {}
        
    async def select_instance(self, instances: List[ServiceInstance]) -> Optional[ServiceInstance]:
        """Select an instance based on load balancing strategy."""
        if not instances:
            return None
            
        if self.strategy == "round_robin":
            return self._round_robin_select(instances)
        elif self.strategy == "least_connections":
            return self._least_connections_select(instances)
        elif self.strategy == "weighted_round_robin":
            return self._weighted_round_robin_select(instances)
        else:
            # Default to round robin
            return self._round_robin_select(instances)
    
    def _round_robin_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Round robin selection."""
        service_name = instances[0].service_name
        
        if service_name not in self.round_robin_index:
            self.round_robin_index[service_name] = 0
            
        index = self.round_robin_index[service_name] % len(instances)
        self.round_robin_index[service_name] += 1
        
        return instances[index]
    
    def _least_connections_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Least connections selection."""
        # Find instance with least connections
        min_connections = float('inf')
        selected_instance = instances[0]
        
        for instance in instances:
            connections = self.connection_counts.get(instance.service_id, 0)
            if connections < min_connections:
                min_connections = connections
                selected_instance = instance
                
        return selected_instance
    
    def record_connection(self, service_id: str):
        """Record a new connection to an instance."""
        self.connection_counts[service_id] = self.connection_counts.get(service_id, 0) + 1
        
    def release_connection(self, service_id: str):
        """Release a connection from an instance."""
        if service_id in self.connection_counts:
            self.connection_counts[service_id] = max(0, self.connection_counts[service_id] - 1)
```

### Backend Implementations

#### Consul Backend

```python
import consul
from typing import List, Optional

class ConsulBackend:
    """Consul service discovery backend."""
    
    def __init__(self, config: Dict):
        self.consul = consul.Consul(
            host=config.get('host', 'localhost'),
            port=config.get('port', 8500),
            token=config.get('token')
        )
        self.config = config
        
    async def register(self, instance: ServiceInstance) -> bool:
        """Register service with Consul."""
        try:
            self.consul.agent.service.register(
                name=instance.service_name,
                service_id=instance.service_id,
                address=instance.host,
                port=instance.port,
                tags=instance.tags,
                meta=instance.metadata,
                check=consul.Check.http(
                    instance.health_check_url,
                    interval="30s",
                    timeout="10s",
                    deregister="1m"
                )
            )
            return True
        except Exception as e:
            print(f"Consul registration error: {e}")
            return False
    
    async def deregister(self, service_id: str) -> bool:
        """Deregister service from Consul."""
        try:
            self.consul.agent.service.deregister(service_id)
            return True
        except Exception as e:
            print(f"Consul deregistration error: {e}")
            return False
    
    async def discover(self, service_name: str, tags: List[str] = None) -> List[ServiceInstance]:
        """Discover services from Consul."""
        try:
            _, services = self.consul.health.service(
                service_name,
                tag=tags[0] if tags else None,
                passing=True
            )
            
            instances = []
            for service in services:
                service_info = service['Service']
                instances.append(ServiceInstance(
                    service_id=service_info['ID'],
                    service_name=service_info['Service'],
                    host=service_info['Address'],
                    port=service_info['Port'],
                    tags=service_info['Tags'],
                    metadata=service_info['Meta'],
                    health_check_url=f"http://{service_info['Address']}:{service_info['Port']}/health",
                    status="passing"
                ))
            
            return instances
            
        except Exception as e:
            print(f"Consul discovery error: {e}")
            return []
```

#### Kubernetes Backend

```python
from kubernetes import client, config
from kubernetes.client.rest import ApiException

class KubernetesBackend:
    """Kubernetes service discovery backend."""
    
    def __init__(self, k8s_config: Dict):
        config.load_incluster_config()
        self.v1 = client.CoreV1Api()
        self.namespace = k8s_config.get('namespace', 'default')
        self.label_selector = k8s_config.get('label_selector', '')
        
    async def discover(self, service_name: str, tags: List[str] = None) -> List[ServiceInstance]:
        """Discover services from Kubernetes."""
        try:
            # Get endpoints for the service
            endpoints = self.v1.list_namespaced_endpoints(
                namespace=self.namespace,
                label_selector=self.label_selector
            )
            
            instances = []
            for endpoint in endpoints.items:
                if endpoint.metadata.name == service_name:
                    for subset in endpoint.subsets or []:
                        for address in subset.addresses or []:
                            for port in subset.ports or []:
                                instances.append(ServiceInstance(
                                    service_id=f"{service_name}-{address.ip}-{port.port}",
                                    service_name=service_name,
                                    host=address.ip,
                                    port=port.port,
                                    tags=tags or [],
                                    metadata={},
                                    health_check_url=f"http://{address.ip}:{port.port}/health",
                                    status="passing"
                                ))
            
            return instances
            
        except ApiException as e:
            print(f"Kubernetes discovery error: {e}")
            return []
```

## Integration with API Gateway

### Gateway Service Discovery Client

```python
class GatewayServiceDiscovery:
    """Service discovery client for API Gateway."""
    
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
        self.route_cache: Dict[str, List[ServiceInstance]] = {}
        self.cache_ttl = 30  # seconds
        self.last_cache_update: Dict[str, datetime] = {}
        
    async def resolve_route(self, path: str) -> Optional[ServiceInstance]:
        """Resolve API path to service instance."""
        service_name = self._extract_service_name(path)
        
        if not service_name:
            return None
            
        # Check cache
        if self._is_cache_valid(service_name):
            instances = self.route_cache[service_name]
        else:
            # Refresh cache
            instances = await self.registry.discover_services(service_name)
            self.route_cache[service_name] = instances
            self.last_cache_update[service_name] = datetime.now()
        
        if not instances:
            return None
            
        # Return load-balanced instance
        return await self.registry.load_balancer.select_instance(instances)
    
    def _extract_service_name(self, path: str) -> Optional[str]:
        """Extract service name from API path."""
        # Example: /api/v1/agents -> agent-service
        # Example: /api/v1/workflows -> workflow-service
        path_parts = path.strip('/').split('/')
        
        if len(path_parts) >= 3 and path_parts[0] == 'api':
            resource = path_parts[2]
            return f"{resource}-service"
            
        return None
    
    def _is_cache_valid(self, service_name: str) -> bool:
        """Check if cache entry is still valid."""
        if service_name not in self.last_cache_update:
            return False
            
        age = datetime.now() - self.last_cache_update[service_name]
        return age.total_seconds() < self.cache_ttl
```

## Deployment Configurations

### Docker Compose with Consul

```yaml
# docker-compose.yml
version: '3.8'
services:
  consul:
    image: consul:latest
    command: agent -dev -client=0.0.0.0 -ui
    ports:
      - "8500:8500"
      - "8600:8600/udp"
    volumes:
      - consul-data:/consul/data
      
  agent-hive-api-1:
    image: leanvibe/agent-hive:latest
    environment:
      - SERVICE_DISCOVERY_BACKEND=consul
      - CONSUL_HOST=consul
      - CONSUL_PORT=8500
      - SERVICE_NAME=agent-hive-api
      - SERVICE_PORT=8080
    ports:
      - "8081:8080"
    depends_on:
      - consul
      
  agent-hive-api-2:
    image: leanvibe/agent-hive:latest
    environment:
      - SERVICE_DISCOVERY_BACKEND=consul
      - CONSUL_HOST=consul
      - CONSUL_PORT=8500
      - SERVICE_NAME=agent-hive-api
      - SERVICE_PORT=8080
    ports:
      - "8082:8080"
    depends_on:
      - consul
      
  api-gateway:
    image: leanvibe/api-gateway:latest
    environment:
      - SERVICE_DISCOVERY_BACKEND=consul
      - CONSUL_HOST=consul
      - CONSUL_PORT=8500
    ports:
      - "8080:8080"
    depends_on:
      - consul
      - agent-hive-api-1
      - agent-hive-api-2
      
volumes:
  consul-data:
```

### Kubernetes Deployment

```yaml
# service-discovery-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-hive-api
  namespace: leanvibe
  labels:
    app: agent-hive
    component: api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent-hive
      component: api
  template:
    metadata:
      labels:
        app: agent-hive
        component: api
    spec:
      serviceAccountName: agent-hive-sa
      containers:
      - name: api
        image: leanvibe/agent-hive:latest
        ports:
        - containerPort: 8080
          name: http
        env:
        - name: SERVICE_DISCOVERY_BACKEND
          value: "kubernetes"
        - name: KUBERNETES_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
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
---
apiVersion: v1
kind: Service
metadata:
  name: agent-hive-api
  namespace: leanvibe
  labels:
    app: agent-hive
    component: api
spec:
  selector:
    app: agent-hive
    component: api
  ports:
  - name: http
    port: 8080
    targetPort: 8080
  type: ClusterIP
```

## Monitoring and Observability

### Service Discovery Metrics

```yaml
metrics:
  service_discovery:
    # Registration metrics
    - name: service_registrations_total
      type: counter
      labels: [service_name, status]
      
    - name: service_instances_active
      type: gauge
      labels: [service_name]
      
    # Health check metrics
    - name: health_checks_total
      type: counter
      labels: [service_name, service_id, status]
      
    - name: health_check_duration
      type: histogram
      labels: [service_name]
      buckets: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
      
    # Load balancing metrics
    - name: load_balancer_requests_total
      type: counter
      labels: [service_name, strategy, instance_id]
      
    - name: service_response_time
      type: histogram
      labels: [service_name, instance_id]
      buckets: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
```

### Logging Configuration

```yaml
logging:
  service_discovery:
    level: INFO
    structured: true
    
    # Log all service registrations/deregistrations
    events:
      - service_registered
      - service_deregistered
      - health_check_failed
      - health_check_recovered
      - load_balancer_selection
      
    # Include context fields
    context_fields:
      - service_name
      - service_id
      - instance_address
      - health_status
      - load_balancer_strategy
```

## Security Considerations

### Service Authentication

```yaml
security:
  service_discovery:
    # Mutual TLS for service communication
    mtls:
      enabled: true
      ca_cert: "/etc/ssl/certs/ca.crt"
      cert_file: "/etc/ssl/certs/service.crt"
      key_file: "/etc/ssl/private/service.key"
      
    # Service identity verification
    service_identity:
      enabled: true
      method: "jwt"  # or "certificate"
      jwt_secret: "${SERVICE_JWT_SECRET}"
      
    # Network policies
    network_policies:
      enabled: true
      default_deny: true
      allowed_ports: [8080, 8443]
```

### Access Control

```yaml
access_control:
  service_discovery:
    # Role-based access for service operations
    rbac:
      enabled: true
      roles:
        service_admin:
          permissions: ["register", "deregister", "discover", "health_check"]
        service_user:
          permissions: ["discover"]
          
    # Rate limiting for discovery requests
    rate_limiting:
      enabled: true
      discover_requests: "100/minute"
      register_requests: "10/minute"
```

## Troubleshooting

### Common Issues

**Service Registration Failures**
```bash
# Check backend connectivity
curl -f http://consul:8500/v1/status/leader

# Verify service configuration
leanvibe service-discovery validate-config

# Check health check endpoint
curl -f http://service-host:8080/health
```

**Service Discovery Not Working**
```bash
# List registered services
leanvibe service-discovery list-services

# Check service health
leanvibe service-discovery health-check --service-name agent-hive-api

# Verify load balancing
leanvibe service-discovery test-load-balancing --service-name agent-hive-api
```

**Health Checks Failing**
```bash
# Check health check configuration
leanvibe service-discovery describe-health-checks

# Test health check manually
curl -v http://service-host:8080/health

# Check health check logs
leanvibe logs --component health-checker --service-id service-123
```

### Debug Commands

```bash
# Enable debug logging
export SERVICE_DISCOVERY_LOG_LEVEL=DEBUG

# Test service discovery
leanvibe service-discovery test --service-name agent-hive-api

# Monitor service health
leanvibe service-discovery monitor --service-name agent-hive-api

# Simulate network partition
leanvibe service-discovery simulate-partition --duration 60s
```

### Performance Tuning

**Health Check Optimization**
```yaml
health_checks:
  # Optimize for performance
  batch_size: 10
  parallel_checks: 5
  check_interval: "15s"  # Reduce for faster detection
  timeout: "3s"          # Reduce for faster failures
  
  # Adaptive health checking
  adaptive:
    enabled: true
    fast_interval: "5s"   # When unhealthy
    slow_interval: "60s"  # When consistently healthy
```

**Discovery Cache Optimization**
```yaml
discovery_cache:
  # Cache configuration
  ttl: "30s"
  max_entries: 1000
  eviction_policy: "lru"
  
  # Refresh strategies
  refresh_strategy: "background"  # background, on_demand, scheduled
  refresh_interval: "15s"
  refresh_jitter: "5s"
```

## Best Practices

### Service Design
- **Stateless Services**: Design services to be stateless for easier scaling
- **Health Endpoints**: Implement comprehensive health checks
- **Graceful Shutdown**: Handle shutdown signals properly
- **Service Versioning**: Use semantic versioning for services

### Configuration Management
- **Environment-specific**: Use different configs for dev/staging/prod
- **Secret Management**: Secure handling of sensitive configuration
- **Configuration Validation**: Validate all configuration on startup
- **Hot Reloading**: Support runtime configuration updates

### Monitoring and Alerting
- **Service Metrics**: Monitor key service metrics
- **Discovery Metrics**: Track service discovery performance
- **Health Alerts**: Alert on service health issues
- **Capacity Planning**: Monitor resource usage trends

## Integration Examples

### API Gateway Integration

```python
# Example API Gateway integration
from fastapi import FastAPI, HTTPException
from leanvibe.discovery import ServiceRegistry

app = FastAPI()
service_registry = ServiceRegistry(consul_config)

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_request(path: str, request: Request):
    # Discover service for this path
    instance = await service_registry.resolve_route(f"/{path}")
    
    if not instance:
        raise HTTPException(status_code=503, detail="Service unavailable")
    
    # Proxy request to service instance
    target_url = f"http://{instance.host}:{instance.port}/{path}"
    
    # Forward request with load balancing
    response = await forward_request(target_url, request)
    return response
```

### Service Mesh Integration

```yaml
# Istio service mesh integration
apiVersion: networking.istio.io/v1alpha3
kind: ServiceEntry
metadata:
  name: external-service-discovery
spec:
  hosts:
  - consul.service.consul
  ports:
  - number: 8500
    name: http
    protocol: HTTP
  resolution: DNS
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: agent-hive-api
spec:
  host: agent-hive-api.leanvibe.svc.cluster.local
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpHeaderName: "x-user-id"
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

## Next Steps

### Learning Path
1. **Setup**: Complete service discovery setup
2. **Integration**: Integrate with API Gateway
3. **Monitoring**: Set up comprehensive monitoring
4. **Security**: Implement security best practices

### Advanced Topics
- Service mesh integration (Istio, Linkerd)
- Multi-region service discovery
- Custom load balancing algorithms
- Advanced health checking strategies

---

This comprehensive guide provides everything needed to implement robust service discovery in LeanVibe Agent Hive, ensuring high availability and scalability for distributed agent systems.