# Production Monitoring and Observability Guide

**🎯 Goal**: Comprehensive monitoring setup for LeanVibe Agent Hive production deployments with real-time insights and proactive alerting.

## Table of Contents

- [Monitoring Architecture](#monitoring-architecture)
- [Core Metrics Collection](#core-metrics-collection)
- [Application Performance Monitoring](#application-performance-monitoring)
- [Infrastructure Monitoring](#infrastructure-monitoring)
- [Real-time Dashboards](#real-time-dashboards)
- [Alerting and Notification](#alerting-and-notification)
- [Log Management](#log-management)
- [Distributed Tracing](#distributed-tracing)
- [Security Monitoring](#security-monitoring)
- [Performance Optimization](#performance-optimization)

## Monitoring Architecture

### Overview

```mermaid
graph TB
    subgraph "Application Layer"
        AH[Agent Hive Services]
        EXT[External APIs]
        CLI[CLI Components]
    end
    
    subgraph "Metrics Collection"
        PROM[Prometheus]
        OTEL[OpenTelemetry]
        APP_METRICS[Application Metrics]
    end
    
    subgraph "Log Aggregation"
        FLUENTD[Fluentd]
        ELK[Elasticsearch]
        KIBANA[Kibana]
    end
    
    subgraph "Visualization"
        GRAF[Grafana]
        DASH[Custom Dashboards]
    end
    
    subgraph "Alerting"
        ALERT[AlertManager]
        SLACK[Slack]
        EMAIL[Email]
        WEBHOOK[Webhooks]
    end
    
    AH --> PROM
    EXT --> OTEL
    CLI --> APP_METRICS
    
    PROM --> GRAF
    OTEL --> GRAF
    APP_METRICS --> GRAF
    
    AH --> FLUENTD
    FLUENTD --> ELK
    ELK --> KIBANA
    
    PROM --> ALERT
    ALERT --> SLACK
    ALERT --> EMAIL
    ALERT --> WEBHOOK
```

### Core Components

1. **Metrics Collection**: Prometheus + OpenTelemetry
2. **Log Aggregation**: Fluentd + Elasticsearch + Kibana  
3. **Visualization**: Grafana with custom dashboards
4. **Alerting**: AlertManager with multi-channel notifications
5. **Tracing**: Jaeger for distributed tracing
6. **Security**: Custom security monitoring + SIEM integration

## Core Metrics Collection

### 1. Application Metrics

#### Agent Hive Custom Metrics
```python
# metrics/agent_hive_metrics.py
from prometheus_client import Counter, Histogram, Gauge, Summary
import time
from functools import wraps

# Core orchestration metrics
AGENT_COORDINATION_LATENCY = Histogram(
    'agent_hive_coordination_latency_seconds',
    'Time spent coordinating agents',
    buckets=(0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float('inf'))
)

ACTIVE_AGENTS = Gauge(
    'agent_hive_active_agents_total',
    'Number of active agents',
    ['agent_type', 'status']
)

TASKS_COMPLETED = Counter(
    'agent_hive_tasks_completed_total',
    'Total number of completed tasks',
    ['agent_type', 'status', 'priority']
)

RESOURCE_UTILIZATION = Gauge(
    'agent_hive_resource_utilization_percent',
    'Current resource utilization percentage',
    ['resource_type']
)

# Intelligence framework metrics
DECISION_CONFIDENCE = Histogram(
    'agent_hive_decision_confidence_score',
    'Confidence score of AI decisions',
    buckets=(0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0)
)

LEARNING_ACCURACY = Gauge(
    'agent_hive_learning_accuracy_percent',
    'Machine learning model accuracy',
    ['model_type']
)

# External API metrics
EXTERNAL_API_REQUESTS = Counter(
    'agent_hive_external_api_requests_total',
    'Total external API requests',
    ['service', 'method', 'status_code']
)

EXTERNAL_API_DURATION = Histogram(
    'agent_hive_external_api_duration_seconds',
    'External API request duration',
    ['service', 'method'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, float('inf'))
)

# Performance metrics
MEMORY_USAGE = Gauge(
    'agent_hive_memory_usage_bytes',
    'Memory usage by component',
    ['component']
)

CPU_USAGE = Gauge(
    'agent_hive_cpu_usage_percent',
    'CPU usage by component',
    ['component']
)

# Custom decorators for automatic instrumentation
def track_latency(metric_name=None):
    """Decorator to track function execution latency."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                AGENT_COORDINATION_LATENCY.observe(time.time() - start_time)
                return result
            except Exception as e:
                # Track errors
                TASKS_COMPLETED.labels(
                    agent_type='orchestrator',
                    status='error',
                    priority='high'
                ).inc()
                raise
        return wrapper
    return decorator

def track_resource_usage():
    """Track current resource usage."""
    import psutil
    
    # Memory usage
    memory = psutil.virtual_memory()
    MEMORY_USAGE.labels(component='system').set(memory.used)
    RESOURCE_UTILIZATION.labels(resource_type='memory').set(memory.percent)
    
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    CPU_USAGE.labels(component='system').set(cpu_percent)
    RESOURCE_UTILIZATION.labels(resource_type='cpu').set(cpu_percent)
    
    # Disk usage
    disk = psutil.disk_usage('/')
    RESOURCE_UTILIZATION.labels(resource_type='disk').set(
        (disk.used / disk.total) * 100
    )

# Usage example in orchestrator
class MonitoredOrchestrator:
    @track_latency('coordination')
    async def coordinate_agents(self, tasks):
        # Update active agents count
        ACTIVE_AGENTS.labels(agent_type='backend', status='active').set(5)
        
        # Your coordination logic here
        pass
        
        # Track completed tasks
        TASKS_COMPLETED.labels(
            agent_type='backend',
            status='completed',
            priority='medium'
        ).inc()
```

#### Prometheus Configuration
```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'agent-hive-prod'
    region: 'us-west-2'

rule_files:
  - "agent_hive_rules.yml"
  - "infrastructure_rules.yml"
  - "security_rules.yml"

scrape_configs:
  # Agent Hive application metrics
  - job_name: 'agent-hive-orchestrator'
    static_configs:
      - targets: ['agent-hive:8081']
    metrics_path: /metrics
    scrape_interval: 10s
    scrape_timeout: 5s
    
  # External API services
  - job_name: 'agent-hive-webhook-server'
    static_configs:
      - targets: ['webhook-server:8081']
    metrics_path: /metrics
    
  - job_name: 'agent-hive-api-gateway'
    static_configs:
      - targets: ['api-gateway:8082']
    metrics_path: /metrics
    
  - job_name: 'agent-hive-event-streaming'
    static_configs:
      - targets: ['event-streaming:8083']
    metrics_path: /metrics

  # Kubernetes metrics
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)

  # Node exporter for infrastructure metrics
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  # Redis metrics
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  # PostgreSQL metrics
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### 2. Infrastructure Metrics

#### Node Exporter Configuration
```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    restart: unless-stopped
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    networks:
      - monitoring

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: cadvisor
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:rw
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    privileged: true
    devices:
      - /dev/kmsg
    networks:
      - monitoring

  redis-exporter:
    image: oliver006/redis_exporter:latest
    container_name: redis-exporter
    restart: unless-stopped
    ports:
      - "9121:9121"
    environment:
      REDIS_ADDR: redis:6379
    networks:
      - monitoring

  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: postgres-exporter
    restart: unless-stopped
    ports:
      - "9187:9187"
    environment:
      DATA_SOURCE_NAME: "postgresql://postgres:password@postgres:5432/agent_hive?sslmode=disable"
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge
```

## Application Performance Monitoring

### 1. Custom Performance Tracking

#### Performance Monitor Component
```python
# monitoring/performance_monitor.py
import asyncio
import time
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class PerformanceMetrics:
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_io: Dict[str, int]
    active_agents: int
    task_queue_length: int
    coordination_latency_ms: float
    decision_confidence: float
    errors_per_minute: int

class PerformanceMonitor:
    def __init__(self, collection_interval: int = 30):
        self.collection_interval = collection_interval
        self.metrics_history: List[PerformanceMetrics] = []
        self.alert_thresholds = {
            'cpu_percent': 85,
            'memory_percent': 90,
            'disk_usage_percent': 95,
            'coordination_latency_ms': 500,
            'errors_per_minute': 10
        }
        self.running = False
        
    async def start_monitoring(self):
        """Start continuous performance monitoring."""
        self.running = True
        while self.running:
            metrics = await self.collect_metrics()
            self.metrics_history.append(metrics)
            
            # Keep only last 24 hours of data
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.metrics_history = [
                m for m in self.metrics_history 
                if m.timestamp > cutoff_time
            ]
            
            # Check for alerts
            await self.check_alerts(metrics)
            
            await asyncio.sleep(self.collection_interval)
    
    async def collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics."""
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        # Application metrics (mock implementation)
        active_agents = await self.get_active_agents_count()
        task_queue_length = await self.get_task_queue_length()
        coordination_latency = await self.get_coordination_latency()
        decision_confidence = await self.get_decision_confidence()
        errors_per_minute = await self.get_errors_per_minute()
        
        return PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_usage_percent=(disk.used / disk.total) * 100,
            network_io={
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv
            },
            active_agents=active_agents,
            task_queue_length=task_queue_length,
            coordination_latency_ms=coordination_latency,
            decision_confidence=decision_confidence,
            errors_per_minute=errors_per_minute
        )
    
    async def check_alerts(self, metrics: PerformanceMetrics):
        """Check metrics against alert thresholds."""
        alerts = []
        
        if metrics.cpu_percent > self.alert_thresholds['cpu_percent']:
            alerts.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
            
        if metrics.memory_percent > self.alert_thresholds['memory_percent']:
            alerts.append(f"High memory usage: {metrics.memory_percent:.1f}%")
            
        if metrics.coordination_latency_ms > self.alert_thresholds['coordination_latency_ms']:
            alerts.append(f"High coordination latency: {metrics.coordination_latency_ms:.1f}ms")
            
        if metrics.errors_per_minute > self.alert_thresholds['errors_per_minute']:
            alerts.append(f"High error rate: {metrics.errors_per_minute} errors/minute")
        
        if alerts:
            await self.send_alerts(alerts, metrics)
    
    async def send_alerts(self, alerts: List[str], metrics: PerformanceMetrics):
        """Send performance alerts."""
        alert_data = {
            'timestamp': metrics.timestamp.isoformat(),
            'alerts': alerts,
            'current_metrics': {
                'cpu_percent': metrics.cpu_percent,
                'memory_percent': metrics.memory_percent,
                'coordination_latency_ms': metrics.coordination_latency_ms,
                'errors_per_minute': metrics.errors_per_minute
            }
        }
        
        # Log alert
        print(f"PERFORMANCE ALERT: {json.dumps(alert_data, indent=2)}")
        
        # Send to monitoring system
        # Implementation depends on your alerting setup
    
    def get_performance_summary(self, hours: int = 1) -> Dict:
        """Get performance summary for the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.metrics_history 
            if m.timestamp > cutoff_time
        ]
        
        if not recent_metrics:
            return {"error": "No metrics available"}
        
        return {
            "time_period": f"Last {hours} hour(s)",
            "metrics_count": len(recent_metrics),
            "cpu_usage": {
                "avg": sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
                "max": max(m.cpu_percent for m in recent_metrics),
                "min": min(m.cpu_percent for m in recent_metrics)
            },
            "memory_usage": {
                "avg": sum(m.memory_percent for m in recent_metrics) / len(recent_metrics),
                "max": max(m.memory_percent for m in recent_metrics),
                "min": min(m.memory_percent for m in recent_metrics)
            },
            "coordination_latency": {
                "avg": sum(m.coordination_latency_ms for m in recent_metrics) / len(recent_metrics),
                "max": max(m.coordination_latency_ms for m in recent_metrics),
                "min": min(m.coordination_latency_ms for m in recent_metrics)
            },
            "active_agents": {
                "avg": sum(m.active_agents for m in recent_metrics) / len(recent_metrics),
                "max": max(m.active_agents for m in recent_metrics),
                "min": min(m.active_agents for m in recent_metrics)
            }
        }
    
    # Mock implementations - replace with actual application logic
    async def get_active_agents_count(self) -> int:
        return 5  # Replace with actual count
    
    async def get_task_queue_length(self) -> int:
        return 10  # Replace with actual queue length
    
    async def get_coordination_latency(self) -> float:
        return 150.0  # Replace with actual latency measurement
    
    async def get_decision_confidence(self) -> float:
        return 0.85  # Replace with actual confidence score
    
    async def get_errors_per_minute(self) -> int:
        return 2  # Replace with actual error count
```

### 2. OpenTelemetry Integration

#### Tracing Configuration
```python
# monitoring/tracing.py
from opentelemetry import trace, baggage
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

def setup_tracing():
    """Setup OpenTelemetry tracing for Agent Hive."""
    # Configure tracer provider
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    
    # Configure Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger",
        agent_port=6831,
    )
    
    # Add span processor
    span_processor = BatchSpanProcessor(jaeger_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    
    # Auto-instrument common libraries
    RequestsInstrumentor().instrument()
    AsyncioInstrumentor().instrument()
    LoggingInstrumentor().instrument()
    
    return tracer

# Usage in application code
tracer = setup_tracing()

class TracedOrchestrator:
    async def coordinate_agents(self, tasks):
        with tracer.start_as_current_span("coordinate_agents") as span:
            span.set_attribute("task_count", len(tasks))
            
            for i, task in enumerate(tasks):
                with tracer.start_as_current_span(f"process_task_{i}") as task_span:
                    task_span.set_attribute("task_type", task.type)
                    task_span.set_attribute("task_priority", task.priority)
                    
                    # Process task
                    result = await self.process_task(task)
                    task_span.set_attribute("task_result", result.status)
            
            span.set_attribute("coordination_status", "completed")
```

## Real-time Dashboards

### 1. Grafana Dashboard Configuration

#### Agent Hive Overview Dashboard
```json
{
  "dashboard": {
    "id": null,
    "title": "Agent Hive - Production Overview",
    "tags": ["agent-hive", "production"],
    "timezone": "UTC",
    "refresh": "30s",
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "panels": [
      {
        "id": 1,
        "title": "System Health Status",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=\"agent-hive-orchestrator\"}",
            "legendFormat": "Orchestrator",
            "refId": "A"
          },
          {
            "expr": "up{job=\"agent-hive-webhook-server\"}",
            "legendFormat": "Webhook Server",
            "refId": "B"
          },
          {
            "expr": "up{job=\"agent-hive-api-gateway\"}",
            "legendFormat": "API Gateway",
            "refId": "C"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "thresholds": {
              "steps": [
                {"color": "red", "value": 0},
                {"color": "green", "value": 1}
              ]
            }
          }
        },
        "gridPos": {"h": 4, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Active Agents",
        "type": "graph",
        "targets": [
          {
            "expr": "agent_hive_active_agents_total",
            "legendFormat": "{{agent_type}} - {{status}}",
            "refId": "A"
          }
        ],
        "yAxes": [
          {
            "label": "Count",
            "min": 0
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4}
      },
      {
        "id": 3,
        "title": "Task Completion Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(agent_hive_tasks_completed_total[5m])",
            "legendFormat": "{{agent_type}} - {{status}}",
            "refId": "A"
          }
        ],
        "yAxes": [
          {
            "label": "Tasks/sec",
            "min": 0
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4}
      },
      {
        "id": 4,
        "title": "Coordination Latency",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, agent_hive_coordination_latency_seconds)",
            "legendFormat": "95th percentile",
            "refId": "A"
          },
          {
            "expr": "histogram_quantile(0.50, agent_hive_coordination_latency_seconds)",
            "legendFormat": "50th percentile",
            "refId": "B"
          }
        ],
        "yAxes": [
          {
            "label": "Seconds",
            "min": 0
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 12}
      },
      {
        "id": 5,
        "title": "Resource Utilization",
        "type": "graph",
        "targets": [
          {
            "expr": "agent_hive_resource_utilization_percent",
            "legendFormat": "{{resource_type}}",
            "refId": "A"
          }
        ],
        "yAxes": [
          {
            "label": "Percent",
            "min": 0,
            "max": 100
          }
        ],
        "thresholds": [
          {"value": 80, "colorMode": "critical", "op": "gt"},
          {"value": 60, "colorMode": "warning", "op": "gt"}
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 12}
      },
      {
        "id": 6,
        "title": "External API Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, agent_hive_external_api_duration_seconds)",
            "legendFormat": "{{service}} - 95th percentile",
            "refId": "A"
          }
        ],
        "yAxes": [
          {
            "label": "Seconds",
            "min": 0
          }
        ],
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 20}
      }
    ]
  }
}
```

### 2. Custom Dashboard Scripts

#### Dashboard Generator
```python
# scripts/generate_dashboards.py
import json
from typing import List, Dict

class DashboardGenerator:
    def __init__(self):
        self.panels = []
        self.panel_id = 1
        
    def add_system_health_panel(self) -> Dict:
        """Add system health status panel."""
        panel = {
            "id": self.panel_id,
            "title": "System Health Status",
            "type": "stat",
            "targets": [
                {
                    "expr": "up{job=\"agent-hive-orchestrator\"}",
                    "legendFormat": "Orchestrator",
                    "refId": "A"
                },
                {
                    "expr": "up{job=\"agent-hive-webhook-server\"}",
                    "legendFormat": "Webhook Server", 
                    "refId": "B"
                },
                {
                    "expr": "up{job=\"agent-hive-api-gateway\"}",
                    "legendFormat": "API Gateway",
                    "refId": "C"
                },
                {
                    "expr": "up{job=\"agent-hive-event-streaming\"}",
                    "legendFormat": "Event Streaming",
                    "refId": "D"
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "thresholds": {
                        "steps": [
                            {"color": "red", "value": 0},
                            {"color": "green", "value": 1}
                        ]
                    },
                    "mappings": [
                        {"options": {"0": {"text": "DOWN"}}, "type": "value"},
                        {"options": {"1": {"text": "UP"}}, "type": "value"}
                    ]
                }
            },
            "gridPos": {"h": 4, "w": 24, "x": 0, "y": 0}
        }
        self.panel_id += 1
        return panel
    
    def add_performance_overview_panel(self) -> Dict:
        """Add performance overview panel."""
        panel = {
            "id": self.panel_id,
            "title": "Performance Overview",
            "type": "graph",
            "targets": [
                {
                    "expr": "agent_hive_resource_utilization_percent{resource_type=\"cpu\"}",
                    "legendFormat": "CPU Usage %",
                    "refId": "A"
                },
                {
                    "expr": "agent_hive_resource_utilization_percent{resource_type=\"memory\"}",
                    "legendFormat": "Memory Usage %",
                    "refId": "B"
                },
                {
                    "expr": "histogram_quantile(0.95, agent_hive_coordination_latency_seconds) * 1000",
                    "legendFormat": "Coordination Latency (ms)",
                    "refId": "C"
                }
            ],
            "yAxes": [
                {
                    "label": "Percent / Milliseconds",
                    "min": 0,
                    "max": 100
                }
            ],
            "thresholds": [
                {"value": 80, "colorMode": "critical", "op": "gt"},
                {"value": 60, "colorMode": "warning", "op": "gt"}
            ],
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4}
        }
        self.panel_id += 1
        return panel
    
    def generate_dashboard(self, title: str = "Agent Hive - Production Dashboard") -> Dict:
        """Generate complete dashboard configuration."""
        dashboard = {
            "dashboard": {
                "id": None,
                "title": title,
                "tags": ["agent-hive", "production", "monitoring"],
                "timezone": "UTC",
                "refresh": "30s",
                "time": {"from": "now-1h", "to": "now"},
                "panels": [
                    self.add_system_health_panel(),
                    self.add_performance_overview_panel(),
                    # Add more panels as needed
                ]
            }
        }
        return dashboard
    
    def export_dashboard(self, filename: str):
        """Export dashboard to JSON file."""
        dashboard = self.generate_dashboard()
        with open(filename, 'w') as f:
            json.dump(dashboard, f, indent=2)

# Usage
if __name__ == "__main__":
    generator = DashboardGenerator()
    generator.export_dashboard("agent_hive_production_dashboard.json")
```

## Alerting and Notification

### 1. AlertManager Configuration

```yaml
# alertmanager/alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@agent-hive.com'
  smtp_auth_username: 'alerts@agent-hive.com'
  smtp_auth_password: 'your-email-password'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h
  receiver: 'default'
  routes:
  - match:
      severity: critical
    receiver: 'critical-alerts'
  - match:
      severity: warning
    receiver: 'warning-alerts'
  - match:
      alertname: AgentHiveDown
    receiver: 'agent-hive-down'

receivers:
- name: 'default'
  email_configs:
  - to: 'ops-team@agent-hive.com'
    subject: 'Agent Hive Alert: {{ .GroupLabels.alertname }}'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      Labels: {{ .Labels }}
      {{ end }}

- name: 'critical-alerts'
  email_configs:
  - to: 'ops-team@agent-hive.com,on-call@agent-hive.com'
    subject: '🚨 CRITICAL Alert: {{ .GroupLabels.alertname }}'
    body: |
      CRITICAL ALERT TRIGGERED
      
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      Severity: {{ .Labels.severity }}
      Time: {{ .StartsAt }}
      Labels: {{ .Labels }}
      {{ end }}
  
  slack_configs:
  - api_url: 'YOUR_SLACK_WEBHOOK_URL'
    channel: '#alerts-critical'
    title: '🚨 Critical Agent Hive Alert'
    text: |
      {{ range .Alerts }}
      *Alert:* {{ .Annotations.summary }}
      *Description:* {{ .Annotations.description }}
      *Severity:* {{ .Labels.severity }}
      {{ end }}

- name: 'warning-alerts'
  slack_configs:
  - api_url: 'YOUR_SLACK_WEBHOOK_URL'
    channel: '#alerts-warning'
    title: '⚠️ Agent Hive Warning'
    text: |
      {{ range .Alerts }}
      *Alert:* {{ .Annotations.summary }}
      *Description:* {{ .Annotations.description }}
      {{ end }}

- name: 'agent-hive-down'
  email_configs:
  - to: 'ops-team@agent-hive.com,cto@agent-hive.com'
    subject: '🔥 URGENT: Agent Hive Service Down'
    body: |
      URGENT: Agent Hive service is DOWN
      
      Immediate action required!
      
      {{ range .Alerts }}
      Service: {{ .Labels.job }}
      Instance: {{ .Labels.instance }}
      Time: {{ .StartsAt }}
      {{ end }}
  
  webhook_configs:
  - url: 'https://hooks.slack.com/services/YOUR/URGENT/WEBHOOK'
    send_resolved: true

inhibit_rules:
- source_match:
    severity: 'critical'
  target_match:
    severity: 'warning'
  equal: ['alertname', 'cluster', 'service']
```

### 2. Alert Rules

```yaml
# prometheus/agent_hive_rules.yml
groups:
- name: agent_hive_alerts
  interval: 30s
  rules:
  
  # Service availability alerts
  - alert: AgentHiveDown
    expr: up{job=~"agent-hive.*"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Agent Hive service {{ $labels.job }} is down"
      description: "Agent Hive service {{ $labels.job }} on instance {{ $labels.instance }} has been down for more than 1 minute."
  
  # Performance alerts
  - alert: HighCoordinationLatency
    expr: histogram_quantile(0.95, agent_hive_coordination_latency_seconds) > 0.5
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High coordination latency detected"
      description: "95th percentile coordination latency is {{ $value }}s for more than 2 minutes."
  
  - alert: CriticalCoordinationLatency
    expr: histogram_quantile(0.95, agent_hive_coordination_latency_seconds) > 1.0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Critical coordination latency detected"
      description: "95th percentile coordination latency is {{ $value }}s for more than 1 minute."
  
  # Resource alerts
  - alert: HighCPUUsage
    expr: agent_hive_resource_utilization_percent{resource_type="cpu"} > 85
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage detected"
      description: "CPU usage is {{ $value }}% for more than 5 minutes."
  
  - alert: HighMemoryUsage
    expr: agent_hive_resource_utilization_percent{resource_type="memory"} > 90
    for: 3m
    labels:
      severity: critical
    annotations:
      summary: "High memory usage detected"
      description: "Memory usage is {{ $value }}% for more than 3 minutes."
  
  # Agent alerts
  - alert: LowActiveAgents
    expr: sum(agent_hive_active_agents_total) < 3
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "Low number of active agents"
      description: "Only {{ $value }} agents are currently active."
  
  - alert: NoActiveAgents
    expr: sum(agent_hive_active_agents_total) == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "No active agents available"
      description: "No agents are currently active. System may be down."
  
  # Task processing alerts
  - alert: HighTaskFailureRate
    expr: rate(agent_hive_tasks_completed_total{status="error"}[5m]) / rate(agent_hive_tasks_completed_total[5m]) > 0.1
    for: 3m
    labels:
      severity: warning
    annotations:
      summary: "High task failure rate"
      description: "Task failure rate is {{ $value | humanizePercentage }} over the last 5 minutes."
  
  # External API alerts
  - alert: ExternalAPIHighLatency
    expr: histogram_quantile(0.95, agent_hive_external_api_duration_seconds) > 5.0
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High external API latency"
      description: "95th percentile external API latency is {{ $value }}s for service {{ $labels.service }}."
  
  - alert: ExternalAPIHighErrorRate
    expr: rate(agent_hive_external_api_requests_total{status_code=~"5.."}[5m]) / rate(agent_hive_external_api_requests_total[5m]) > 0.05
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "High external API error rate"
      description: "External API error rate is {{ $value | humanizePercentage }} for service {{ $labels.service }}."
  
  # Intelligence framework alerts
  - alert: LowDecisionConfidence
    expr: avg(agent_hive_decision_confidence_score) < 0.7
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Low AI decision confidence"
      description: "Average decision confidence is {{ $value }} for more than 5 minutes."
  
  - alert: MachineLearningAccuracyDrop
    expr: agent_hive_learning_accuracy_percent < 80
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Machine learning accuracy drop"
      description: "ML model {{ $labels.model_type }} accuracy is {{ $value }}% for more than 10 minutes."
```

### 3. Custom Notification Scripts

```python
# scripts/custom_alerts.py
import asyncio
import aiohttp
import json
from datetime import datetime
from typing import List, Dict

class AlertNotifier:
    def __init__(self, config: Dict):
        self.config = config
        self.slack_webhook = config.get('slack_webhook')
        self.email_smtp = config.get('email_smtp')
        self.webhook_urls = config.get('webhook_urls', [])
    
    async def send_slack_alert(self, alert: Dict):
        """Send alert to Slack."""
        if not self.slack_webhook:
            return
        
        payload = {
            "channel": "#alerts",
            "username": "Agent Hive Monitor",
            "icon_emoji": ":warning:",
            "attachments": [
                {
                    "color": "danger" if alert['severity'] == 'critical' else "warning",
                    "title": f"Agent Hive Alert: {alert['name']}",
                    "text": alert['description'],
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert['severity'],
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": alert['timestamp'],
                            "short": True
                        }
                    ],
                    "footer": "Agent Hive Monitoring",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            await session.post(self.slack_webhook, json=payload)
    
    async def send_webhook_alerts(self, alert: Dict):
        """Send alert to configured webhooks."""
        for webhook_url in self.webhook_urls:
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(webhook_url, json=alert)
            except Exception as e:
                print(f"Failed to send webhook alert to {webhook_url}: {e}")
    
    async def process_alert(self, alert: Dict):
        """Process and send alert through all configured channels."""
        tasks = []
        
        if self.slack_webhook:
            tasks.append(self.send_slack_alert(alert))
        
        if self.webhook_urls:
            tasks.append(self.send_webhook_alerts(alert))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

# Usage example
async def main():
    config = {
        'slack_webhook': 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL',
        'webhook_urls': ['https://your-monitoring-system.com/alerts']
    }
    
    notifier = AlertNotifier(config)
    
    alert = {
        'name': 'HighCoordinationLatency',
        'severity': 'warning',
        'description': 'Coordination latency is above threshold',
        'timestamp': datetime.now().isoformat(),
        'metrics': {
            'latency_ms': 750,
            'threshold_ms': 500
        }
    }
    
    await notifier.process_alert(alert)

if __name__ == "__main__":
    asyncio.run(main())
```

This comprehensive monitoring guide provides:

1. **Complete metrics collection** with custom Agent Hive metrics
2. **Infrastructure monitoring** with Prometheus, Node Exporter, and custom exporters
3. **Real-time dashboards** with Grafana configurations
4. **Intelligent alerting** with AlertManager and custom notification systems
5. **Performance tracking** with detailed monitoring components
6. **Distributed tracing** with OpenTelemetry and Jaeger

The monitoring system is designed to provide full observability into Agent Hive production deployments with proactive alerting and comprehensive performance insights.

---

**Last Updated**: July 19, 2025  
**Status**: Production Ready  
**Estimated Setup Time**: 2-4 hours for complete monitoring stack