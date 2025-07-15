"""
Monitoring and Alerting System for Integration Agent

Provides comprehensive monitoring, metrics collection, and alerting
for all integration components.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import psutil
import threading
from collections import deque, defaultdict

from .api_gateway import ApiGateway
from .service_discovery import ServiceDiscovery
from .github_client import GitHubClient
from .slack_client import SlackClient
from .integration_manager import IntegrationManager


logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricData:
    """Metric data point."""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str]
    metric_type: MetricType


@dataclass
class AlertRule:
    """Alert rule definition."""
    name: str
    metric_name: str
    condition: str  # e.g., "> 0.8", "< 0.1"
    threshold: float
    duration: int  # seconds
    level: AlertLevel
    enabled: bool = True
    cooldown: int = 300  # seconds between alerts


@dataclass
class AlertEvent:
    """Alert event."""
    rule_name: str
    level: AlertLevel
    message: str
    timestamp: datetime
    metric_value: float
    tags: Dict[str, str]


class MetricsCollector:
    """Collects and stores metrics from various sources."""
    
    def __init__(self, max_metrics: int = 10000):
        self.metrics: deque = deque(maxlen=max_metrics)
        self.metric_index: Dict[str, List[MetricData]] = defaultdict(list)
        self.lock = threading.Lock()
        
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None, 
                     metric_type: MetricType = MetricType.GAUGE):
        """Record a metric data point."""
        metric = MetricData(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            metric_type=metric_type
        )
        
        with self.lock:
            self.metrics.append(metric)
            self.metric_index[name].append(metric)
            
            # Keep only recent metrics per name
            if len(self.metric_index[name]) > 1000:
                self.metric_index[name] = self.metric_index[name][-1000:]
    
    def get_metrics(self, name: Optional[str] = None, 
                   since: Optional[datetime] = None) -> List[MetricData]:
        """Get metrics, optionally filtered by name and time."""
        with self.lock:
            if name:
                metrics = self.metric_index.get(name, [])
            else:
                metrics = list(self.metrics)
            
            if since:
                metrics = [m for m in metrics if m.timestamp >= since]
            
            return metrics
    
    def get_latest_metric(self, name: str) -> Optional[MetricData]:
        """Get the latest metric value for a name."""
        with self.lock:
            metrics = self.metric_index.get(name, [])
            return metrics[-1] if metrics else None
    
    def get_metric_summary(self, name: str, duration: int = 300) -> Dict[str, Any]:
        """Get metric summary for the last duration seconds."""
        since = datetime.now() - timedelta(seconds=duration)
        metrics = self.get_metrics(name, since)
        
        if not metrics:
            return {"count": 0, "avg": 0, "min": 0, "max": 0}
        
        values = [m.value for m in metrics]
        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "latest": values[-1] if values else 0
        }


class AlertManager:
    """Manages alert rules and notifications."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.alert_rules: Dict[str, AlertRule] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.alert_handlers: List[Callable] = []
        
    def add_alert_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self.alert_rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_alert_rule(self, rule_name: str):
        """Remove an alert rule."""
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            logger.info(f"Removed alert rule: {rule_name}")
    
    def add_alert_handler(self, handler: Callable):
        """Add an alert handler function."""
        self.alert_handlers.append(handler)
    
    async def check_alerts(self):
        """Check all alert rules and trigger alerts if needed."""
        for rule_name, rule in self.alert_rules.items():
            if not rule.enabled:
                continue
                
            try:
                await self._check_alert_rule(rule)
            except Exception as e:
                logger.error(f"Error checking alert rule {rule_name}: {e}")
    
    async def _check_alert_rule(self, rule: AlertRule):
        """Check a single alert rule."""
        # Check cooldown
        if rule.name in self.alert_cooldowns:
            cooldown_until = self.alert_cooldowns[rule.name] + timedelta(seconds=rule.cooldown)
            if datetime.now() < cooldown_until:
                return
        
        # Get metric summary
        summary = self.metrics_collector.get_metric_summary(rule.metric_name, rule.duration)
        
        if summary["count"] == 0:
            return
        
        metric_value = summary["latest"]
        
        # Check condition
        condition_met = self._evaluate_condition(metric_value, rule.condition, rule.threshold)
        
        if condition_met:
            # Create alert event
            alert_event = AlertEvent(
                rule_name=rule.name,
                level=rule.level,
                message=f"Alert: {rule.name} - {rule.metric_name} {rule.condition} {rule.threshold} (current: {metric_value})",
                timestamp=datetime.now(),
                metric_value=metric_value,
                tags={"rule": rule.name, "metric": rule.metric_name}
            )
            
            # Record alert
            self.alert_history.append(alert_event)
            self.alert_cooldowns[rule.name] = datetime.now()
            
            # Trigger alert handlers
            for handler in self.alert_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(alert_event)
                    else:
                        handler(alert_event)
                except Exception as e:
                    logger.error(f"Error in alert handler: {e}")
    
    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Evaluate an alert condition."""
        condition = condition.strip()
        
        if condition == ">":
            return value > threshold
        elif condition == ">=":
            return value >= threshold
        elif condition == "<":
            return value < threshold
        elif condition == "<=":
            return value <= threshold
        elif condition == "==":
            return value == threshold
        elif condition == "!=":
            return value != threshold
        else:
            logger.warning(f"Unknown condition: {condition}")
            return False
    
    def get_alert_history(self, limit: int = 100) -> List[AlertEvent]:
        """Get recent alert history."""
        return list(self.alert_history)[-limit:]


class SystemMonitor:
    """Monitors system resources and health."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start system monitoring."""
        if self.running:
            return
            
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("System monitor started")
    
    async def stop(self):
        """Stop system monitoring."""
        if not self.running:
            return
            
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("System monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(10)  # Collect every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in system monitor: {e}")
                await asyncio.sleep(5)
    
    async def _collect_system_metrics(self):
        """Collect system metrics."""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        self.metrics_collector.record_metric("system.cpu.percent", cpu_percent)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        self.metrics_collector.record_metric("system.memory.percent", memory.percent)
        self.metrics_collector.record_metric("system.memory.available", memory.available)
        self.metrics_collector.record_metric("system.memory.used", memory.used)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        self.metrics_collector.record_metric("system.disk.percent", disk_percent)
        self.metrics_collector.record_metric("system.disk.free", disk.free)
        self.metrics_collector.record_metric("system.disk.used", disk.used)
        
        # Network metrics
        network = psutil.net_io_counters()
        self.metrics_collector.record_metric("system.network.bytes_sent", network.bytes_sent, metric_type=MetricType.COUNTER)
        self.metrics_collector.record_metric("system.network.bytes_recv", network.bytes_recv, metric_type=MetricType.COUNTER)
        
        # Process metrics
        process = psutil.Process()
        self.metrics_collector.record_metric("process.cpu.percent", process.cpu_percent())
        self.metrics_collector.record_metric("process.memory.percent", process.memory_percent())
        self.metrics_collector.record_metric("process.memory.rss", process.memory_info().rss)
        self.metrics_collector.record_metric("process.threads", process.num_threads())


class IntegrationMonitor:
    """Monitors integration components."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.components: Dict[str, Any] = {}
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        
    def register_component(self, name: str, component: Any):
        """Register a component for monitoring."""
        self.components[name] = component
        logger.info(f"Registered component for monitoring: {name}")
    
    async def start(self):
        """Start integration monitoring."""
        if self.running:
            return
            
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Integration monitor started")
    
    async def stop(self):
        """Stop integration monitoring."""
        if not self.running:
            return
            
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Integration monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                await self._collect_integration_metrics()
                await asyncio.sleep(30)  # Collect every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in integration monitor: {e}")
                await asyncio.sleep(10)
    
    async def _collect_integration_metrics(self):
        """Collect integration metrics."""
        for component_name, component in self.components.items():
            try:
                await self._collect_component_metrics(component_name, component)
            except Exception as e:
                logger.error(f"Error collecting metrics for {component_name}: {e}")
    
    async def _collect_component_metrics(self, name: str, component: Any):
        """Collect metrics for a specific component."""
        tags = {"component": name}
        
        # API Gateway metrics
        if isinstance(component, ApiGateway):
            info = component.get_gateway_info()
            self.metrics_collector.record_metric(
                "integration.api_gateway.requests_total",
                info.get("total_requests", 0),
                tags,
                MetricType.COUNTER
            )
            
            # Health status
            health_status = 1 if info.get("server_status") == "running" else 0
            self.metrics_collector.record_metric(
                "integration.api_gateway.health",
                health_status,
                tags
            )
            
            # Rate limiting metrics
            rate_limit_stats = info.get("rate_limiting", {}).get("stats", {})
            if rate_limit_stats:
                self.metrics_collector.record_metric(
                    "integration.api_gateway.rate_limit_hits",
                    rate_limit_stats.get("rate_limit_hits", 0),
                    tags,
                    MetricType.COUNTER
                )
        
        # Service Discovery metrics
        elif isinstance(component, ServiceDiscovery):
            stats = component.get_discovery_stats()
            self.metrics_collector.record_metric(
                "integration.service_discovery.total_services",
                stats.get("total_services", 0),
                tags
            )
            self.metrics_collector.record_metric(
                "integration.service_discovery.healthy_services",
                stats.get("healthy_services", 0),
                tags
            )
            
            # Health status
            health_status = 1 if stats.get("running") else 0
            self.metrics_collector.record_metric(
                "integration.service_discovery.health",
                health_status,
                tags
            )
        
        # GitHub Client metrics
        elif isinstance(component, GitHubClient):
            stats = component.get_client_stats()
            client_stats = stats.get("stats", {})
            
            self.metrics_collector.record_metric(
                "integration.github.requests_total",
                client_stats.get("total_requests", 0),
                tags,
                MetricType.COUNTER
            )
            self.metrics_collector.record_metric(
                "integration.github.requests_failed",
                client_stats.get("failed_requests", 0),
                tags,
                MetricType.COUNTER
            )
            
            # Rate limit metrics
            rate_limit = stats.get("rate_limit", {})
            self.metrics_collector.record_metric(
                "integration.github.rate_limit_remaining",
                rate_limit.get("remaining", 0),
                tags
            )
        
        # Slack Client metrics
        elif isinstance(component, SlackClient):
            stats = component.get_client_stats()
            client_stats = stats.get("stats", {})
            
            self.metrics_collector.record_metric(
                "integration.slack.messages_sent",
                client_stats.get("messages_sent", 0),
                tags,
                MetricType.COUNTER
            )
            self.metrics_collector.record_metric(
                "integration.slack.events_processed",
                client_stats.get("events_processed", 0),
                tags,
                MetricType.COUNTER
            )
        
        # Integration Manager metrics
        elif isinstance(component, IntegrationManager):
            status = component.get_integration_status()
            
            # Count healthy integrations
            healthy_count = sum(1 for integration in status.get("integrations", {}).values() 
                              if integration.get("status") == "connected")
            
            self.metrics_collector.record_metric(
                "integration.manager.healthy_integrations",
                healthy_count,
                tags
            )
            
            # Total events processed
            stats = status.get("stats", {})
            self.metrics_collector.record_metric(
                "integration.manager.events_processed",
                stats.get("total_events_processed", 0),
                tags,
                MetricType.COUNTER
            )


class MonitoringEndpoints:
    """HTTP endpoints for monitoring and metrics."""
    
    def __init__(self, metrics_collector: MetricsCollector, alert_manager: AlertManager):
        self.metrics_collector = metrics_collector
        self.alert_manager = alert_manager
        
    async def health_handler(self, request) -> Dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    
    async def ready_handler(self, request) -> Dict[str, Any]:
        """Readiness check endpoint."""
        # Check if all components are ready
        cpu_metric = self.metrics_collector.get_latest_metric("system.cpu.percent")
        memory_metric = self.metrics_collector.get_latest_metric("system.memory.percent")
        
        is_ready = (
            cpu_metric is not None and cpu_metric.value < 90 and
            memory_metric is not None and memory_metric.value < 90
        )
        
        return {
            "status": "ready" if is_ready else "not_ready",
            "timestamp": datetime.now().isoformat(),
            "checks": {
                "cpu": cpu_metric.value if cpu_metric else None,
                "memory": memory_metric.value if memory_metric else None
            }
        }
    
    async def metrics_handler(self, request) -> str:
        """Prometheus metrics endpoint."""
        metrics_text = []
        
        # Get all metrics
        metrics = self.metrics_collector.get_metrics()
        
        # Group by name
        metric_groups = defaultdict(list)
        for metric in metrics:
            metric_groups[metric.name].append(metric)
        
        # Format for Prometheus
        for name, metric_list in metric_groups.items():
            latest_metric = metric_list[-1]
            
            # Format metric name
            prom_name = name.replace(".", "_")
            
            # Add help and type
            metrics_text.append(f"# HELP {prom_name} {name}")
            metrics_text.append(f"# TYPE {prom_name} {latest_metric.metric_type.value}")
            
            # Add metric value with tags
            tags_str = ""
            if latest_metric.tags:
                tag_pairs = [f'{k}="{v}"' for k, v in latest_metric.tags.items()]
                tags_str = "{" + ",".join(tag_pairs) + "}"
            
            metrics_text.append(f"{prom_name}{tags_str} {latest_metric.value}")
        
        return "\n".join(metrics_text)
    
    async def alerts_handler(self, request) -> Dict[str, Any]:
        """Alerts endpoint."""
        return {
            "alerts": [asdict(alert) for alert in self.alert_manager.get_alert_history()],
            "rules": {
                name: asdict(rule) for name, rule in self.alert_manager.alert_rules.items()
            }
        }
    
    async def metrics_json_handler(self, request) -> Dict[str, Any]:
        """JSON metrics endpoint."""
        metrics = self.metrics_collector.get_metrics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": [
                {
                    "name": metric.name,
                    "value": metric.value,
                    "timestamp": metric.timestamp.isoformat(),
                    "tags": metric.tags,
                    "type": metric.metric_type.value
                }
                for metric in metrics[-100:]  # Last 100 metrics
            ]
        }


class MonitoringServer:
    """Complete monitoring server with metrics, alerts, and health checks."""
    
    def __init__(self, port: int = 9090):
        self.port = port
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager(self.metrics_collector)
        self.system_monitor = SystemMonitor(self.metrics_collector)
        self.integration_monitor = IntegrationMonitor(self.metrics_collector)
        self.endpoints = MonitoringEndpoints(self.metrics_collector, self.alert_manager)
        
        self.running = False
        self.server = None
        self.alert_task: Optional[asyncio.Task] = None
        
        # Set up default alert rules
        self._setup_default_alerts()
        
    def _setup_default_alerts(self):
        """Set up default alert rules."""
        default_rules = [
            AlertRule(
                name="high_cpu_usage",
                metric_name="system.cpu.percent",
                condition=">",
                threshold=80.0,
                duration=300,
                level=AlertLevel.WARNING
            ),
            AlertRule(
                name="critical_cpu_usage",
                metric_name="system.cpu.percent",
                condition=">",
                threshold=90.0,
                duration=60,
                level=AlertLevel.CRITICAL
            ),
            AlertRule(
                name="high_memory_usage",
                metric_name="system.memory.percent",
                condition=">",
                threshold=85.0,
                duration=300,
                level=AlertLevel.WARNING
            ),
            AlertRule(
                name="critical_memory_usage",
                metric_name="system.memory.percent",
                condition=">",
                threshold=95.0,
                duration=60,
                level=AlertLevel.CRITICAL
            ),
            AlertRule(
                name="high_disk_usage",
                metric_name="system.disk.percent",
                condition=">",
                threshold=90.0,
                duration=600,
                level=AlertLevel.WARNING
            ),
            AlertRule(
                name="integration_service_down",
                metric_name="integration.service_discovery.health",
                condition="<",
                threshold=1.0,
                duration=60,
                level=AlertLevel.ERROR
            )
        ]
        
        for rule in default_rules:
            self.alert_manager.add_alert_rule(rule)
    
    def register_component(self, name: str, component: Any):
        """Register a component for monitoring."""
        self.integration_monitor.register_component(name, component)
    
    def add_alert_handler(self, handler: Callable):
        """Add a custom alert handler."""
        self.alert_manager.add_alert_handler(handler)
    
    async def start(self):
        """Start the monitoring server."""
        if self.running:
            return
            
        self.running = True
        
        # Start monitors
        await self.system_monitor.start()
        await self.integration_monitor.start()
        
        # Start alert checking
        self.alert_task = asyncio.create_task(self._alert_loop())
        
        # Start HTTP server
        from aiohttp import web
        
        app = web.Application()
        app.router.add_get("/health", self._wrap_handler(self.endpoints.health_handler))
        app.router.add_get("/ready", self._wrap_handler(self.endpoints.ready_handler))
        app.router.add_get("/metrics", self._wrap_text_handler(self.endpoints.metrics_handler))
        app.router.add_get("/alerts", self._wrap_handler(self.endpoints.alerts_handler))
        app.router.add_get("/metrics.json", self._wrap_handler(self.endpoints.metrics_json_handler))
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self.port)
        await site.start()
        
        self.server = runner
        
        logger.info(f"Monitoring server started on port {self.port}")
    
    async def stop(self):
        """Stop the monitoring server."""
        if not self.running:
            return
            
        self.running = False
        
        # Stop monitors
        await self.system_monitor.stop()
        await self.integration_monitor.stop()
        
        # Stop alert checking
        if self.alert_task:
            self.alert_task.cancel()
            try:
                await self.alert_task
            except asyncio.CancelledError:
                pass
        
        # Stop HTTP server
        if self.server:
            await self.server.cleanup()
        
        logger.info("Monitoring server stopped")
    
    async def _alert_loop(self):
        """Alert checking loop."""
        while self.running:
            try:
                await self.alert_manager.check_alerts()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert loop: {e}")
                await asyncio.sleep(10)
    
    def _wrap_handler(self, handler):
        """Wrap handler to return JSON response."""
        async def wrapped_handler(request):
            try:
                result = await handler(request)
                from aiohttp import web
                return web.json_response(result)
            except Exception as e:
                logger.error(f"Error in handler: {e}")
                from aiohttp import web
                return web.json_response({"error": str(e)}, status=500)
        return wrapped_handler
    
    def _wrap_text_handler(self, handler):
        """Wrap handler to return text response."""
        async def wrapped_handler(request):
            try:
                result = await handler(request)
                from aiohttp import web
                return web.Response(text=result, content_type="text/plain")
            except Exception as e:
                logger.error(f"Error in handler: {e}")
                from aiohttp import web
                return web.Response(text=f"Error: {e}", status=500)
        return wrapped_handler


# Example usage
async def example_monitoring_setup():
    """Example of how to set up monitoring."""
    # Create monitoring server
    monitoring_server = MonitoringServer(port=9090)
    
    # Add custom alert handler
    async def slack_alert_handler(alert_event: AlertEvent):
        print(f"ALERT: {alert_event.message}")
        # Here you would send to Slack
    
    monitoring_server.add_alert_handler(slack_alert_handler)
    
    # Register components (these would be your actual components)
    # monitoring_server.register_component("api_gateway", api_gateway)
    # monitoring_server.register_component("service_discovery", service_discovery)
    
    # Start monitoring
    await monitoring_server.start()
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await monitoring_server.stop()


if __name__ == "__main__":
    asyncio.run(example_monitoring_setup())