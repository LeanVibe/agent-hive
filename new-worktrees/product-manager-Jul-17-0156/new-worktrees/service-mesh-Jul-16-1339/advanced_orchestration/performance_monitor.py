"""
Advanced Performance Monitoring for Multi-Agent Coordination.

This module provides comprehensive performance monitoring, analytics, and optimization
for the enhanced multi-agent coordination system.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
import threading
from collections import defaultdict, deque

from .models import AgentSpecialization, WorkflowType, CoordinationMetrics


class PerformanceMetricType(Enum):
    """Types of performance metrics to track."""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    RESOURCE_UTILIZATION = "resource_utilization"
    ERROR_RATE = "error_rate"
    COORDINATION_EFFICIENCY = "coordination_efficiency"
    AGENT_PRODUCTIVITY = "agent_productivity"
    WORKFLOW_COMPLETION_TIME = "workflow_completion_time"
    DEPENDENCY_RESOLUTION_TIME = "dependency_resolution_time"
    QUALITY_GATE_PASS_RATE = "quality_gate_pass_rate"
    PARALLEL_EFFICIENCY = "parallel_efficiency"


@dataclass
class PerformanceMetric:
    """Individual performance metric data point."""
    metric_type: PerformanceMetricType
    value: float
    timestamp: datetime
    agent_id: Optional[str] = None
    workflow_id: Optional[str] = None
    task_id: Optional[str] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration."""
    metric_type: PerformanceMetricType
    warning_threshold: float
    critical_threshold: float
    optimization_threshold: float
    measurement_unit: str
    improvement_target: float = 0.0


@dataclass
class PerformanceAlert:
    """Performance alert notification."""
    alert_id: str
    metric_type: PerformanceMetricType
    severity: str  # "warning", "critical", "optimization"
    current_value: float
    threshold_value: float
    agent_id: Optional[str] = None
    workflow_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    recommendation: str = ""
    auto_fix_available: bool = False


@dataclass
class PerformanceReport:
    """Comprehensive performance analysis report."""
    report_id: str
    generated_at: datetime
    time_period: Tuple[datetime, datetime]
    metrics_summary: Dict[PerformanceMetricType, Dict[str, float]]
    agent_performance: Dict[str, Dict[str, float]]
    workflow_analysis: Dict[str, Dict[str, float]]
    recommendations: List[str]
    performance_trends: Dict[str, List[float]]
    optimization_opportunities: List[str]
    alerts_summary: List[PerformanceAlert]


class PerformanceMonitor:
    """Advanced performance monitoring and optimization system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics_store: deque = deque(maxlen=10000)  # Ring buffer for metrics
        self.alerts: List[PerformanceAlert] = []
        self.performance_history: Dict[str, List[float]] = defaultdict(list)
        self.agent_metrics: Dict[str, Dict[PerformanceMetricType, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.workflow_metrics: Dict[str, Dict[PerformanceMetricType, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        # Performance thresholds
        self.thresholds = {
            PerformanceMetricType.LATENCY: PerformanceThreshold(
                PerformanceMetricType.LATENCY,
                warning_threshold=2.0,
                critical_threshold=5.0,
                optimization_threshold=1.0,
                measurement_unit="seconds",
                improvement_target=0.5
            ),
            PerformanceMetricType.THROUGHPUT: PerformanceThreshold(
                PerformanceMetricType.THROUGHPUT,
                warning_threshold=5.0,
                critical_threshold=2.0,
                optimization_threshold=10.0,
                measurement_unit="tasks/minute",
                improvement_target=15.0
            ),
            PerformanceMetricType.ERROR_RATE: PerformanceThreshold(
                PerformanceMetricType.ERROR_RATE,
                warning_threshold=0.05,
                critical_threshold=0.10,
                optimization_threshold=0.01,
                measurement_unit="percentage",
                improvement_target=0.005
            ),
            PerformanceMetricType.COORDINATION_EFFICIENCY: PerformanceThreshold(
                PerformanceMetricType.COORDINATION_EFFICIENCY,
                warning_threshold=0.7,
                critical_threshold=0.5,
                optimization_threshold=0.9,
                measurement_unit="percentage",
                improvement_target=0.95
            ),
            PerformanceMetricType.PARALLEL_EFFICIENCY: PerformanceThreshold(
                PerformanceMetricType.PARALLEL_EFFICIENCY,
                warning_threshold=0.6,
                critical_threshold=0.4,
                optimization_threshold=0.8,
                measurement_unit="percentage",
                improvement_target=0.85
            )
        }

        # Optimization strategies
        self.optimization_strategies = {
            PerformanceMetricType.LATENCY: self._optimize_latency,
            PerformanceMetricType.THROUGHPUT: self._optimize_throughput,
            PerformanceMetricType.COORDINATION_EFFICIENCY: self._optimize_coordination,
            PerformanceMetricType.PARALLEL_EFFICIENCY: self._optimize_parallel_execution
        }

        self.logger.info("PerformanceMonitor initialized with advanced analytics")

    def start_monitoring(self) -> None:
        """Start continuous performance monitoring."""
        if self.running:
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Performance monitoring started")

    def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        self.logger.info("Performance monitoring stopped")

    def record_metric(self, metric: PerformanceMetric) -> None:
        """Record a performance metric."""
        with self.lock:
            self.metrics_store.append(metric)

            # Update agent metrics
            if metric.agent_id:
                self.agent_metrics[metric.agent_id][metric.metric_type].append(metric.value)

            # Update workflow metrics
            if metric.workflow_id:
                self.workflow_metrics[metric.workflow_id][metric.metric_type].append(metric.value)

            # Update performance history
            history_key = f"{metric.metric_type.value}_{metric.agent_id or 'global'}"
            self.performance_history[history_key].append(metric.value)

            # Keep only last 1000 values for history
            if len(self.performance_history[history_key]) > 1000:
                self.performance_history[history_key] = self.performance_history[history_key][-1000:]

            # Check for threshold violations
            self._check_thresholds(metric)

    def _check_thresholds(self, metric: PerformanceMetric) -> None:
        """Check if metric violates performance thresholds."""
        threshold = self.thresholds.get(metric.metric_type)
        if not threshold:
            return

        alert_severity = None
        threshold_value = None

        if metric.value >= threshold.critical_threshold:
            alert_severity = "critical"
            threshold_value = threshold.critical_threshold
        elif metric.value >= threshold.warning_threshold:
            alert_severity = "warning"
            threshold_value = threshold.warning_threshold
        elif metric.value <= threshold.optimization_threshold:
            alert_severity = "optimization"
            threshold_value = threshold.optimization_threshold

        if alert_severity:
            alert = PerformanceAlert(
                alert_id=f"alert_{int(time.time())}_{metric.metric_type.value}",
                metric_type=metric.metric_type,
                severity=alert_severity,
                current_value=metric.value,
                threshold_value=threshold_value,
                agent_id=metric.agent_id,
                workflow_id=metric.workflow_id,
                recommendation=self._generate_recommendation(metric, threshold),
                auto_fix_available=metric.metric_type in self.optimization_strategies
            )

            self.alerts.append(alert)
            self.logger.warning(f"Performance alert: {alert_severity} - {metric.metric_type.value} = {metric.value}")

    def _generate_recommendation(self, metric: PerformanceMetric, threshold: PerformanceThreshold) -> str:
        """Generate performance improvement recommendation."""
        recommendations = {
            PerformanceMetricType.LATENCY: "Consider optimizing task routing or reducing coordination overhead",
            PerformanceMetricType.THROUGHPUT: "Consider increasing agent parallelism or task batching",
            PerformanceMetricType.ERROR_RATE: "Review error handling and task validation processes",
            PerformanceMetricType.COORDINATION_EFFICIENCY: "Optimize agent communication and dependency resolution",
            PerformanceMetricType.PARALLEL_EFFICIENCY: "Balance task distribution across agents"
        }

        base_recommendation = recommendations.get(metric.metric_type, "Review system configuration")

        if metric.agent_id:
            return f"Agent {metric.agent_id}: {base_recommendation}"
        elif metric.workflow_id:
            return f"Workflow {metric.workflow_id}: {base_recommendation}"
        else:
            return f"System-wide: {base_recommendation}"

    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.running:
            try:
                # Collect system metrics
                self._collect_system_metrics()

                # Analyze performance trends
                self._analyze_performance_trends()

                # Auto-optimize if configured
                self._auto_optimize()

                # Clean up old alerts
                self._cleanup_old_alerts()

                time.sleep(30)  # Monitor every 30 seconds

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Brief pause on error

    def _collect_system_metrics(self) -> None:
        """Collect system-wide performance metrics."""
        try:
            # Collect coordination efficiency metrics
            coordination_metrics = self._calculate_coordination_efficiency()
            if coordination_metrics:
                self.record_metric(PerformanceMetric(
                    metric_type=PerformanceMetricType.COORDINATION_EFFICIENCY,
                    value=coordination_metrics,
                    timestamp=datetime.now(),
                    additional_context={"source": "system_monitoring"}
                ))

            # Collect parallel efficiency metrics
            parallel_metrics = self._calculate_parallel_efficiency()
            if parallel_metrics:
                self.record_metric(PerformanceMetric(
                    metric_type=PerformanceMetricType.PARALLEL_EFFICIENCY,
                    value=parallel_metrics,
                    timestamp=datetime.now(),
                    additional_context={"source": "system_monitoring"}
                ))

        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")

    def _calculate_coordination_efficiency(self) -> Optional[float]:
        """Calculate current coordination efficiency."""
        if not self.workflow_metrics:
            return None

        # Calculate based on workflow completion times and coordination overhead
        recent_metrics = []
        for workflow_id, metrics in self.workflow_metrics.items():
            completion_times = metrics.get(PerformanceMetricType.WORKFLOW_COMPLETION_TIME, [])
            if completion_times:
                recent_metrics.extend(completion_times[-10:])  # Last 10 measurements

        if not recent_metrics:
            return None

        # Efficiency = 1 - (average_coordination_overhead / total_completion_time)
        avg_completion_time = statistics.mean(recent_metrics)
        estimated_coordination_overhead = avg_completion_time * 0.2  # 20% overhead baseline

        efficiency = max(0.0, 1.0 - (estimated_coordination_overhead / avg_completion_time))
        return min(1.0, efficiency)

    def _calculate_parallel_efficiency(self) -> Optional[float]:
        """Calculate current parallel execution efficiency."""
        if not self.agent_metrics:
            return None

        # Calculate based on agent utilization and task distribution
        agent_utilizations = []
        for agent_id, metrics in self.agent_metrics.items():
            productivity = metrics.get(PerformanceMetricType.AGENT_PRODUCTIVITY, [])
            if productivity:
                agent_utilizations.append(statistics.mean(productivity[-10:]))

        if not agent_utilizations:
            return None

        # Parallel efficiency = 1 - coefficient_of_variation(agent_utilizations)
        if len(agent_utilizations) < 2:
            return 1.0

        mean_utilization = statistics.mean(agent_utilizations)
        if mean_utilization == 0:
            return 0.0

        std_utilization = statistics.stdev(agent_utilizations)
        coefficient_of_variation = std_utilization / mean_utilization

        efficiency = max(0.0, 1.0 - coefficient_of_variation)
        return min(1.0, efficiency)

    def _analyze_performance_trends(self) -> None:
        """Analyze performance trends and predict issues."""
        for metric_type, threshold in self.thresholds.items():
            history_key = f"{metric_type.value}_global"
            history = self.performance_history.get(history_key, [])

            if len(history) >= 10:
                # Trend analysis
                recent_values = history[-10:]
                if len(recent_values) >= 5:
                    # Check for degrading performance
                    first_half = recent_values[:len(recent_values)//2]
                    second_half = recent_values[len(recent_values)//2:]

                    if statistics.mean(second_half) > statistics.mean(first_half) * 1.2:
                        self.logger.warning(f"Performance degradation detected in {metric_type.value}")

    def _auto_optimize(self) -> None:
        """Automatically optimize performance based on metrics."""
        for alert in self.alerts:
            if alert.auto_fix_available and alert.severity in ["warning", "critical"]:
                optimization_func = self.optimization_strategies.get(alert.metric_type)
                if optimization_func:
                    try:
                        optimization_func(alert)
                        self.logger.info(f"Auto-optimization applied for {alert.metric_type.value}")
                    except Exception as e:
                        self.logger.error(f"Auto-optimization failed for {alert.metric_type.value}: {e}")

    def _optimize_latency(self, alert: PerformanceAlert) -> None:
        """Optimize system latency."""
        # Implementation would depend on specific coordination system
        self.logger.info(f"Optimizing latency for {alert.agent_id or 'system'}")

    def _optimize_throughput(self, alert: PerformanceAlert) -> None:
        """Optimize system throughput."""
        # Implementation would depend on specific coordination system
        self.logger.info(f"Optimizing throughput for {alert.agent_id or 'system'}")

    def _optimize_coordination(self, alert: PerformanceAlert) -> None:
        """Optimize coordination efficiency."""
        # Implementation would depend on specific coordination system
        self.logger.info(f"Optimizing coordination for {alert.workflow_id or 'system'}")

    def _optimize_parallel_execution(self, alert: PerformanceAlert) -> None:
        """Optimize parallel execution efficiency."""
        # Implementation would depend on specific coordination system
        self.logger.info(f"Optimizing parallel execution for {alert.workflow_id or 'system'}")

    def _cleanup_old_alerts(self) -> None:
        """Clean up old alerts."""
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.alerts = [alert for alert in self.alerts if alert.timestamp > cutoff_time]

    def generate_performance_report(self, time_period: Optional[Tuple[datetime, datetime]] = None) -> PerformanceReport:
        """Generate comprehensive performance report."""
        if not time_period:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            time_period = (start_time, end_time)

        start_time, end_time = time_period

        # Filter metrics by time period
        relevant_metrics = [
            metric for metric in self.metrics_store
            if start_time <= metric.timestamp <= end_time
        ]

        # Calculate metrics summary
        metrics_summary = {}
        for metric_type in PerformanceMetricType:
            type_metrics = [m.value for m in relevant_metrics if m.metric_type == metric_type]
            if type_metrics:
                metrics_summary[metric_type] = {
                    "avg": statistics.mean(type_metrics),
                    "min": min(type_metrics),
                    "max": max(type_metrics),
                    "std": statistics.stdev(type_metrics) if len(type_metrics) > 1 else 0.0,
                    "count": len(type_metrics)
                }

        # Calculate agent performance
        agent_performance = {}
        for agent_id, metrics in self.agent_metrics.items():
            agent_performance[agent_id] = {}
            for metric_type, values in metrics.items():
                if values:
                    agent_performance[agent_id][metric_type.value] = {
                        "avg": statistics.mean(values[-100:]),  # Last 100 measurements
                        "trend": self._calculate_trend(values[-20:]) if len(values) >= 20 else 0.0
                    }

        # Generate recommendations
        recommendations = self._generate_performance_recommendations(metrics_summary)

        # Get relevant alerts
        relevant_alerts = [
            alert for alert in self.alerts
            if start_time <= alert.timestamp <= end_time
        ]

        return PerformanceReport(
            report_id=f"perf_report_{int(time.time())}",
            generated_at=datetime.now(),
            time_period=time_period,
            metrics_summary=metrics_summary,
            agent_performance=agent_performance,
            workflow_analysis={},  # Could be expanded
            recommendations=recommendations,
            performance_trends={},  # Could be expanded
            optimization_opportunities=[],  # Could be expanded
            alerts_summary=relevant_alerts
        )

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate performance trend (-1 to 1, where 1 is improving)."""
        if len(values) < 2:
            return 0.0

        # Simple linear trend calculation
        n = len(values)
        sum_x = sum(range(n))
        sum_y = sum(values)
        sum_xy = sum(i * values[i] for i in range(n))
        sum_x2 = sum(i * i for i in range(n))

        if n * sum_x2 - sum_x * sum_x == 0:
            return 0.0

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

        # Normalize slope to -1 to 1 range
        return max(-1.0, min(1.0, slope))

    def _generate_performance_recommendations(self, metrics_summary: Dict) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []

        for metric_type, stats in metrics_summary.items():
            threshold = self.thresholds.get(metric_type)
            if not threshold:
                continue

            avg_value = stats["avg"]

            if avg_value >= threshold.critical_threshold:
                recommendations.append(
                    f"CRITICAL: {metric_type.value} averaging {avg_value:.2f}, "
                    f"exceeds critical threshold of {threshold.critical_threshold}. "
                    f"Immediate action required."
                )
            elif avg_value >= threshold.warning_threshold:
                recommendations.append(
                    f"WARNING: {metric_type.value} averaging {avg_value:.2f}, "
                    f"approaching warning threshold of {threshold.warning_threshold}. "
                    f"Consider optimization."
                )
            elif avg_value <= threshold.optimization_threshold:
                recommendations.append(
                    f"OPPORTUNITY: {metric_type.value} averaging {avg_value:.2f}, "
                    f"below optimization threshold of {threshold.optimization_threshold}. "
                    f"Performance is excellent but could be leveraged for higher workloads."
                )

        return recommendations

    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time performance metrics."""
        current_time = datetime.now()
        recent_cutoff = current_time - timedelta(minutes=5)

        recent_metrics = [
            metric for metric in self.metrics_store
            if metric.timestamp >= recent_cutoff
        ]

        real_time_data = {}
        for metric_type in PerformanceMetricType:
            type_metrics = [m.value for m in recent_metrics if m.metric_type == metric_type]
            if type_metrics:
                real_time_data[metric_type.value] = {
                    "current": type_metrics[-1] if type_metrics else 0.0,
                    "avg_5min": statistics.mean(type_metrics),
                    "trend": self._calculate_trend(type_metrics[-10:]) if len(type_metrics) >= 10 else 0.0
                }

        return {
            "timestamp": current_time.isoformat(),
            "metrics": real_time_data,
            "active_alerts": len([a for a in self.alerts if a.severity in ["warning", "critical"]]),
            "total_measurements": len(self.metrics_store)
        }

    def get_agent_performance_summary(self) -> Dict[str, Any]:
        """Get agent-specific performance summary."""
        summary = {}

        for agent_id, metrics in self.agent_metrics.items():
            agent_summary = {}

            for metric_type, values in metrics.items():
                if values:
                    recent_values = values[-50:]  # Last 50 measurements
                    agent_summary[metric_type.value] = {
                        "current": recent_values[-1],
                        "average": statistics.mean(recent_values),
                        "best": min(recent_values) if metric_type in [PerformanceMetricType.LATENCY, PerformanceMetricType.ERROR_RATE] else max(recent_values),
                        "stability": 1.0 - (statistics.stdev(recent_values) / statistics.mean(recent_values)) if len(recent_values) > 1 and statistics.mean(recent_values) > 0 else 1.0
                    }

            summary[agent_id] = agent_summary

        return summary
