"""
Monitoring and metrics collection system for the message queue.
Provides comprehensive insights into system performance and health.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import time

from .models import MessageQueueStats
from .queue_service import MessageQueueService
from .agent_registry import AgentRegistry
from .message_broker import MessageBroker


logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


@dataclass
class SystemHealth:
    """Overall system health status."""
    status: str  # healthy, degraded, unhealthy
    score: float  # 0-100
    message_queue_health: float
    agent_registry_health: float
    broker_health: float
    last_updated: datetime
    issues: List[str] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot."""
    messages_per_second: float
    average_latency_ms: float
    error_rate: float
    agent_availability: float
    queue_utilization: float
    memory_usage_mb: float
    timestamp: datetime


class MetricsCollector:
    """Collects and aggregates metrics from various system components."""

    def __init__(self,
                 queue_service: MessageQueueService,
                 agent_registry: AgentRegistry,
                 message_broker: MessageBroker,
                 retention_hours: int = 24):
        self.queue_service = queue_service
        self.agent_registry = agent_registry
        self.message_broker = message_broker
        self.retention_hours = retention_hours

        # In-memory metrics storage
        self.metrics: List[MetricPoint] = []
        self.performance_history: List[PerformanceMetrics] = []
        self.health_history: List[SystemHealth] = []

        # Aggregated statistics
        self.hourly_stats: Dict[str, Dict] = {}
        self.daily_stats: Dict[str, Dict] = {}

        # Collection state
        self.is_collecting = False
        self._collection_tasks: List[asyncio.Task] = []

        # Performance tracking
        self._last_message_count = 0
        self._last_collection_time = datetime.utcnow()

    async def start_collection(self, interval_seconds: int = 30):
        """Start metrics collection."""
        self.is_collecting = True

        self._collection_tasks = [
            asyncio.create_task(self._collect_metrics_loop(interval_seconds)),
            asyncio.create_task(self._cleanup_old_metrics()),
            asyncio.create_task(self._aggregate_metrics())
        ]

        logger.info("Metrics collection started")

    async def stop_collection(self):
        """Stop metrics collection."""
        self.is_collecting = False

        for task in self._collection_tasks:
            task.cancel()

        if self._collection_tasks:
            await asyncio.gather(*self._collection_tasks, return_exceptions=True)

        logger.info("Metrics collection stopped")

    async def collect_current_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics."""
        current_time = datetime.utcnow()

        try:
            # Queue metrics
            queue_stats = await self.queue_service.get_queue_stats()

            # Agent metrics
            agent_stats = await self.agent_registry.get_registry_stats()

            # Broker metrics
            broker_stats = await self.message_broker.get_broker_stats()

            # Calculate performance metrics
            messages_delta = queue_stats.delivered_messages - self._last_message_count
            time_delta = (current_time - self._last_collection_time).total_seconds()
            messages_per_second = messages_delta / max(time_delta, 1)

            # Update tracking variables
            self._last_message_count = queue_stats.delivered_messages
            self._last_collection_time = current_time

            # System health calculation
            health = await self._calculate_system_health(queue_stats, agent_stats, broker_stats)

            # Performance metrics
            performance = PerformanceMetrics(
                messages_per_second=messages_per_second,
                average_latency_ms=queue_stats.average_delivery_time,
                error_rate=broker_stats.get('routing_failures', 0) / max(broker_stats.get('messages_routed', 1), 1),
                agent_availability=agent_stats.get('online_agents', 0) / max(agent_stats.get('total_agents', 1), 1),
                queue_utilization=queue_stats.queue_size / 10000,  # Assuming max 10k messages
                memory_usage_mb=await self._get_memory_usage(),
                timestamp=current_time
            )

            # Store metrics
            await self._store_metrics(queue_stats, agent_stats, broker_stats, performance, health)

            return {
                'queue': asdict(queue_stats),
                'agents': agent_stats,
                'broker': broker_stats,
                'performance': asdict(performance),
                'health': asdict(health),
                'timestamp': current_time.isoformat()
            }

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {}

    async def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get metrics summary for specified time period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Filter recent metrics
        recent_metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
        recent_performance = [p for p in self.performance_history if p.timestamp > cutoff_time]
        recent_health = [h for h in self.health_history if h.timestamp > cutoff_time]

        if not recent_metrics:
            return {}

        # Calculate averages
        avg_messages_per_second = sum(p.messages_per_second for p in recent_performance) / len(recent_performance) if recent_performance else 0
        avg_latency = sum(p.average_latency_ms for p in recent_performance) / len(recent_performance) if recent_performance else 0
        avg_error_rate = sum(p.error_rate for p in recent_performance) / len(recent_performance) if recent_performance else 0
        avg_health_score = sum(h.score for h in recent_health) / len(recent_health) if recent_health else 0

        # Get current values
        current_health = recent_health[-1] if recent_health else None
        current_performance = recent_performance[-1] if recent_performance else None

        return {
            'time_period_hours': hours,
            'total_metrics': len(recent_metrics),
            'averages': {
                'messages_per_second': avg_messages_per_second,
                'latency_ms': avg_latency,
                'error_rate': avg_error_rate,
                'health_score': avg_health_score
            },
            'current': {
                'health': asdict(current_health) if current_health else None,
                'performance': asdict(current_performance) if current_performance else None
            },
            'trends': await self._calculate_trends(recent_performance)
        }

    async def get_alerts(self) -> List[Dict[str, Any]]:
        """Get current system alerts."""
        alerts = []

        try:
            # Recent health check
            if self.health_history:
                latest_health = self.health_history[-1]

                if latest_health.score < 50:
                    alerts.append({
                        'level': 'critical',
                        'message': 'System health score below 50%',
                        'value': latest_health.score,
                        'timestamp': latest_health.last_updated.isoformat()
                    })
                elif latest_health.score < 75:
                    alerts.append({
                        'level': 'warning',
                        'message': 'System health score below 75%',
                        'value': latest_health.score,
                        'timestamp': latest_health.last_updated.isoformat()
                    })

                # Check for specific issues
                for issue in latest_health.issues:
                    alerts.append({
                        'level': 'warning',
                        'message': issue,
                        'timestamp': latest_health.last_updated.isoformat()
                    })

            # Performance alerts
            if self.performance_history:
                latest_performance = self.performance_history[-1]

                if latest_performance.error_rate > 0.1:  # >10% error rate
                    alerts.append({
                        'level': 'critical',
                        'message': f'High error rate: {latest_performance.error_rate:.1%}',
                        'value': latest_performance.error_rate,
                        'timestamp': latest_performance.timestamp.isoformat()
                    })

                if latest_performance.average_latency_ms > 5000:  # >5 second latency
                    alerts.append({
                        'level': 'warning',
                        'message': f'High message latency: {latest_performance.average_latency_ms:.0f}ms',
                        'value': latest_performance.average_latency_ms,
                        'timestamp': latest_performance.timestamp.isoformat()
                    })

                if latest_performance.agent_availability < 0.8:  # <80% agents available
                    alerts.append({
                        'level': 'warning',
                        'message': f'Low agent availability: {latest_performance.agent_availability:.1%}',
                        'value': latest_performance.agent_availability,
                        'timestamp': latest_performance.timestamp.isoformat()
                    })

        except Exception as e:
            logger.error(f"Error generating alerts: {e}")

        return alerts

    async def export_metrics(self, format: str = "json", hours: int = 24) -> str:
        """Export metrics in specified format."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Collect data
        metrics_data = {
            'export_time': datetime.utcnow().isoformat(),
            'time_period_hours': hours,
            'metrics': [
                asdict(m) for m in self.metrics
                if m.timestamp > cutoff_time
            ],
            'performance_history': [
                asdict(p) for p in self.performance_history
                if p.timestamp > cutoff_time
            ],
            'health_history': [
                asdict(h) for h in self.health_history
                if h.timestamp > cutoff_time
            ],
            'summary': await self.get_metrics_summary(hours)
        }

        if format.lower() == "json":
            return json.dumps(metrics_data, indent=2, default=str)
        else:
            # Could add CSV, XML, etc.
            return json.dumps(metrics_data, default=str)

    async def _collect_metrics_loop(self, interval_seconds: int):
        """Background metrics collection loop."""
        while self.is_collecting:
            try:
                await self.collect_current_metrics()
                await asyncio.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _cleanup_old_metrics(self):
        """Remove old metrics beyond retention period."""
        while self.is_collecting:
            try:
                cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)

                # Clean up metrics
                self.metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
                self.performance_history = [p for p in self.performance_history if p.timestamp > cutoff_time]
                self.health_history = [h for h in self.health_history if h.timestamp > cutoff_time]

                logger.debug(f"Cleaned up old metrics. Retained: {len(self.metrics)} metrics")

                await asyncio.sleep(3600)  # Clean up every hour

            except Exception as e:
                logger.error(f"Error in metrics cleanup: {e}")
                await asyncio.sleep(3600)

    async def _aggregate_metrics(self):
        """Aggregate metrics into hourly and daily summaries."""
        while self.is_collecting:
            try:
                # This would implement time-series aggregation
                # For now, just placeholder
                await asyncio.sleep(1800)  # Run every 30 minutes

            except Exception as e:
                logger.error(f"Error in metrics aggregation: {e}")
                await asyncio.sleep(3600)

    async def _store_metrics(self,
                           queue_stats: MessageQueueStats,
                           agent_stats: Dict,
                           broker_stats: Dict,
                           performance: PerformanceMetrics,
                           health: SystemHealth):
        """Store collected metrics."""
        timestamp = datetime.utcnow()

        # Store individual metrics
        metrics_to_add = [
            MetricPoint(timestamp, "queue.total_messages", queue_stats.total_messages),
            MetricPoint(timestamp, "queue.pending_messages", queue_stats.pending_messages),
            MetricPoint(timestamp, "queue.delivered_messages", queue_stats.delivered_messages),
            MetricPoint(timestamp, "queue.size", queue_stats.queue_size),
            MetricPoint(timestamp, "queue.avg_delivery_time", queue_stats.average_delivery_time),
            MetricPoint(timestamp, "agents.total", agent_stats.get('total_agents', 0)),
            MetricPoint(timestamp, "agents.online", agent_stats.get('online_agents', 0)),
            MetricPoint(timestamp, "broker.messages_routed", broker_stats.get('messages_routed', 0)),
            MetricPoint(timestamp, "broker.routing_failures", broker_stats.get('routing_failures', 0)),
            MetricPoint(timestamp, "performance.messages_per_second", performance.messages_per_second),
            MetricPoint(timestamp, "performance.latency_ms", performance.average_latency_ms),
            MetricPoint(timestamp, "performance.error_rate", performance.error_rate),
            MetricPoint(timestamp, "health.score", health.score)
        ]

        self.metrics.extend(metrics_to_add)
        self.performance_history.append(performance)
        self.health_history.append(health)

        # Limit memory usage
        max_metrics = 10000
        if len(self.metrics) > max_metrics:
            self.metrics = self.metrics[-max_metrics:]

        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]

        if len(self.health_history) > 1000:
            self.health_history = self.health_history[-1000:]

    async def _calculate_system_health(self,
                                     queue_stats: MessageQueueStats,
                                     agent_stats: Dict,
                                     broker_stats: Dict) -> SystemHealth:
        """Calculate overall system health score."""
        issues = []

        # Queue health (0-25 points)
        queue_health = 25
        if queue_stats.queue_size > 5000:  # High queue size
            queue_health -= 10
            issues.append("High message queue size")
        if queue_stats.average_delivery_time > 10000:  # >10s delivery time
            queue_health -= 10
            issues.append("High message delivery latency")
        if queue_stats.pending_messages > 1000:  # Many pending
            queue_health -= 5
            issues.append("Many pending messages")

        # Agent health (0-25 points)
        total_agents = agent_stats.get('total_agents', 1)
        online_agents = agent_stats.get('online_agents', 0)
        agent_availability = online_agents / max(total_agents, 1)

        agent_health = 25 * agent_availability
        if agent_availability < 0.8:
            issues.append(f"Low agent availability: {agent_availability:.1%}")
        if total_agents < 3:
            agent_health -= 5
            issues.append("Few registered agents")

        # Broker health (0-25 points)
        messages_routed = broker_stats.get('messages_routed', 0)
        routing_failures = broker_stats.get('routing_failures', 0)

        if messages_routed > 0:
            success_rate = (messages_routed - routing_failures) / messages_routed
            broker_health = 25 * success_rate
            if success_rate < 0.9:
                issues.append(f"Low routing success rate: {success_rate:.1%}")
        else:
            broker_health = 25  # No data yet, assume healthy

        # System responsiveness (0-25 points)
        responsiveness_health = 25
        if queue_stats.average_delivery_time > 5000:
            responsiveness_health -= 10
        if broker_stats.get('average_routing_time_ms', 0) > 1000:
            responsiveness_health -= 10
            issues.append("Slow message routing")

        # Calculate overall score
        total_score = queue_health + agent_health + broker_health + responsiveness_health

        # Determine status
        if total_score >= 90:
            status = "healthy"
        elif total_score >= 70:
            status = "degraded"
        else:
            status = "unhealthy"

        return SystemHealth(
            status=status,
            score=total_score,
            message_queue_health=queue_health,
            agent_registry_health=agent_health,
            broker_health=broker_health,
            last_updated=datetime.utcnow(),
            issues=issues
        )

    async def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            return 0.0  # psutil not available
        except Exception:
            return 0.0

    async def _calculate_trends(self, performance_data: List[PerformanceMetrics]) -> Dict[str, str]:
        """Calculate performance trends."""
        if len(performance_data) < 2:
            return {}

        # Simple trend calculation
        recent = performance_data[-5:]  # Last 5 data points
        older = performance_data[-10:-5] if len(performance_data) >= 10 else performance_data[:-5]

        if not older:
            return {}

        trends = {}

        # Messages per second trend
        recent_avg_mps = sum(p.messages_per_second for p in recent) / len(recent)
        older_avg_mps = sum(p.messages_per_second for p in older) / len(older)
        if recent_avg_mps > older_avg_mps * 1.1:
            trends['messages_per_second'] = 'increasing'
        elif recent_avg_mps < older_avg_mps * 0.9:
            trends['messages_per_second'] = 'decreasing'
        else:
            trends['messages_per_second'] = 'stable'

        # Latency trend
        recent_avg_latency = sum(p.average_latency_ms for p in recent) / len(recent)
        older_avg_latency = sum(p.average_latency_ms for p in older) / len(older)
        if recent_avg_latency > older_avg_latency * 1.2:
            trends['latency'] = 'increasing'
        elif recent_avg_latency < older_avg_latency * 0.8:
            trends['latency'] = 'decreasing'
        else:
            trends['latency'] = 'stable'

        # Error rate trend
        recent_avg_error = sum(p.error_rate for p in recent) / len(recent)
        older_avg_error = sum(p.error_rate for p in older) / len(older)
        if recent_avg_error > older_avg_error * 1.5:
            trends['error_rate'] = 'increasing'
        elif recent_avg_error < older_avg_error * 0.5:
            trends['error_rate'] = 'decreasing'
        else:
            trends['error_rate'] = 'stable'

        return trends
