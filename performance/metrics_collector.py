#!/usr/bin/env python3
"""
Unified Metrics Collection and Dashboard System

Provides comprehensive metrics collection, aggregation, and visualization
for all Agent Hive components with real-time dashboard capabilities.

Features:
- Multi-component metrics aggregation
- Real-time performance dashboards
- Historical trend analysis
- Performance alerting and notifications
- Export capabilities (JSON, CSV, Prometheus)
- Integration with monitoring systems
"""

import asyncio
import time
import logging
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
import threading
import sqlite3
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from performance_monitor import (
    ComponentType, PerformanceLevel, UnifiedPerformanceMonitor,
    performance_monitor
)


logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Individual metric data point."""
    timestamp: float
    metric_name: str
    value: float
    component_type: ComponentType
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class AggregatedMetric:
    """Aggregated metric over time period."""
    metric_name: str
    component_type: ComponentType
    time_period: str
    start_time: datetime
    end_time: datetime
    count: int
    avg: float
    min: float
    max: float
    p50: float
    p95: float
    p99: float
    std_dev: float
    trend: float  # -1 to 1, where 1 is improving
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "component_type": self.component_type.value,
            "time_period": self.time_period,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "count": self.count,
            "avg": round(self.avg, 2),
            "min": round(self.min, 2),
            "max": round(self.max, 2),
            "p50": round(self.p50, 2),
            "p95": round(self.p95, 2),
            "p99": round(self.p99, 2),
            "std_dev": round(self.std_dev, 2),
            "trend": round(self.trend, 3)
        }


@dataclass
class DashboardData:
    """Real-time dashboard data."""
    timestamp: datetime
    overall_health: float
    component_health: Dict[ComponentType, float]
    active_alerts: int
    performance_trends: Dict[str, List[float]]
    top_slow_operations: List[Dict[str, Any]]
    recent_errors: List[Dict[str, Any]]
    throughput_metrics: Dict[str, float]
    latency_metrics: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall_health": round(self.overall_health, 1),
            "component_health": {
                comp.value: round(health, 1) 
                for comp, health in self.component_health.items()
            },
            "active_alerts": self.active_alerts,
            "performance_trends": {
                name: [round(v, 2) for v in values[-20:]]  # Last 20 points
                for name, values in self.performance_trends.items()
            },
            "top_slow_operations": self.top_slow_operations,
            "recent_errors": self.recent_errors,
            "throughput_metrics": {
                name: round(value, 2) 
                for name, value in self.throughput_metrics.items()
            },
            "latency_metrics": {
                name: round(value, 2) 
                for name, value in self.latency_metrics.items()
            }
        }


class UnifiedMetricsCollector:
    """Unified metrics collection and dashboard system."""
    
    def __init__(self, monitor: UnifiedPerformanceMonitor, config: Optional[Dict[str, Any]] = None):
        self.monitor = monitor
        self.config = config or self._get_default_config()
        self.logger = logging.getLogger(__name__)
        
        # Metrics storage
        self.metrics_buffer: deque = deque(maxlen=100000)  # In-memory buffer
        self.aggregated_metrics: Dict[str, List[AggregatedMetric]] = defaultdict(list)
        self.performance_trends: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Dashboard data
        self.current_dashboard: Optional[DashboardData] = None
        self.dashboard_history: deque = deque(maxlen=2880)  # 24 hours at 30s intervals
        
        # Database
        self.db_path = self.config.get("db_path", "unified_metrics.db")
        self._init_database()
        
        # Background tasks
        self._collection_task: Optional[asyncio.Task] = None
        self._aggregation_task: Optional[asyncio.Task] = None
        self._dashboard_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Alert handlers
        self.alert_handlers: List[Callable] = []
        
        self.logger.info("UnifiedMetricsCollector initialized")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "db_path": "unified_metrics.db",
            "collection_interval": 30,  # seconds
            "aggregation_interval": 60,  # seconds  
            "dashboard_update_interval": 30,  # seconds
            "retention_days": 30,
            "alert_thresholds": {
                "response_time_ms": 1000,
                "error_rate_percent": 5.0,
                "health_score": 70.0
            },
            "enable_trends": True,
            "enable_alerting": True
        }
    
    def _init_database(self):
        """Initialize metrics database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    component_type TEXT NOT NULL,
                    tags TEXT DEFAULT '{}',
                    metadata TEXT DEFAULT '{}',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Aggregated metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS aggregated_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    component_type TEXT NOT NULL,
                    time_period TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    count INTEGER NOT NULL,
                    avg REAL NOT NULL,
                    min REAL NOT NULL,
                    max REAL NOT NULL,
                    p50 REAL NOT NULL,
                    p95 REAL NOT NULL,
                    p99 REAL NOT NULL,
                    std_dev REAL NOT NULL,
                    trend REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Dashboard snapshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dashboard_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    overall_health REAL NOT NULL,
                    active_alerts INTEGER NOT NULL,
                    dashboard_data TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_component ON metrics(component_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_aggregated_period ON aggregated_metrics(time_period, start_time)")
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Metrics database initialized: {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize metrics database: {e}")
    
    async def start(self):
        """Start metrics collection and processing."""
        if self._running:
            return
        
        self._running = True
        
        # Start background tasks
        self._collection_task = asyncio.create_task(self._collection_loop())
        self._aggregation_task = asyncio.create_task(self._aggregation_loop())
        self._dashboard_task = asyncio.create_task(self._dashboard_loop())
        
        self.logger.info("UnifiedMetricsCollector started")
    
    async def stop(self):
        """Stop metrics collection and processing."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel background tasks
        tasks = [self._collection_task, self._aggregation_task, self._dashboard_task]
        for task in tasks:
            if task:
                task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self.logger.info("UnifiedMetricsCollector stopped")
    
    async def _collection_loop(self):
        """Background metrics collection loop."""
        while self._running:
            try:
                await self._collect_metrics()
                await asyncio.sleep(self.config.get("collection_interval", 30))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(5)
    
    async def _aggregation_loop(self):
        """Background metrics aggregation loop."""
        while self._running:
            try:
                await self._aggregate_metrics()
                await asyncio.sleep(self.config.get("aggregation_interval", 60))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics aggregation error: {e}")
                await asyncio.sleep(5)
    
    async def _dashboard_loop(self):
        """Background dashboard update loop."""
        while self._running:
            try:
                await self._update_dashboard()
                await asyncio.sleep(self.config.get("dashboard_update_interval", 30))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Dashboard update error: {e}")
                await asyncio.sleep(5)
    
    async def _collect_metrics(self):
        """Collect metrics from performance monitor."""
        try:
            # Get current metrics from performance monitor
            recent_metrics = [
                m for m in self.monitor.metrics 
                if m.start_time > time.time() - self.config.get("collection_interval", 30)
            ]
            
            for metric in recent_metrics:
                # Convert performance metric to metric point
                metric_point = MetricPoint(
                    timestamp=metric.start_time,
                    metric_name=f"{metric.operation_name}_duration",
                    value=metric.duration or 0,
                    component_type=metric.component_type,
                    tags={
                        "success": str(metric.success),
                        "performance_level": metric.performance_level.value if metric.performance_level else "unknown"
                    },
                    metadata=metric.metadata
                )
                
                await self._store_metric(metric_point)
            
            # Collect system-level metrics
            await self._collect_system_metrics()
            
        except Exception as e:
            self.logger.error(f"Metrics collection failed: {e}")
    
    async def _collect_system_metrics(self):
        """Collect system-level metrics."""
        try:
            # Component health scores
            for component_type in ComponentType:
                component_metrics = [
                    m for m in self.monitor.component_metrics[component_type]
                    if m.start_time > time.time() - 300  # Last 5 minutes
                ]
                
                if component_metrics:
                    health_score = self.monitor._calculate_component_health(component_metrics)
                    
                    health_metric = MetricPoint(
                        timestamp=time.time(),
                        metric_name="health_score",
                        value=health_score,
                        component_type=component_type,
                        tags={"metric_type": "health"},
                        metadata={"sample_size": len(component_metrics)}
                    )
                    
                    await self._store_metric(health_metric)
            
            # Throughput metrics
            for component_type in ComponentType:
                recent_count = len([
                    m for m in self.monitor.component_metrics[component_type]
                    if m.start_time > time.time() - 60  # Last minute
                ])
                
                throughput_metric = MetricPoint(
                    timestamp=time.time(),
                    metric_name="throughput_rpm",
                    value=recent_count,
                    component_type=component_type,
                    tags={"metric_type": "throughput"},
                    metadata={}
                )
                
                await self._store_metric(throughput_metric)
            
        except Exception as e:
            self.logger.error(f"System metrics collection failed: {e}")
    
    async def _store_metric(self, metric: MetricPoint):
        """Store metric in buffer and database."""
        try:
            # Add to buffer
            with self._lock:
                self.metrics_buffer.append(metric)
            
            # Update trends
            if self.config.get("enable_trends", True):
                trend_key = f"{metric.component_type.value}_{metric.metric_name}"
                self.performance_trends[trend_key].append(metric.value)
            
            # Store in database (async)
            await self._store_metric_db(metric)
            
        except Exception as e:
            self.logger.error(f"Failed to store metric: {e}")
    
    async def _store_metric_db(self, metric: MetricPoint):
        """Store metric in database asynchronously."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._store_metric_sync, metric)
        except Exception as e:
            self.logger.error(f"Database storage error: {e}")
    
    def _store_metric_sync(self, metric: MetricPoint):
        """Store metric in database synchronously."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO metrics (timestamp, metric_name, value, component_type, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                metric.timestamp,
                metric.metric_name,
                metric.value,
                metric.component_type.value,
                json.dumps(metric.tags),
                json.dumps(metric.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Database sync storage error: {e}")
    
    async def _aggregate_metrics(self):
        """Aggregate metrics over time periods."""
        try:
            current_time = datetime.now()
            
            # Define aggregation periods
            periods = [
                ("1m", timedelta(minutes=1)),
                ("5m", timedelta(minutes=5)),
                ("15m", timedelta(minutes=15)),
                ("1h", timedelta(hours=1)),
                ("24h", timedelta(hours=24))
            ]
            
            for period_name, period_delta in periods:
                start_time = current_time - period_delta
                
                # Aggregate by component and metric
                for component_type in ComponentType:
                    component_metrics = [
                        m for m in self.metrics_buffer
                        if (m.component_type == component_type and
                            datetime.fromtimestamp(m.timestamp) >= start_time)
                    ]
                    
                    # Group by metric name
                    metric_groups = defaultdict(list)
                    for metric in component_metrics:
                        metric_groups[metric.metric_name].append(metric.value)
                    
                    # Calculate aggregations
                    for metric_name, values in metric_groups.items():
                        if values:
                            aggregated = await self._calculate_aggregation(
                                metric_name, component_type, period_name, 
                                start_time, current_time, values
                            )
                            
                            await self._store_aggregated_metric(aggregated)
            
        except Exception as e:
            self.logger.error(f"Metrics aggregation failed: {e}")
    
    async def _calculate_aggregation(self, metric_name: str, component_type: ComponentType,
                                   period: str, start_time: datetime, end_time: datetime,
                                   values: List[float]) -> AggregatedMetric:
        """Calculate aggregated statistics for a metric."""
        count = len(values)
        avg = statistics.mean(values)
        min_val = min(values)
        max_val = max(values)
        p50 = statistics.median(values)
        p95 = statistics.quantiles(values, n=20)[18] if len(values) >= 20 else max_val
        p99 = statistics.quantiles(values, n=100)[98] if len(values) >= 100 else max_val
        std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
        
        # Calculate trend (simple linear trend)
        trend = self._calculate_trend(values) if len(values) >= 3 else 0.0
        
        return AggregatedMetric(
            metric_name=metric_name,
            component_type=component_type,
            time_period=period,
            start_time=start_time,
            end_time=end_time,
            count=count,
            avg=avg,
            min=min_val,
            max=max_val,
            p50=p50,
            p95=p95,
            p99=p99,
            std_dev=std_dev,
            trend=trend
        )
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend direction (-1 to 1)."""
        if len(values) < 3:
            return 0.0
        
        # Simple linear regression slope
        n = len(values)
        x_vals = list(range(n))
        
        sum_x = sum(x_vals)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(x_vals, values))
        sum_x2 = sum(x * x for x in x_vals)
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Normalize to -1 to 1 range
        max_slope = max(abs(slope), 1.0)
        return max(-1.0, min(1.0, slope / max_slope))
    
    async def _store_aggregated_metric(self, aggregated: AggregatedMetric):
        """Store aggregated metric in database."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._store_aggregated_sync, aggregated)
        except Exception as e:
            self.logger.error(f"Failed to store aggregated metric: {e}")
    
    def _store_aggregated_sync(self, aggregated: AggregatedMetric):
        """Store aggregated metric synchronously."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if already exists
            cursor.execute("""
                SELECT id FROM aggregated_metrics 
                WHERE metric_name = ? AND component_type = ? AND time_period = ? AND start_time = ?
            """, (aggregated.metric_name, aggregated.component_type.value, aggregated.time_period, aggregated.start_time.isoformat()))
            
            if cursor.fetchone():
                # Update existing
                cursor.execute("""
                    UPDATE aggregated_metrics SET
                        count = ?, avg = ?, min = ?, max = ?, p50 = ?, p95 = ?, p99 = ?, std_dev = ?, trend = ?
                    WHERE metric_name = ? AND component_type = ? AND time_period = ? AND start_time = ?
                """, (
                    aggregated.count, aggregated.avg, aggregated.min, aggregated.max,
                    aggregated.p50, aggregated.p95, aggregated.p99, aggregated.std_dev, aggregated.trend,
                    aggregated.metric_name, aggregated.component_type.value, aggregated.time_period, aggregated.start_time.isoformat()
                ))
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO aggregated_metrics (
                        metric_name, component_type, time_period, start_time, end_time,
                        count, avg, min, max, p50, p95, p99, std_dev, trend
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    aggregated.metric_name, aggregated.component_type.value, aggregated.time_period,
                    aggregated.start_time.isoformat(), aggregated.end_time.isoformat(),
                    aggregated.count, aggregated.avg, aggregated.min, aggregated.max,
                    aggregated.p50, aggregated.p95, aggregated.p99, aggregated.std_dev, aggregated.trend
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Aggregated metric sync storage error: {e}")


# Global metrics collector instance
metrics_collector = None  # Will be initialized properly
