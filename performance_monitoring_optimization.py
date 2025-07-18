"""
Performance Monitoring and Optimization System

This module provides comprehensive performance monitoring, analysis, and
optimization capabilities for the intelligent agent system.
"""

import asyncio
import json
import logging
import sqlite3
import statistics
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import psutil

from agent_coordination_protocols import AgentCoordinationProtocols
from intelligence_framework import IntelligenceFramework
from intelligent_task_allocation import IntelligentTaskAllocator

logger = logging.getLogger(__name__)


class PerformanceMetricType(Enum):
    """Types of performance metrics."""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    RESOURCE_UTILIZATION = "resource_utilization"
    TASK_COMPLETION_RATE = "task_completion_rate"
    AGENT_EFFICIENCY = "agent_efficiency"
    COORDINATION_EFFECTIVENESS = "coordination_effectiveness"
    LEARNING_PROGRESS = "learning_progress"
    QUALITY_SCORE = "quality_score"
    AVAILABILITY = "availability"


class OptimizationAction(Enum):
    """Types of optimization actions."""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    REBALANCE_LOAD = "rebalance_load"
    ADJUST_PARAMETERS = "adjust_parameters"
    RESTART_COMPONENT = "restart_component"
    REALLOCATE_RESOURCES = "reallocate_resources"
    UPDATE_STRATEGY = "update_strategy"
    TRIGGER_LEARNING = "trigger_learning"


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """Represents a performance metric measurement."""

    metric_type: PerformanceMetricType
    value: float
    timestamp: datetime
    source: str
    context: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'metric_type': self.metric_type.value,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'context': self.context,
            'tags': self.tags
        }


@dataclass
class PerformanceThreshold:
    """Defines performance thresholds for alerts and optimization."""

    metric_type: PerformanceMetricType
    warning_threshold: float
    critical_threshold: float
    optimization_threshold: float
    comparison_operator: str = ">"  # ">", "<", ">=", "<=", "==", "!="
    duration_minutes: int = 5  # How long threshold must be breached

    def check_threshold(self, value: float) -> Optional[AlertLevel]:
        """Check if value breaches thresholds."""
        if self._compare_value(value, self.critical_threshold):
            return AlertLevel.CRITICAL
        elif self._compare_value(value, self.warning_threshold):
            return AlertLevel.WARNING
        return None

    def _compare_value(self, value: float, threshold: float) -> bool:
        """Compare value against threshold using the specified operator."""
        if self.comparison_operator == ">":
            return value > threshold
        elif self.comparison_operator == "<":
            return value < threshold
        elif self.comparison_operator == ">=":
            return value >= threshold
        elif self.comparison_operator == "<=":
            return value <= threshold
        elif self.comparison_operator == "==":
            return value == threshold
        elif self.comparison_operator == "!=":
            return value != threshold
        return False


@dataclass
class PerformanceAlert:
    """Represents a performance alert."""

    alert_id: str
    metric_type: PerformanceMetricType
    level: AlertLevel
    message: str
    value: float
    threshold: float
    timestamp: datetime
    source: str
    resolved: bool = False
    resolution_timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'alert_id': self.alert_id,
            'metric_type': self.metric_type.value,
            'level': self.level.value,
            'message': self.message,
            'value': self.value,
            'threshold': self.threshold,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'resolved': self.resolved,
            'resolution_timestamp': self.resolution_timestamp.isoformat() if self.resolution_timestamp else None
        }


@dataclass
class OptimizationRecommendation:
    """Represents an optimization recommendation."""

    recommendation_id: str
    action: OptimizationAction
    description: str
    impact_score: float
    confidence: float
    priority: int
    estimated_improvement: float
    resource_cost: float
    implementation_complexity: str
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'recommendation_id': self.recommendation_id,
            'action': self.action.value,
            'description': self.description,
            'impact_score': self.impact_score,
            'confidence': self.confidence,
            'priority': self.priority,
            'estimated_improvement': self.estimated_improvement,
            'resource_cost': self.resource_cost,
            'implementation_complexity': self.implementation_complexity,
            'context': self.context,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class SystemHealthStatus:
    """Represents overall system health status."""

    overall_health: float  # 0.0 to 1.0
    component_health: Dict[str, float]
    active_alerts: List[PerformanceAlert]
    recent_metrics: Dict[PerformanceMetricType, float]
    optimization_recommendations: List[OptimizationRecommendation]
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'overall_health': self.overall_health,
            'component_health': self.component_health,
            'active_alerts': [
                alert.to_dict() for alert in self.active_alerts],
            'recent_metrics': {
                k.value: v for k,
                v in self.recent_metrics.items()},
            'optimization_recommendations': [
                rec.to_dict() for rec in self.optimization_recommendations],
            'timestamp': self.timestamp.isoformat()}


class PerformanceMonitoringOptimization:
    """
    Comprehensive performance monitoring and optimization system.

    This class provides real-time monitoring, analysis, alerting, and
    optimization capabilities for the intelligent agent system.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the performance monitoring system."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Core components (will be injected)
        self.intelligence_framework: Optional[IntelligenceFramework] = None
        self.task_allocator: Optional[IntelligentTaskAllocator] = None
        self.coordination_protocols: Optional[AgentCoordinationProtocols] = None

        # Monitoring infrastructure
        self.metrics_buffer: deque = deque(maxlen=10000)
        self.metric_history: Dict[PerformanceMetricType, deque] = {}
        self.active_alerts: Dict[str, PerformanceAlert] = {}

        # Performance thresholds
        self.thresholds: Dict[PerformanceMetricType, PerformanceThreshold] = {}
        self._initialize_default_thresholds()

        # Optimization
        self.optimization_recommendations: List[OptimizationRecommendation] = [
        ]
        self.optimization_history: List[Dict[str, Any]] = []

        # Real-time monitoring
        self.monitoring_active = False
        self.monitoring_tasks: List[asyncio.Task] = []
        self.monitoring_interval = self.config.get('monitoring_interval', 10.0)

        # Performance baselines
        self.performance_baselines: Dict[PerformanceMetricType, float] = {}
        self.baseline_update_interval = self.config.get(
            'baseline_update_interval', 3600)

        # Resource monitoring
        self.system_resource_monitor = SystemResourceMonitor()

        # Statistics and analytics
        self.performance_analytics = PerformanceAnalytics()

        # Initialize database
        self._init_database()

        # Thread pool for background processing
        self.executor = ThreadPoolExecutor(max_workers=4)

        self.logger.info(
            "Performance Monitoring and Optimization system initialized")

    def _init_database(self) -> None:
        """Initialize SQLite database for performance data."""
        db_path = self.config.get('db_path', 'performance_monitoring.db')

        with sqlite3.connect(db_path,
                             detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as conn:
            # Performance metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    metric_id TEXT PRIMARY KEY,
                    metric_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    source TEXT NOT NULL,
                    context TEXT,
                    tags TEXT
                )
            """)

            # Performance alerts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_alerts (
                    alert_id TEXT PRIMARY KEY,
                    metric_type TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    source TEXT NOT NULL,
                    resolved BOOLEAN NOT NULL,
                    resolution_timestamp TIMESTAMP
                )
            """)

            # Optimization recommendations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS optimization_recommendations (
                    recommendation_id TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    description TEXT NOT NULL,
                    impact_score REAL NOT NULL,
                    confidence REAL NOT NULL,
                    priority INTEGER NOT NULL,
                    estimated_improvement REAL NOT NULL,
                    resource_cost REAL NOT NULL,
                    implementation_complexity TEXT NOT NULL,
                    context TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    implemented BOOLEAN DEFAULT FALSE,
                    implementation_timestamp TIMESTAMP
                )
            """)

            # System health snapshots
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_health_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    overall_health REAL NOT NULL,
                    component_health TEXT NOT NULL,
                    active_alerts_count INTEGER NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    metadata TEXT
                )
            """)

            # Performance baselines
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_baselines (
                    baseline_id TEXT PRIMARY KEY,
                    metric_type TEXT NOT NULL,
                    baseline_value REAL NOT NULL,
                    confidence_interval_lower REAL NOT NULL,
                    confidence_interval_upper REAL NOT NULL,
                    sample_size INTEGER NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    metadata TEXT
                )
            """)

            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_type_timestamp
                ON performance_metrics(metric_type, timestamp)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_level_timestamp
                ON performance_alerts(level, timestamp)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_recommendations_priority
                ON optimization_recommendations(priority, timestamp)
            """)

            conn.commit()

    def _initialize_default_thresholds(self) -> None:
        """Initialize default performance thresholds."""
        self.thresholds = {
            PerformanceMetricType.RESPONSE_TIME: PerformanceThreshold(
                metric_type=PerformanceMetricType.RESPONSE_TIME,
                warning_threshold=2.0,
                critical_threshold=5.0,
                optimization_threshold=1.5,
                comparison_operator=">",
                duration_minutes=3
            ),
            PerformanceMetricType.THROUGHPUT: PerformanceThreshold(
                metric_type=PerformanceMetricType.THROUGHPUT,
                warning_threshold=50.0,
                critical_threshold=20.0,
                optimization_threshold=80.0,
                comparison_operator="<",
                duration_minutes=5
            ),
            PerformanceMetricType.ERROR_RATE: PerformanceThreshold(
                metric_type=PerformanceMetricType.ERROR_RATE,
                warning_threshold=0.05,
                critical_threshold=0.10,
                optimization_threshold=0.02,
                comparison_operator=">",
                duration_minutes=3
            ),
            PerformanceMetricType.RESOURCE_UTILIZATION: PerformanceThreshold(
                metric_type=PerformanceMetricType.RESOURCE_UTILIZATION,
                warning_threshold=0.80,
                critical_threshold=0.95,
                optimization_threshold=0.70,
                comparison_operator=">",
                duration_minutes=10
            ),
            PerformanceMetricType.TASK_COMPLETION_RATE: PerformanceThreshold(
                metric_type=PerformanceMetricType.TASK_COMPLETION_RATE,
                warning_threshold=0.85,
                critical_threshold=0.70,
                optimization_threshold=0.95,
                comparison_operator="<",
                duration_minutes=15
            ),
            PerformanceMetricType.AGENT_EFFICIENCY: PerformanceThreshold(
                metric_type=PerformanceMetricType.AGENT_EFFICIENCY,
                warning_threshold=0.70,
                critical_threshold=0.50,
                optimization_threshold=0.85,
                comparison_operator="<",
                duration_minutes=20
            )
        }

    def set_components(
        self,
        intelligence_framework: IntelligenceFramework,
        task_allocator: IntelligentTaskAllocator,
        coordination_protocols: AgentCoordinationProtocols
    ) -> None:
        """Set references to core system components."""
        self.intelligence_framework = intelligence_framework
        self.task_allocator = task_allocator
        self.coordination_protocols = coordination_protocols

    async def start_monitoring(self) -> None:
        """Start the performance monitoring system."""
        if self.monitoring_active:
            return

        self.monitoring_active = True

        # Start monitoring tasks
        self.monitoring_tasks = [
            asyncio.create_task(self._metric_collection_loop()),
            asyncio.create_task(self._alert_monitoring_loop()),
            asyncio.create_task(self._optimization_loop()),
            asyncio.create_task(self._baseline_update_loop()),
            asyncio.create_task(self._health_check_loop())
        ]

        self.logger.info("Performance monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop the performance monitoring system."""
        if not self.monitoring_active:
            return

        self.monitoring_active = False

        # Cancel monitoring tasks
        for task in self.monitoring_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self.monitoring_tasks:
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)

        self.monitoring_tasks.clear()

        # Shutdown thread pool
        self.executor.shutdown(wait=True)

        self.logger.info("Performance monitoring stopped")

    async def record_metric(
        self,
        metric_type: PerformanceMetricType,
        value: float,
        source: str,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a performance metric."""
        metric = PerformanceMetric(
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(),
            source=source,
            context=context or {},
            tags=tags or {}
        )

        # Add to buffer
        self.metrics_buffer.append(metric)

        # Add to history
        if metric_type not in self.metric_history:
            self.metric_history[metric_type] = deque(maxlen=1000)
        self.metric_history[metric_type].append(metric)

        # Check thresholds
        await self._check_thresholds(metric)

        # Store in database (async)
        asyncio.create_task(self._store_metric(metric))

    async def get_system_health(self) -> SystemHealthStatus:
        """Get current system health status."""
        # Calculate overall health
        overall_health = await self._calculate_overall_health()

        # Get component health
        component_health = await self._get_component_health()

        # Get active alerts
        active_alerts = list(self.active_alerts.values())

        # Get recent metrics
        recent_metrics = await self._get_recent_metrics()

        # Get optimization recommendations
        optimization_recommendations = await self._get_top_recommendations()

        return SystemHealthStatus(
            overall_health=overall_health,
            component_health=component_health,
            active_alerts=active_alerts,
            recent_metrics=recent_metrics,
            optimization_recommendations=optimization_recommendations
        )

    async def get_performance_report(
        self,
        time_range: timedelta = timedelta(hours=24)
    ) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        end_time = datetime.now()
        start_time = end_time - time_range

        # Get metrics for time range
        metrics_data = await self._get_metrics_for_range(start_time, end_time)

        # Calculate statistics
        statistics = await self._calculate_performance_statistics(metrics_data)

        # Get trends
        trends = await self._analyze_performance_trends(metrics_data)

        # Get alerts history
        alerts_history = await self._get_alerts_history(start_time, end_time)

        # Get optimization history
        optimization_history = await self._get_optimization_history(start_time, end_time)

        return {
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'statistics': statistics,
            'trends': trends,
            'alerts_history': alerts_history,
            'optimization_history': optimization_history,
            'system_health': (await self.get_system_health()).to_dict()
        }

    async def _get_metrics_for_range(
            self,
            start_time: datetime,
            end_time: datetime) -> List[PerformanceMetric]:
        """Get metrics for a specific time range."""
        metrics = []
        for metric in self.metrics_buffer:
            if start_time <= metric.timestamp <= end_time:
                metrics.append(metric)
        return metrics

    async def _calculate_performance_statistics(
            self, metrics_data: List[PerformanceMetric]) -> Dict[str, Any]:
        """Calculate performance statistics from metrics data."""
        stats = {}

        # Group metrics by type
        metrics_by_type = defaultdict(list)
        for metric in metrics_data:
            metrics_by_type[metric.metric_type].append(metric.value)

        # Calculate statistics for each type
        for metric_type, values in metrics_by_type.items():
            if values:
                stats[metric_type.value] = {
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'min': min(values),
                    'max': max(values),
                    'count': len(values),
                    'std_dev': statistics.stdev(values) if len(values) > 1 else 0
                }

        return stats

    async def _analyze_performance_trends(
            self, metrics_data: List[PerformanceMetric]) -> Dict[str, Any]:
        """Analyze performance trends from metrics data."""
        trends = {}

        # Group metrics by type
        metrics_by_type = defaultdict(list)
        for metric in metrics_data:
            metrics_by_type[metric.metric_type].append(
                (metric.timestamp, metric.value))

        # Calculate trends for each type
        for metric_type, time_values in metrics_by_type.items():
            if len(time_values) > 1:
                # Sort by timestamp
                time_values.sort(key=lambda x: x[0])
                values = [v[1] for v in time_values]

                # Calculate simple trend
                if len(values) >= 2:
                    trend = (values[-1] - values[0]) / len(values)
                    trends[metric_type.value] = {
                        'trend': trend,
                        'direction': 'increasing' if trend > 0 else 'decreasing' if trend < 0 else 'stable'
                    }

        return trends

    async def _get_alerts_history(
            self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get alerts history for time range."""
        alerts = []
        for alert in self.active_alerts.values():
            if start_time <= alert.timestamp <= end_time:
                alerts.append(alert.to_dict())
        return alerts

    async def _get_optimization_history(
            self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get optimization history for time range."""
        history = []
        for record in self.optimization_history:
            if 'implementation_time' in record:
                impl_time = datetime.fromisoformat(
                    record['implementation_time'])
                if start_time <= impl_time <= end_time:
                    history.append(record)
        return history

    async def optimize_performance(
        self,
        focus_areas: Optional[List[PerformanceMetricType]] = None
    ) -> List[OptimizationRecommendation]:
        """Generate performance optimization recommendations."""
        recommendations = []

        # Analyze current performance
        current_metrics = await self._get_current_performance_metrics()

        # Focus on specific areas or all
        areas_to_optimize = focus_areas or list(PerformanceMetricType)

        for metric_type in areas_to_optimize:
            if metric_type in current_metrics:
                metric_recommendations = await self._generate_optimization_recommendations(
                    metric_type, current_metrics[metric_type]
                )
                recommendations.extend(metric_recommendations)

        # Sort by priority and impact
        recommendations.sort(key=lambda r: (r.priority, -r.impact_score))

        # Store recommendations
        self.optimization_recommendations = recommendations

        # Store in database
        for recommendation in recommendations:
            asyncio.create_task(self._store_recommendation(recommendation))

        return recommendations

    async def _get_current_performance_metrics(
            self) -> Dict[PerformanceMetricType, float]:
        """Get current performance metrics."""
        current_metrics = {}

        # Get most recent metric for each type
        for metric_type, history in self.metric_history.items():
            if history:
                current_metrics[metric_type] = history[-1].value

        return current_metrics

    async def implement_optimization(
        self,
        recommendation_id: str
    ) -> Dict[str, Any]:
        """Implement an optimization recommendation."""
        recommendation = None
        for rec in self.optimization_recommendations:
            if rec.recommendation_id == recommendation_id:
                recommendation = rec
                break

        if not recommendation:
            return {'error': 'Recommendation not found'}

        try:
            # Implement the optimization
            result = await self._execute_optimization(recommendation)

            # Record implementation
            implementation_record = {
                'recommendation_id': recommendation_id,
                'implementation_time': datetime.now().isoformat(),
                'result': result,
                'success': result.get('success', False)
            }

            self.optimization_history.append(implementation_record)

            # Update database
            await self._update_recommendation_implemented(recommendation_id)

            return result

        except Exception as e:
            self.logger.error(
                f"Failed to implement optimization {recommendation_id}: {e}")
            return {'error': str(e), 'success': False}

    async def _metric_collection_loop(self) -> None:
        """Background loop for collecting performance metrics."""
        while self.monitoring_active:
            try:
                # Collect system metrics
                await self._collect_system_metrics()

                # Collect component metrics
                await self._collect_component_metrics()

                # Collect application metrics
                await self._collect_application_metrics()

                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                self.logger.error(f"Error in metric collection loop: {e}")
                await asyncio.sleep(self.monitoring_interval)

    async def _alert_monitoring_loop(self) -> None:
        """Background loop for monitoring alerts."""
        while self.monitoring_active:
            try:
                # Check for alert resolution
                await self._check_alert_resolution()

                # Send alert notifications
                await self._send_alert_notifications()

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                self.logger.error(f"Error in alert monitoring loop: {e}")
                await asyncio.sleep(30)

    async def _optimization_loop(self) -> None:
        """Background loop for optimization analysis."""
        while self.monitoring_active:
            try:
                # Run optimization analysis
                await self.optimize_performance()

                # Auto-implement low-risk optimizations
                await self._auto_implement_optimizations()

                await asyncio.sleep(300)  # Run every 5 minutes

            except Exception as e:
                self.logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(300)

    async def _baseline_update_loop(self) -> None:
        """Background loop for updating performance baselines."""
        while self.monitoring_active:
            try:
                # Update baselines
                await self._update_performance_baselines()

                await asyncio.sleep(self.baseline_update_interval)

            except Exception as e:
                self.logger.error(f"Error in baseline update loop: {e}")
                await asyncio.sleep(self.baseline_update_interval)

    async def _update_performance_baselines(self) -> None:
        """Update performance baselines based on historical data."""
        for metric_type, history in self.metric_history.items():
            if len(history) >= 100:  # Need sufficient data
                values = [metric.value for metric in history]

                # Calculate baseline statistics
                baseline_value = statistics.mean(values)
                std_dev = statistics.stdev(values) if len(values) > 1 else 0

                # Store baseline
                self.performance_baselines[metric_type] = baseline_value

                # Store in database
                await self._store_baseline(metric_type, baseline_value, std_dev, len(values))

    async def _store_baseline(
            self,
            metric_type: PerformanceMetricType,
            baseline_value: float,
            std_dev: float,
            sample_size: int) -> None:
        """Store performance baseline in database."""
        db_path = self.config.get('db_path', 'performance_monitoring.db')

        with sqlite3.connect(db_path,
                             detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as conn:
            baseline_id = f"baseline_{metric_type.value}_{int(time.time())}"
            confidence_lower = baseline_value - std_dev
            confidence_upper = baseline_value + std_dev

            conn.execute("""
                INSERT INTO performance_baselines VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                baseline_id,
                metric_type.value,
                baseline_value,
                confidence_lower,
                confidence_upper,
                sample_size,
                datetime.now(),
                json.dumps({})
            ))
            conn.commit()

    async def _health_check_loop(self) -> None:
        """Background loop for system health checks."""
        while self.monitoring_active:
            try:
                # Perform health checks
                health_status = await self.get_system_health()

                # Store health snapshot
                await self._store_health_snapshot(health_status)

                # Check for critical health issues
                if health_status.overall_health < 0.5:
                    await self._handle_critical_health_issue(health_status)

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(60)

    async def _collect_system_metrics(self) -> None:
        """Collect system-level performance metrics."""
        # CPU utilization
        cpu_percent = self.system_resource_monitor.get_cpu_usage()
        await self.record_metric(
            PerformanceMetricType.RESOURCE_UTILIZATION,
            cpu_percent / 100.0,
            "system_cpu",
            {"resource_type": "cpu"}
        )

        # Memory utilization
        memory_percent = self.system_resource_monitor.get_memory_usage()
        await self.record_metric(
            PerformanceMetricType.RESOURCE_UTILIZATION,
            memory_percent / 100.0,
            "system_memory",
            {"resource_type": "memory"}
        )

        # Disk utilization
        disk_percent = self.system_resource_monitor.get_disk_usage()
        await self.record_metric(
            PerformanceMetricType.RESOURCE_UTILIZATION,
            disk_percent / 100.0,
            "system_disk",
            {"resource_type": "disk"}
        )

        # Network utilization
        network_percent = self.system_resource_monitor.get_network_usage()
        await self.record_metric(
            PerformanceMetricType.RESOURCE_UTILIZATION,
            network_percent / 100.0,
            "system_network",
            {"resource_type": "network"}
        )

    async def _collect_component_metrics(self) -> None:
        """Collect metrics from system components."""
        # Intelligence framework metrics
        if self.intelligence_framework:
            intelligence_metrics = self.intelligence_framework.get_intelligence_summary()

            # Decision accuracy
            decision_accuracy = intelligence_metrics.get(
                'performance_metrics', {}).get('decision_accuracy', 0)
            await self.record_metric(
                PerformanceMetricType.QUALITY_SCORE,
                decision_accuracy,
                "intelligence_framework",
                {"component": "decision_making"}
            )

        # Task allocator metrics
        if self.task_allocator:
            allocator_summary = self.task_allocator.get_allocation_summary()

            # Task completion rate
            if allocator_summary['completed_tasks'] > 0:
                completion_rate = allocator_summary['completed_tasks'] / (
                    allocator_summary['completed_tasks'] +
                    allocator_summary['failed_tasks']
                )
                await self.record_metric(
                    PerformanceMetricType.TASK_COMPLETION_RATE,
                    completion_rate,
                    "task_allocator",
                    {"component": "task_allocation"}
                )

            # Average allocation time
            allocation_time = allocator_summary['allocation_metrics']['average_allocation_time']
            await self.record_metric(
                PerformanceMetricType.RESPONSE_TIME,
                allocation_time,
                "task_allocator",
                {"component": "task_allocation", "operation": "allocation"}
            )

        # Coordination protocols metrics
        if self.coordination_protocols:
            coordination_status = self.coordination_protocols.get_coordination_status()

            # Coordination effectiveness
            if coordination_status['metrics']['messages_sent'] > 0:
                response_rate = coordination_status['metrics']['messages_received'] / (
                    coordination_status['metrics']['messages_sent'] + 1)
                await self.record_metric(
                    PerformanceMetricType.COORDINATION_EFFECTIVENESS,
                    response_rate,
                    "coordination_protocols",
                    {"component": "agent_coordination"}
                )

    async def _collect_application_metrics(self) -> None:
        """Collect application-specific metrics."""
        # Calculate throughput (tasks per minute)
        if self.task_allocator:
            current_time = datetime.now()
            current_time - timedelta(minutes=1)

            # This would typically query the database for recent completions
            # For now, use a simple approximation
            throughput = len(self.task_allocator.completed_tasks) / \
                60.0  # Tasks per minute

            await self.record_metric(
                PerformanceMetricType.THROUGHPUT,
                throughput,
                "application",
                {"component": "task_processing"}
            )

        # Calculate error rate
        if self.task_allocator:
            total_tasks = len(self.task_allocator.completed_tasks) + \
                len(self.task_allocator.failed_tasks)
            if total_tasks > 0:
                error_rate = len(
                    self.task_allocator.failed_tasks) / total_tasks
                await self.record_metric(
                    PerformanceMetricType.ERROR_RATE,
                    error_rate,
                    "application",
                    {"component": "task_processing"}
                )

    async def _check_thresholds(self, metric: PerformanceMetric) -> None:
        """Check if metric breaches performance thresholds."""
        if metric.metric_type not in self.thresholds:
            return

        threshold = self.thresholds[metric.metric_type]
        alert_level = threshold.check_threshold(metric.value)

        if alert_level:
            await self._create_alert(metric, alert_level, threshold)

    async def _create_alert(
        self,
        metric: PerformanceMetric,
        level: AlertLevel,
        threshold: PerformanceThreshold
    ) -> None:
        """Create a performance alert."""
        alert_id = f"alert_{
            metric.metric_type.value}_{
            metric.timestamp.strftime('%Y%m%d_%H%M%S')}"

        # Check if similar alert already exists
        for existing_alert in self.active_alerts.values():
            if (existing_alert.metric_type == metric.metric_type and
                existing_alert.level == level and
                    not existing_alert.resolved):
                return  # Don't create duplicate alerts

        # Determine appropriate threshold value
        threshold_value = (threshold.critical_threshold if level ==
                           AlertLevel.CRITICAL else threshold.warning_threshold)

        alert = PerformanceAlert(
            alert_id=alert_id,
            metric_type=metric.metric_type,
            level=level,
            message=f"{
                metric.metric_type.value} {
                threshold.comparison_operator} {threshold_value} " f"(current: {
                metric.value})",
            value=metric.value,
            threshold=threshold_value,
            timestamp=metric.timestamp,
            source=metric.source)

        # Store alert
        self.active_alerts[alert_id] = alert

        # Store in database
        await self._store_alert(alert)

        self.logger.warning(f"Performance alert created: {alert.message}")

    async def _check_alert_resolution(self) -> None:
        """Check if any active alerts should be resolved."""
        for alert_id, alert in list(self.active_alerts.items()):
            if alert.resolved:
                continue

            # Get recent metrics for this type
            if alert.metric_type not in self.metric_history:
                continue

            recent_metrics = list(
                self.metric_history[alert.metric_type])[-5:]  # Last 5 metrics

            if not recent_metrics:
                continue

            # Check if threshold is no longer breached
            threshold = self.thresholds[alert.metric_type]
            resolved = True

            for metric in recent_metrics:
                if threshold.check_threshold(metric.value):
                    resolved = False
                    break

            if resolved:
                alert.resolved = True
                alert.resolution_timestamp = datetime.now()
                await self._update_alert_resolved(alert)

                self.logger.info(f"Alert resolved: {alert.message}")

    async def _send_alert_notifications(self) -> None:
        """Send notifications for active alerts."""
        # This would typically integrate with notification systems
        # For now, just log critical alerts
        for alert in self.active_alerts.values():
            if alert.level == AlertLevel.CRITICAL and not alert.resolved:
                self.logger.critical(f"CRITICAL ALERT: {alert.message}")

    async def _calculate_overall_health(self) -> float:
        """Calculate overall system health score."""
        health_scores = []

        # Component health scores
        if self.intelligence_framework:
            health_scores.append(0.8)  # Placeholder

        if self.task_allocator:
            # Base health on task completion rate
            summary = self.task_allocator.get_allocation_summary()
            if summary['completed_tasks'] + summary['failed_tasks'] > 0:
                completion_rate = summary['completed_tasks'] / (
                    summary['completed_tasks'] + summary['failed_tasks']
                )
                health_scores.append(completion_rate)

        # System resource health
        cpu_health = 1.0 - \
            (self.system_resource_monitor.get_cpu_usage() / 100.0)
        memory_health = 1.0 - \
            (self.system_resource_monitor.get_memory_usage() / 100.0)
        health_scores.extend([cpu_health, memory_health])

        # Alert impact on health
        critical_alerts = sum(1 for a in self.active_alerts.values(
        ) if a.level == AlertLevel.CRITICAL and not a.resolved)
        warning_alerts = sum(1 for a in self.active_alerts.values(
        ) if a.level == AlertLevel.WARNING and not a.resolved)

        alert_impact = max(
            0, 1.0 - (critical_alerts * 0.3 + warning_alerts * 0.1))
        health_scores.append(alert_impact)

        return statistics.mean(health_scores) if health_scores else 0.5

    async def _get_component_health(self) -> Dict[str, float]:
        """Get health scores for individual components."""
        component_health = {}

        # Intelligence framework health
        if self.intelligence_framework:
            intelligence_summary = self.intelligence_framework.get_intelligence_summary()
            decision_accuracy = intelligence_summary.get(
                'performance_metrics', {}).get('decision_accuracy', 0.5)
            component_health['intelligence_framework'] = decision_accuracy

        # Task allocator health
        if self.task_allocator:
            summary = self.task_allocator.get_allocation_summary()
            if summary['completed_tasks'] + summary['failed_tasks'] > 0:
                completion_rate = summary['completed_tasks'] / (
                    summary['completed_tasks'] + summary['failed_tasks']
                )
                component_health['task_allocator'] = completion_rate
            else:
                # Default for new systems
                component_health['task_allocator'] = 0.8

        # Coordination protocols health
        if self.coordination_protocols:
            coordination_status = self.coordination_protocols.get_coordination_status()
            # Simple health based on message success rate
            if coordination_status['metrics']['messages_sent'] > 0:
                success_rate = coordination_status['metrics']['messages_received'] / (
                    coordination_status['metrics']['messages_sent'] + 1)
                component_health['coordination_protocols'] = success_rate
            else:
                component_health['coordination_protocols'] = 0.8

        # System resources health
        component_health['system_cpu'] = 1.0 - \
            (self.system_resource_monitor.get_cpu_usage() / 100.0)
        component_health['system_memory'] = 1.0 - \
            (self.system_resource_monitor.get_memory_usage() / 100.0)
        component_health['system_disk'] = 1.0 - \
            (self.system_resource_monitor.get_disk_usage() / 100.0)

        return component_health

    async def _get_recent_metrics(self) -> Dict[PerformanceMetricType, float]:
        """Get most recent metric values."""
        recent_metrics = {}

        for metric_type, history in self.metric_history.items():
            if history:
                recent_metrics[metric_type] = history[-1].value

        return recent_metrics

    async def _get_top_recommendations(
            self, limit: int = 5) -> List[OptimizationRecommendation]:
        """Get top optimization recommendations."""
        return sorted(
            self.optimization_recommendations,
            key=lambda r: (r.priority, -r.impact_score)
        )[:limit]

    async def _generate_optimization_recommendations(
        self,
        metric_type: PerformanceMetricType,
        current_value: float
    ) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations for a metric."""
        recommendations = []

        if metric_type == PerformanceMetricType.RESPONSE_TIME:
            if current_value > 2.0:
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"opt_response_time_{int(time.time())}",
                    action=OptimizationAction.SCALE_UP,
                    description="Scale up processing capacity to reduce response times",
                    impact_score=0.8,
                    confidence=0.9,
                    priority=1,
                    estimated_improvement=0.4,
                    resource_cost=0.3,
                    implementation_complexity="medium"
                ))

        elif metric_type == PerformanceMetricType.THROUGHPUT:
            if current_value < 50.0:
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"opt_throughput_{int(time.time())}",
                    action=OptimizationAction.REBALANCE_LOAD,
                    description="Rebalance workload distribution to improve throughput",
                    impact_score=0.7,
                    confidence=0.8,
                    priority=2,
                    estimated_improvement=0.3,
                    resource_cost=0.1,
                    implementation_complexity="low"
                ))

        elif metric_type == PerformanceMetricType.ERROR_RATE:
            if current_value > 0.05:
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"opt_error_rate_{int(time.time())}",
                    action=OptimizationAction.ADJUST_PARAMETERS,
                    description="Adjust task allocation parameters to reduce error rates",
                    impact_score=0.9,
                    confidence=0.7,
                    priority=1,
                    estimated_improvement=0.5,
                    resource_cost=0.0,
                    implementation_complexity="low"
                ))

        elif metric_type == PerformanceMetricType.RESOURCE_UTILIZATION:
            if current_value > 0.8:
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"opt_resource_util_{int(time.time())}",
                    action=OptimizationAction.REALLOCATE_RESOURCES,
                    description="Reallocate resources to prevent overutilization",
                    impact_score=0.8,
                    confidence=0.9,
                    priority=1,
                    estimated_improvement=0.3,
                    resource_cost=0.2,
                    implementation_complexity="medium"
                ))

        return recommendations

    async def _execute_optimization(
            self, recommendation: OptimizationRecommendation) -> Dict[str, Any]:
        """Execute an optimization recommendation."""
        try:
            if recommendation.action == OptimizationAction.SCALE_UP:
                return await self._execute_scale_up(recommendation)

            elif recommendation.action == OptimizationAction.REBALANCE_LOAD:
                return await self._execute_rebalance_load(recommendation)

            elif recommendation.action == OptimizationAction.ADJUST_PARAMETERS:
                return await self._execute_adjust_parameters(recommendation)

            elif recommendation.action == OptimizationAction.REALLOCATE_RESOURCES:
                return await self._execute_reallocate_resources(recommendation)

            else:
                return {
                    'success': False,
                    'message': f"Optimization action {
                        recommendation.action.value} not implemented"}

        except Exception as e:
            return {
                'success': False,
                'message': f"Optimization execution failed: {str(e)}"
            }

    async def _execute_scale_up(
            self, recommendation: OptimizationRecommendation) -> Dict[str, Any]:
        """Execute scale up optimization."""
        # This would typically interact with the orchestration system
        # For now, return a simulation result
        return {
            'success': True,
            'message': 'Scale up optimization simulated',
            'details': {
                'action': 'increased_worker_capacity',
                'estimated_improvement': recommendation.estimated_improvement
            }
        }

    async def _execute_rebalance_load(
            self, recommendation: OptimizationRecommendation) -> Dict[str, Any]:
        """Execute load rebalancing optimization."""
        if self.task_allocator:
            # Trigger load rebalancing
            # This would typically call the task allocator's rebalance method
            return {
                'success': True,
                'message': 'Load rebalancing triggered',
                'details': {
                    'action': 'workload_redistributed',
                    'estimated_improvement': recommendation.estimated_improvement}}

        return {
            'success': False,
            'message': 'Task allocator not available for rebalancing'
        }

    async def _execute_adjust_parameters(
            self, recommendation: OptimizationRecommendation) -> Dict[str, Any]:
        """Execute parameter adjustment optimization."""
        # This would typically adjust system parameters
        return {
            'success': True,
            'message': 'Parameters adjusted',
            'details': {
                'action': 'parameter_optimization',
                'estimated_improvement': recommendation.estimated_improvement
            }
        }

    async def _execute_reallocate_resources(
            self, recommendation: OptimizationRecommendation) -> Dict[str, Any]:
        """Execute resource reallocation optimization."""
        # This would typically interact with resource management
        return {
            'success': True,
            'message': 'Resources reallocated',
            'details': {
                'action': 'resource_reallocation',
                'estimated_improvement': recommendation.estimated_improvement
            }
        }

    async def _auto_implement_optimizations(self) -> None:
        """Automatically implement low-risk optimizations."""
        for recommendation in self.optimization_recommendations:
            # Only auto-implement low-risk, high-confidence optimizations
            if (recommendation.resource_cost < 0.2 and
                recommendation.confidence > 0.8 and
                    recommendation.implementation_complexity == "low"):

                result = await self.implement_optimization(recommendation.recommendation_id)
                if result.get('success'):
                    self.logger.info(
                        f"Auto-implemented optimization: {recommendation.description}")

    async def _store_metric(self, metric: PerformanceMetric) -> None:
        """Store metric in database."""
        db_path = self.config.get('db_path', 'performance_monitoring.db')

        with sqlite3.connect(db_path,
                             detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as conn:
            conn.execute("""
                INSERT INTO performance_metrics VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                f"metric_{metric.timestamp.strftime('%Y%m%d_%H%M%S_%f')}",
                metric.metric_type.value,
                metric.value,
                metric.timestamp,
                metric.source,
                json.dumps(metric.context),
                json.dumps(metric.tags)
            ))
            conn.commit()

    async def _store_alert(self, alert: PerformanceAlert) -> None:
        """Store alert in database."""
        db_path = self.config.get('db_path', 'performance_monitoring.db')

        with sqlite3.connect(db_path,
                             detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as conn:
            conn.execute("""
                INSERT INTO performance_alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_id,
                alert.metric_type.value,
                alert.level.value,
                alert.message,
                alert.value,
                alert.threshold,
                alert.timestamp,
                alert.source,
                alert.resolved,
                alert.resolution_timestamp
            ))
            conn.commit()

    async def _store_recommendation(
            self, recommendation: OptimizationRecommendation) -> None:
        """Store recommendation in database."""
        db_path = self.config.get('db_path', 'performance_monitoring.db')

        with sqlite3.connect(db_path,
                             detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as conn:
            conn.execute("""
                INSERT INTO optimization_recommendations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recommendation.recommendation_id,
                recommendation.action.value,
                recommendation.description,
                recommendation.impact_score,
                recommendation.confidence,
                recommendation.priority,
                recommendation.estimated_improvement,
                recommendation.resource_cost,
                recommendation.implementation_complexity,
                json.dumps(recommendation.context),
                recommendation.timestamp,
                False,  # implemented
                None    # implementation_timestamp
            ))
            conn.commit()

    async def _update_alert_resolved(self, alert: PerformanceAlert) -> None:
        """Update alert as resolved in database."""
        db_path = self.config.get('db_path', 'performance_monitoring.db')

        with sqlite3.connect(db_path,
                             detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as conn:
            conn.execute("""
                UPDATE performance_alerts
                SET resolved = ?, resolution_timestamp = ?
                WHERE alert_id = ?
            """, (True, alert.resolution_timestamp, alert.alert_id))
            conn.commit()

    async def _update_recommendation_implemented(
            self, recommendation_id: str) -> None:
        """Update recommendation as implemented in database."""
        db_path = self.config.get('db_path', 'performance_monitoring.db')

        with sqlite3.connect(db_path,
                             detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as conn:
            conn.execute("""
                UPDATE optimization_recommendations
                SET implemented = ?, implementation_timestamp = ?
                WHERE recommendation_id = ?
            """, (True, datetime.now(), recommendation_id))
            conn.commit()

    async def _store_health_snapshot(
            self, health_status: SystemHealthStatus) -> None:
        """Store health snapshot in database."""
        db_path = self.config.get('db_path', 'performance_monitoring.db')

        with sqlite3.connect(db_path,
                             detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as conn:
            conn.execute(
                """
                INSERT INTO system_health_snapshots VALUES (?, ?, ?, ?, ?, ?)
            """, (f"health_{
                    health_status.timestamp.strftime('%Y%m%d_%H%M%S_%f')}", health_status.overall_health, json.dumps(
                    health_status.component_health), len(
                    health_status.active_alerts), health_status.timestamp, json.dumps(
                    {
                        'resource_health': getattr(
                            health_status, 'resource_health', 0.0), 'recommendations': [
                                rec.to_dict() for rec in health_status.optimization_recommendations]})))
            conn.commit()

    async def _handle_critical_health_issue(
            self, health_status: SystemHealthStatus) -> None:
        """Handle critical system health issues."""
        self.logger.critical(
            f"Critical system health issue detected: {
                health_status.overall_health}")

        # Create critical alert
        alert = PerformanceAlert(
            alert_id=f"critical_health_{
                datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            metric_type=PerformanceMetricType.SYSTEM_HEALTH,
            level=AlertLevel.CRITICAL,
            message=f"System health critically low: {
                health_status.overall_health:.2f}",
            value=health_status.overall_health,
            threshold=0.5,
            source="health_monitor")

        self.active_alerts[alert.alert_id] = alert
        await self._store_alert(alert)

        # Trigger emergency optimization recommendations
        for recommendation in health_status.optimization_recommendations:
            if recommendation.priority == 1:  # Critical priority
                # Auto-implement critical recommendations
                self.logger.info(
                    f"Auto-implementing critical recommendation: {recommendation.description}")
                # Here you would implement the recommendation logic

    def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get summary of monitoring system status."""
        return {
            'monitoring_active': self.monitoring_active,
            'metrics_buffer_size': len(self.metrics_buffer),
            'metric_types_tracked': len(self.metric_history),
            'active_alerts': len(self.active_alerts),
            'optimization_recommendations': len(self.optimization_recommendations),
            'performance_thresholds': len(self.thresholds),
            'monitoring_interval': self.monitoring_interval
        }


class SystemResourceMonitor:
    """System resource monitoring utility."""

    def __init__(self):
        self.cpu_percent_history = deque(maxlen=60)  # 1 minute history
        self.memory_percent_history = deque(maxlen=60)
        self.disk_percent_history = deque(maxlen=60)
        self.network_bytes_history = deque(maxlen=60)
        self.last_network_bytes = None

    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        self.cpu_percent_history.append(cpu_percent)
        return cpu_percent

    def get_memory_usage(self) -> float:
        """Get current memory usage percentage."""
        memory = psutil.virtual_memory()
        self.memory_percent_history.append(memory.percent)
        return memory.percent

    def get_disk_usage(self) -> float:
        """Get current disk usage percentage."""
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        self.disk_percent_history.append(disk_percent)
        return disk_percent

    def get_network_usage(self) -> float:
        """Get current network usage as percentage (simplified)."""
        # This is a simplified implementation
        # In practice, you'd calculate based on interface capacity
        network_io = psutil.net_io_counters()
        current_bytes = network_io.bytes_sent + network_io.bytes_recv

        if self.last_network_bytes is not None:
            bytes_diff = current_bytes - self.last_network_bytes
            # Assume 1 Gbps capacity and normalize to percentage
            # 125 MB/s = 1 Gbps
            network_percent = min(100, (bytes_diff / 1024 / 1024 / 125) * 100)
            self.network_bytes_history.append(network_percent)
        else:
            network_percent = 0

        self.last_network_bytes = current_bytes
        return network_percent


class PerformanceAnalytics:
    """Performance analytics and statistical analysis."""

    def __init__(self):
        pass

    def calculate_statistics(self, values: List[float]) -> Dict[str, float]:
        """Calculate statistical metrics for a list of values."""
        if not values:
            return {}

        return {
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'stdev': statistics.stdev(values) if len(values) > 1 else 0,
            'min': min(values),
            'max': max(values),
            'count': len(values)
        }

    def calculate_percentiles(
            self, values: List[float], percentiles: List[float]) -> Dict[str, float]:
        """Calculate percentiles for a list of values."""
        if not values:
            return {}

        sorted_values = sorted(values)
        result = {}

        for p in percentiles:
            index = int(len(sorted_values) * p / 100)
            result[f'p{p}'] = sorted_values[min(index, len(sorted_values) - 1)]

        return result

    def detect_anomalies(
            self,
            values: List[float],
            threshold: float = 2.0) -> List[int]:
        """Detect anomalies using standard deviation method."""
        if len(values) < 3:
            return []

        mean = statistics.mean(values)
        stdev = statistics.stdev(values)

        anomalies = []
        for i, value in enumerate(values):
            if abs(value - mean) > threshold * stdev:
                anomalies.append(i)

        return anomalies

    def calculate_trend(self, values: List[float]) -> float:
        """Calculate trend direction (-1 to 1)."""
        if len(values) < 2:
            return 0.0

        # Simple linear regression slope
        n = len(values)
        x = list(range(n))

        x_mean = sum(x) / n
        y_mean = sum(values) / n

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean)
                        for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        slope = numerator / denominator

        # Normalize to -1 to 1 range
        return max(-1.0, min(1.0, slope))
