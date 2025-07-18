"""
Monitoring System for Integration Agent Components

Provides comprehensive monitoring, metrics collection, and alerting
for all integration agent components and external services.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import uuid
import psutil


logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class MetricData:
    """Metric data point."""
    name: str
    value: float
    metric_type: MetricType
    tags: Dict[str, str]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "tags": self.tags,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class Alert:
    """Alert data structure."""
    id: str
    name: str
    severity: AlertSeverity
    message: str
    component: str
    metric_name: str
    threshold: float
    current_value: float
    timestamp: datetime
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "severity": self.severity.value,
            "message": self.message,
            "component": self.component,
            "metric_name": self.metric_name,
            "threshold": self.threshold,
            "current_value": self.current_value,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved
        }


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    metric_name: str
    threshold: float
    comparison: str  # "gt", "lt", "eq"
    severity: AlertSeverity
    component: str
    enabled: bool = True
    cooldown_minutes: int = 5


class MonitoringSystem:
    """
    Comprehensive monitoring system for integration components.

    Provides metrics collection, alerting, health monitoring,
    and performance tracking for all integration services.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize monitoring system.

        Args:
            config: Monitoring configuration
        """
        self.config = config or {}
        self.metrics: Dict[str, List[MetricData]] = {}
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: Dict[str, AlertRule] = {}
        self.alert_handlers: List[Callable] = []

        # Configuration
        self.retention_hours = self.config.get("retention_hours", 24)
        self.collection_interval = self.config.get("collection_interval", 60)
        self.alert_check_interval = self.config.get("alert_check_interval", 30)

        # System monitoring
        self.system_metrics_enabled = self.config.get("system_metrics", True)
        self.component_health: Dict[str, Dict[str, Any]] = {}

        # Background tasks
        self._collection_task: Optional[asyncio.Task] = None
        self._alert_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # Default alert rules
        self._setup_default_alert_rules()

        logger.info("MonitoringSystem initialized")

    async def start(self) -> None:
        """Start the monitoring system."""
        if self._running:
            logger.warning("Monitoring system already running")
            return

        self._running = True

        # Start background tasks
        self._collection_task = asyncio.create_task(self._metrics_collection_loop())
        self._alert_task = asyncio.create_task(self._alert_processing_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("Monitoring system started")

    async def stop(self) -> None:
        """Stop the monitoring system."""
        if not self._running:
            return

        self._running = False

        # Cancel background tasks
        tasks = [self._collection_task, self._alert_task, self._cleanup_task]
        for task in tasks:
            if task:
                task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("Monitoring system stopped")

    def record_metric(self, name: str, value: float, metric_type: MetricType = MetricType.GAUGE,
                     tags: Dict[str, str] = None) -> None:
        """
        Record a metric value.

        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            tags: Optional tags for the metric
        """
        if tags is None:
            tags = {}

        metric = MetricData(
            name=name,
            value=value,
            metric_type=metric_type,
            tags=tags,
            timestamp=datetime.now()
        )

        if name not in self.metrics:
            self.metrics[name] = []

        self.metrics[name].append(metric)

        # Check for alerts
        asyncio.create_task(self._check_metric_alerts(name, value))

        logger.debug(f"Recorded metric: {name} = {value}")

    def increment_counter(self, name: str, value: float = 1, tags: Dict[str, str] = None) -> None:
        """
        Increment a counter metric.

        Args:
            name: Counter name
            value: Increment value
            tags: Optional tags
        """
        self.record_metric(name, value, MetricType.COUNTER, tags)

    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """
        Set a gauge metric value.

        Args:
            name: Gauge name
            value: Gauge value
            tags: Optional tags
        """
        self.record_metric(name, value, MetricType.GAUGE, tags)

    def record_timer(self, name: str, duration_ms: float, tags: Dict[str, str] = None) -> None:
        """
        Record a timer metric.

        Args:
            name: Timer name
            duration_ms: Duration in milliseconds
            tags: Optional tags
        """
        self.record_metric(name, duration_ms, MetricType.TIMER, tags)

    def add_alert_rule(self, rule: AlertRule) -> None:
        """
        Add an alert rule.

        Args:
            rule: Alert rule configuration
        """
        self.alert_rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")

    def remove_alert_rule(self, rule_name: str) -> bool:
        """
        Remove an alert rule.

        Args:
            rule_name: Name of rule to remove

        Returns:
            True if rule was removed
        """
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            logger.info(f"Removed alert rule: {rule_name}")
            return True
        return False

    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """
        Add an alert handler function.

        Args:
            handler: Function to handle alerts
        """
        self.alert_handlers.append(handler)
        logger.info("Added alert handler")

    def get_metrics(self, name: str, start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None) -> List[MetricData]:
        """
        Get metrics for a given name and time range.

        Args:
            name: Metric name
            start_time: Start time filter
            end_time: End time filter

        Returns:
            List of metric data points
        """
        if name not in self.metrics:
            return []

        metrics = self.metrics[name]

        if start_time:
            metrics = [m for m in metrics if m.timestamp >= start_time]

        if end_time:
            metrics = [m for m in metrics if m.timestamp <= end_time]

        return sorted(metrics, key=lambda x: x.timestamp)

    def get_metric_summary(self, name: str, hours: int = 1) -> Dict[str, Any]:
        """
        Get summary statistics for a metric.

        Args:
            name: Metric name
            hours: Hours to look back

        Returns:
            Summary statistics
        """
        start_time = datetime.now() - timedelta(hours=hours)
        metrics = self.get_metrics(name, start_time=start_time)

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

    def get_active_alerts(self) -> List[Alert]:
        """
        Get all active (unresolved) alerts.

        Returns:
            List of active alerts
        """
        return [alert for alert in self.alerts.values() if not alert.resolved]

    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert.

        Args:
            alert_id: Alert ID to resolve

        Returns:
            True if alert was resolved
        """
        if alert_id in self.alerts:
            self.alerts[alert_id].resolved = True
            logger.info(f"Resolved alert: {alert_id}")
            return True
        return False

    def update_component_health(self, component: str, health_data: Dict[str, Any]) -> None:
        """
        Update health status for a component.

        Args:
            component: Component name
            health_data: Health status data
        """
        self.component_health[component] = {
            **health_data,
            "timestamp": datetime.now().isoformat()
        }

        # Record health metrics
        if "healthy" in health_data:
            self.set_gauge(f"{component}.health", 1.0 if health_data["healthy"] else 0.0)

        if "response_time" in health_data:
            self.record_timer(f"{component}.response_time", health_data["response_time"])

    def get_component_health(self, component: str = None) -> Dict[str, Any]:
        """
        Get health status for components.

        Args:
            component: Specific component name, or None for all

        Returns:
            Health status data
        """
        if component:
            return self.component_health.get(component, {})
        return self.component_health

    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get current system metrics.

        Returns:
            System metrics data
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used / (1024 * 1024),
                "memory_total_mb": memory.total / (1024 * 1024),
                "disk_percent": disk.percent,
                "disk_used_gb": disk.used / (1024 * 1024 * 1024),
                "disk_total_gb": disk.total / (1024 * 1024 * 1024)
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {}

    def export_metrics(self, format: str = "json") -> str:
        """
        Export all metrics in specified format.

        Args:
            format: Export format ("json" or "prometheus")

        Returns:
            Exported metrics string
        """
        if format == "json":
            export_data = {
                "metrics": {
                    name: [m.to_dict() for m in metrics]
                    for name, metrics in self.metrics.items()
                },
                "alerts": {
                    id: alert.to_dict() for id, alert in self.alerts.items()
                },
                "component_health": self.component_health,
                "exported_at": datetime.now().isoformat()
            }
            return json.dumps(export_data, indent=2)

        elif format == "prometheus":
            # Simple Prometheus format export
            lines = []
            for name, metrics in self.metrics.items():
                if metrics:
                    latest = metrics[-1]
                    lines.append(f"{name.replace('.', '_')} {latest.value}")
            return "\n".join(lines)

        else:
            raise ValueError(f"Unsupported export format: {format}")

    async def _metrics_collection_loop(self) -> None:
        """Background task for collecting system metrics."""
        while self._running:
            try:
                if self.system_metrics_enabled:
                    system_metrics = self.get_system_metrics()
                    for name, value in system_metrics.items():
                        self.set_gauge(f"system.{name}", value)

                await asyncio.sleep(self.collection_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(self.collection_interval)

    async def _alert_processing_loop(self) -> None:
        """Background task for processing alerts."""
        while self._running:
            try:
                await asyncio.sleep(self.alert_check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert processing: {e}")
                await asyncio.sleep(self.alert_check_interval)

    async def _cleanup_loop(self) -> None:
        """Background task for cleaning up old metrics."""
        while self._running:
            try:
                cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)

                for name, metrics in self.metrics.items():
                    self.metrics[name] = [
                        m for m in metrics if m.timestamp > cutoff_time
                    ]

                await asyncio.sleep(3600)  # Run cleanup every hour

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup: {e}")
                await asyncio.sleep(3600)

    async def _check_metric_alerts(self, metric_name: str, value: float) -> None:
        """Check if a metric triggers any alerts."""
        for rule in self.alert_rules.values():
            if rule.metric_name == metric_name and rule.enabled:
                triggered = False

                if rule.comparison == "gt" and value > rule.threshold:
                    triggered = True
                elif rule.comparison == "lt" and value < rule.threshold:
                    triggered = True
                elif rule.comparison == "eq" and value == rule.threshold:
                    triggered = True

                if triggered:
                    await self._create_alert(rule, value)

    async def _create_alert(self, rule: AlertRule, current_value: float) -> None:
        """Create an alert based on a rule."""
        alert_id = str(uuid.uuid4())

        alert = Alert(
            id=alert_id,
            name=rule.name,
            severity=rule.severity,
            message=f"{rule.name}: {rule.metric_name} = {current_value} (threshold: {rule.threshold})",
            component=rule.component,
            metric_name=rule.metric_name,
            threshold=rule.threshold,
            current_value=current_value,
            timestamp=datetime.now()
        )

        self.alerts[alert_id] = alert

        # Notify alert handlers
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")

        logger.warning(f"Alert triggered: {alert.message}")

    def _setup_default_alert_rules(self) -> None:
        """Set up default alert rules."""
        default_rules = [
            AlertRule(
                name="High CPU Usage",
                metric_name="system.cpu_percent",
                threshold=80.0,
                comparison="gt",
                severity=AlertSeverity.HIGH,
                component="system"
            ),
            AlertRule(
                name="High Memory Usage",
                metric_name="system.memory_percent",
                threshold=85.0,
                comparison="gt",
                severity=AlertSeverity.HIGH,
                component="system"
            ),
            AlertRule(
                name="Low Disk Space",
                metric_name="system.disk_percent",
                threshold=90.0,
                comparison="gt",
                severity=AlertSeverity.CRITICAL,
                component="system"
            )
        ]

        for rule in default_rules:
            self.add_alert_rule(rule)
