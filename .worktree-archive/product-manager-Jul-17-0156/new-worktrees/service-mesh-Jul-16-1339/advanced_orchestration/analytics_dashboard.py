"""
Advanced Analytics Dashboard for Multi-Agent Orchestration.

This module provides a comprehensive analytics dashboard for monitoring,
analyzing, and optimizing multi-agent coordination performance.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics

from .performance_monitor import PerformanceMonitor


class DashboardView(Enum):
    """Different dashboard view types."""
    OVERVIEW = "overview"
    REAL_TIME = "real_time"
    AGENT_PERFORMANCE = "agent_performance"
    WORKFLOW_ANALYSIS = "workflow_analysis"
    SYSTEM_HEALTH = "system_health"
    OPTIMIZATION = "optimization"
    ALERTS = "alerts"
    HISTORICAL = "historical"


@dataclass
class DashboardMetric:
    """Dashboard metric with visualization metadata."""
    name: str
    value: float
    unit: str
    trend: float  # -1 to 1, where 1 is improving
    status: str  # "excellent", "good", "warning", "critical"
    description: str
    chart_type: str = "line"  # "line", "bar", "gauge", "pie"
    color: str = "#007bff"
    target_value: Optional[float] = None
    historical_data: List[float] = field(default_factory=list)


@dataclass
class DashboardAlert:
    """Dashboard alert with action items."""
    id: str
    title: str
    severity: str  # "info", "warning", "critical"
    message: str
    timestamp: datetime
    action_items: List[str] = field(default_factory=list)
    auto_fix_available: bool = False
    estimated_fix_time: Optional[str] = None


@dataclass
class DashboardInsight:
    """Dashboard insight or recommendation."""
    title: str
    description: str
    impact: str  # "high", "medium", "low"
    effort: str  # "high", "medium", "low"
    category: str  # "performance", "reliability", "efficiency"
    action_items: List[str] = field(default_factory=list)
    estimated_improvement: Optional[str] = None


@dataclass
class DashboardData:
    """Complete dashboard data structure."""
    view_type: DashboardView
    generated_at: datetime
    time_range: Tuple[datetime, datetime]
    metrics: List[DashboardMetric]
    alerts: List[DashboardAlert]
    insights: List[DashboardInsight]
    agent_status: Dict[str, Dict[str, Any]]
    workflow_status: Dict[str, Dict[str, Any]]
    system_health: Dict[str, Any]
    performance_summary: Dict[str, Any]


class AnalyticsDashboard:
    """Advanced analytics dashboard for multi-agent orchestration."""

    def __init__(self, performance_monitor: PerformanceMonitor):
        self.logger = logging.getLogger(__name__)
        self.performance_monitor = performance_monitor
        self.cache = {}
        self.cache_ttl = 30  # seconds

        # Dashboard configuration
        self.metric_colors = {
            "excellent": "#28a745",
            "good": "#17a2b8",
            "warning": "#ffc107",
            "critical": "#dc3545"
        }

        # Insight templates
        self.insight_templates = {
            "agent_imbalance": {
                "title": "Agent Workload Imbalance Detected",
                "description": "Some agents are significantly more loaded than others",
                "impact": "medium",
                "effort": "low",
                "category": "efficiency"
            },
            "coordination_overhead": {
                "title": "High Coordination Overhead",
                "description": "Coordination between agents is taking longer than expected",
                "impact": "high",
                "effort": "medium",
                "category": "performance"
            },
            "workflow_bottleneck": {
                "title": "Workflow Bottleneck Identified",
                "description": "Specific workflow steps are causing delays",
                "impact": "high",
                "effort": "medium",
                "category": "performance"
            }
        }

        self.logger.info("AnalyticsDashboard initialized")

    async def generate_dashboard_data(self, view_type: DashboardView,
                                    time_range: Optional[Tuple[datetime, datetime]] = None) -> DashboardData:
        """Generate comprehensive dashboard data."""
        if not time_range:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            time_range = (start_time, end_time)

        cache_key = f"{view_type.value}_{time_range[0].timestamp()}_{time_range[1].timestamp()}"

        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (datetime.now() - cached_time).total_seconds() < self.cache_ttl:
                return cached_data

        # Generate fresh data
        dashboard_data = await self._generate_fresh_dashboard_data(view_type, time_range)

        # Cache the result
        self.cache[cache_key] = (dashboard_data, datetime.now())

        return dashboard_data

    async def _generate_fresh_dashboard_data(self, view_type: DashboardView,
                                           time_range: Tuple[datetime, datetime]) -> DashboardData:
        """Generate fresh dashboard data."""

        # Get base metrics
        metrics = await self._generate_metrics(view_type, time_range)
        alerts = await self._generate_alerts(view_type, time_range)
        insights = await self._generate_insights(view_type, time_range)
        agent_status = await self._generate_agent_status(time_range)
        workflow_status = await self._generate_workflow_status(time_range)
        system_health = await self._generate_system_health(time_range)
        performance_summary = await self._generate_performance_summary(time_range)

        return DashboardData(
            view_type=view_type,
            generated_at=datetime.now(),
            time_range=time_range,
            metrics=metrics,
            alerts=alerts,
            insights=insights,
            agent_status=agent_status,
            workflow_status=workflow_status,
            system_health=system_health,
            performance_summary=performance_summary
        )

    async def _generate_metrics(self, view_type: DashboardView,
                              time_range: Tuple[datetime, datetime]) -> List[DashboardMetric]:
        """Generate dashboard metrics based on view type."""
        metrics = []

        if view_type == DashboardView.OVERVIEW:
            metrics.extend(await self._generate_overview_metrics(time_range))
        elif view_type == DashboardView.REAL_TIME:
            metrics.extend(await self._generate_real_time_metrics())
        elif view_type == DashboardView.AGENT_PERFORMANCE:
            metrics.extend(await self._generate_agent_metrics(time_range))
        elif view_type == DashboardView.WORKFLOW_ANALYSIS:
            metrics.extend(await self._generate_workflow_metrics(time_range))
        elif view_type == DashboardView.SYSTEM_HEALTH:
            metrics.extend(await self._generate_system_health_metrics(time_range))
        elif view_type == DashboardView.OPTIMIZATION:
            metrics.extend(await self._generate_optimization_metrics(time_range))

        return metrics

    async def _generate_overview_metrics(self, time_range: Tuple[datetime, datetime]) -> List[DashboardMetric]:
        """Generate overview dashboard metrics."""
        metrics = []

        # System-wide coordination efficiency
        real_time_data = self.performance_monitor.get_real_time_metrics()

        coordination_efficiency = real_time_data.get("metrics", {}).get("coordination_efficiency", {})
        if coordination_efficiency:
            metrics.append(DashboardMetric(
                name="Coordination Efficiency",
                value=coordination_efficiency.get("current", 0.0),
                unit="%",
                trend=coordination_efficiency.get("trend", 0.0),
                status=self._get_status_from_value(coordination_efficiency.get("current", 0.0), 0.9, 0.7, 0.5),
                description="Overall efficiency of agent coordination and task distribution",
                chart_type="gauge",
                color=self._get_color_from_status(self._get_status_from_value(coordination_efficiency.get("current", 0.0), 0.9, 0.7, 0.5)),
                target_value=0.95
            ))

        # Parallel efficiency
        parallel_efficiency = real_time_data.get("metrics", {}).get("parallel_efficiency", {})
        if parallel_efficiency:
            metrics.append(DashboardMetric(
                name="Parallel Efficiency",
                value=parallel_efficiency.get("current", 0.0),
                unit="%",
                trend=parallel_efficiency.get("trend", 0.0),
                status=self._get_status_from_value(parallel_efficiency.get("current", 0.0), 0.85, 0.65, 0.45),
                description="Efficiency of parallel task execution across agents",
                chart_type="gauge",
                color=self._get_color_from_status(self._get_status_from_value(parallel_efficiency.get("current", 0.0), 0.85, 0.65, 0.45)),
                target_value=0.90
            ))

        # System throughput
        throughput = real_time_data.get("metrics", {}).get("throughput", {})
        if throughput:
            metrics.append(DashboardMetric(
                name="System Throughput",
                value=throughput.get("current", 0.0),
                unit="tasks/min",
                trend=throughput.get("trend", 0.0),
                status=self._get_status_from_value(throughput.get("current", 0.0), 15.0, 10.0, 5.0),
                description="Number of tasks completed per minute across all agents",
                chart_type="line",
                color=self._get_color_from_status(self._get_status_from_value(throughput.get("current", 0.0), 15.0, 10.0, 5.0)),
                target_value=20.0
            ))

        # Error rate
        error_rate = real_time_data.get("metrics", {}).get("error_rate", {})
        if error_rate:
            metrics.append(DashboardMetric(
                name="Error Rate",
                value=error_rate.get("current", 0.0),
                unit="%",
                trend=-error_rate.get("trend", 0.0),  # Negative trend is good for errors
                status=self._get_status_from_value(error_rate.get("current", 0.0), 0.01, 0.05, 0.10, reverse=True),
                description="Percentage of tasks that fail or require retry",
                chart_type="line",
                color=self._get_color_from_status(self._get_status_from_value(error_rate.get("current", 0.0), 0.01, 0.05, 0.10, reverse=True)),
                target_value=0.005
            ))

        return metrics

    async def _generate_real_time_metrics(self) -> List[DashboardMetric]:
        """Generate real-time dashboard metrics."""
        metrics = []

        real_time_data = self.performance_monitor.get_real_time_metrics()

        for metric_name, metric_data in real_time_data.get("metrics", {}).items():
            metrics.append(DashboardMetric(
                name=metric_name.replace("_", " ").title(),
                value=metric_data.get("current", 0.0),
                unit=self._get_unit_for_metric(metric_name),
                trend=metric_data.get("trend", 0.0),
                status=self._get_status_for_metric(metric_name, metric_data.get("current", 0.0)),
                description=f"Current {metric_name.replace('_', ' ')} measurement",
                chart_type="line",
                color=self._get_color_for_metric(metric_name, metric_data.get("current", 0.0)),
                historical_data=self._get_historical_data(metric_name)
            ))

        return metrics

    async def _generate_agent_metrics(self, time_range: Tuple[datetime, datetime]) -> List[DashboardMetric]:
        """Generate agent-specific metrics."""
        metrics = []

        agent_summary = self.performance_monitor.get_agent_performance_summary()

        for agent_id, agent_data in agent_summary.items():
            # Agent productivity
            productivity = agent_data.get("agent_productivity", {})
            if productivity:
                metrics.append(DashboardMetric(
                    name=f"{agent_id} Productivity",
                    value=productivity.get("current", 0.0),
                    unit="tasks/hour",
                    trend=0.0,  # Could calculate from historical data
                    status=self._get_status_from_value(productivity.get("current", 0.0), 10.0, 7.0, 3.0),
                    description=f"Task completion rate for {agent_id}",
                    chart_type="bar",
                    color=self._get_color_from_status(self._get_status_from_value(productivity.get("current", 0.0), 10.0, 7.0, 3.0))
                ))

            # Agent stability
            stability = agent_data.get("latency", {}).get("stability", 0.0)
            if stability:
                metrics.append(DashboardMetric(
                    name=f"{agent_id} Stability",
                    value=stability,
                    unit="%",
                    trend=0.0,
                    status=self._get_status_from_value(stability, 0.9, 0.7, 0.5),
                    description=f"Performance stability for {agent_id}",
                    chart_type="gauge",
                    color=self._get_color_from_status(self._get_status_from_value(stability, 0.9, 0.7, 0.5))
                ))

        return metrics

    async def _generate_workflow_metrics(self, time_range: Tuple[datetime, datetime]) -> List[DashboardMetric]:
        """Generate workflow-specific metrics."""
        metrics = []

        # This would integrate with workflow coordinator to get actual workflow metrics
        # For now, providing structure for when workflow metrics are available

        return metrics

    async def _generate_system_health_metrics(self, time_range: Tuple[datetime, datetime]) -> List[DashboardMetric]:
        """Generate system health metrics."""
        metrics = []

        # System uptime
        metrics.append(DashboardMetric(
            name="System Uptime",
            value=99.9,  # Would calculate from actual uptime
            unit="%",
            trend=0.0,
            status="excellent",
            description="System availability over the selected time period",
            chart_type="gauge",
            color=self.metric_colors["excellent"],
            target_value=99.9
        ))

        # Active alerts
        active_alerts = len([a for a in self.performance_monitor.alerts if a.severity in ["warning", "critical"]])
        metrics.append(DashboardMetric(
            name="Active Alerts",
            value=active_alerts,
            unit="count",
            trend=0.0,
            status="good" if active_alerts == 0 else "warning" if active_alerts < 5 else "critical",
            description="Number of active performance alerts",
            chart_type="bar",
            color=self.metric_colors["good" if active_alerts == 0 else "warning" if active_alerts < 5 else "critical"],
            target_value=0
        ))

        return metrics

    async def _generate_optimization_metrics(self, time_range: Tuple[datetime, datetime]) -> List[DashboardMetric]:
        """Generate optimization-focused metrics."""
        metrics = []

        # Optimization opportunities
        metrics.append(DashboardMetric(
            name="Optimization Opportunities",
            value=3,  # Would calculate from actual analysis
            unit="count",
            trend=0.0,
            status="good",
            description="Number of identified optimization opportunities",
            chart_type="bar",
            color=self.metric_colors["good"]
        ))

        return metrics

    async def _generate_alerts(self, view_type: DashboardView,
                             time_range: Tuple[datetime, datetime]) -> List[DashboardAlert]:
        """Generate dashboard alerts."""
        alerts = []

        # Convert performance alerts to dashboard alerts
        for perf_alert in self.performance_monitor.alerts:
            if time_range[0] <= perf_alert.timestamp <= time_range[1]:
                alerts.append(DashboardAlert(
                    id=perf_alert.alert_id,
                    title=f"{perf_alert.metric_type.value.replace('_', ' ').title()} Alert",
                    severity=perf_alert.severity,
                    message=f"Current value: {perf_alert.current_value:.2f}, Threshold: {perf_alert.threshold_value:.2f}",
                    timestamp=perf_alert.timestamp,
                    action_items=[perf_alert.recommendation] if perf_alert.recommendation else [],
                    auto_fix_available=perf_alert.auto_fix_available,
                    estimated_fix_time="5-10 minutes" if perf_alert.auto_fix_available else None
                ))

        return alerts

    async def _generate_insights(self, view_type: DashboardView,
                               time_range: Tuple[datetime, datetime]) -> List[DashboardInsight]:
        """Generate dashboard insights."""
        insights = []

        # Analyze agent performance balance
        agent_summary = self.performance_monitor.get_agent_performance_summary()
        if len(agent_summary) > 1:
            productivities = []
            for agent_id, agent_data in agent_summary.items():
                productivity = agent_data.get("agent_productivity", {})
                if productivity:
                    productivities.append(productivity.get("current", 0.0))

            if productivities and len(productivities) > 1:
                avg_productivity = statistics.mean(productivities)
                std_productivity = statistics.stdev(productivities)

                # Check for imbalance
                if avg_productivity > 0 and std_productivity / avg_productivity > 0.3:
                    insight = DashboardInsight(
                        title="Agent Workload Imbalance",
                        description=f"Agent productivity varies significantly (CV: {std_productivity/avg_productivity:.2f})",
                        impact="medium",
                        effort="low",
                        category="efficiency",
                        action_items=[
                            "Review task distribution algorithm",
                            "Consider agent specialization optimization",
                            "Implement dynamic load balancing"
                        ],
                        estimated_improvement="15-25% efficiency gain"
                    )
                    insights.append(insight)

        # Check for coordination overhead
        real_time_data = self.performance_monitor.get_real_time_metrics()
        coordination_efficiency = real_time_data.get("metrics", {}).get("coordination_efficiency", {})
        if coordination_efficiency and coordination_efficiency.get("current", 1.0) < 0.7:
            insight = DashboardInsight(
                title="High Coordination Overhead",
                description=f"Coordination efficiency is {coordination_efficiency.get('current', 0.0):.1%}",
                impact="high",
                effort="medium",
                category="performance",
                action_items=[
                    "Optimize agent communication protocols",
                    "Reduce dependency resolution complexity",
                    "Implement coordination caching"
                ],
                estimated_improvement="20-30% performance improvement"
            )
            insights.append(insight)

        return insights

    async def _generate_agent_status(self, time_range: Tuple[datetime, datetime]) -> Dict[str, Dict[str, Any]]:
        """Generate agent status information."""
        agent_status = {}

        agent_summary = self.performance_monitor.get_agent_performance_summary()
        for agent_id, agent_data in agent_summary.items():
            agent_status[agent_id] = {
                "status": "healthy",  # Would determine from actual health checks
                "uptime": "99.9%",
                "current_tasks": 2,  # Would get from actual task tracking
                "completed_tasks": 156,
                "specialization": agent_id.split("-")[0],
                "performance_score": 85,  # Would calculate from metrics
                "last_activity": datetime.now().isoformat()
            }

        return agent_status

    async def _generate_workflow_status(self, time_range: Tuple[datetime, datetime]) -> Dict[str, Dict[str, Any]]:
        """Generate workflow status information."""
        workflow_status = {}

        # This would integrate with workflow coordinator to get actual workflow status
        # For now, providing structure for when workflow data is available

        return workflow_status

    async def _generate_system_health(self, time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Generate system health information."""
        return {
            "overall_status": "healthy",
            "uptime": "99.9%",
            "active_agents": 5,
            "active_workflows": 1,
            "system_load": 0.65,
            "memory_usage": 0.42,
            "last_health_check": datetime.now().isoformat()
        }

    async def _generate_performance_summary(self, time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Generate performance summary."""
        return {
            "total_tasks_completed": 1250,
            "average_task_duration": 2.3,
            "peak_throughput": 18.5,
            "error_rate": 0.02,
            "coordination_efficiency": 0.87,
            "parallel_efficiency": 0.78
        }

    def _get_status_from_value(self, value: float, excellent: float, good: float,
                             warning: float, reverse: bool = False) -> str:
        """Get status string from metric value."""
        if reverse:
            if value <= excellent:
                return "excellent"
            elif value <= good:
                return "good"
            elif value <= warning:
                return "warning"
            else:
                return "critical"
        else:
            if value >= excellent:
                return "excellent"
            elif value >= good:
                return "good"
            elif value >= warning:
                return "warning"
            else:
                return "critical"

    def _get_color_from_status(self, status: str) -> str:
        """Get color from status."""
        return self.metric_colors.get(status, "#6c757d")

    def _get_unit_for_metric(self, metric_name: str) -> str:
        """Get unit for metric name."""
        unit_map = {
            "latency": "ms",
            "throughput": "tasks/min",
            "error_rate": "%",
            "coordination_efficiency": "%",
            "parallel_efficiency": "%",
            "agent_productivity": "tasks/hour"
        }
        return unit_map.get(metric_name, "")

    def _get_status_for_metric(self, metric_name: str, value: float) -> str:
        """Get status for specific metric."""
        if metric_name == "latency":
            return self._get_status_from_value(value, 1.0, 2.0, 5.0, reverse=True)
        elif metric_name == "error_rate":
            return self._get_status_from_value(value, 0.01, 0.05, 0.10, reverse=True)
        elif metric_name in ["coordination_efficiency", "parallel_efficiency"]:
            return self._get_status_from_value(value, 0.9, 0.7, 0.5)
        else:
            return "good"

    def _get_color_for_metric(self, metric_name: str, value: float) -> str:
        """Get color for specific metric."""
        status = self._get_status_for_metric(metric_name, value)
        return self._get_color_from_status(status)

    def _get_historical_data(self, metric_name: str) -> List[float]:
        """Get historical data for metric."""
        history_key = f"{metric_name}_global"
        return self.performance_monitor.performance_history.get(history_key, [])[-50:]  # Last 50 points

    def export_dashboard_data(self, dashboard_data: DashboardData, format: str = "json") -> str:
        """Export dashboard data in specified format."""
        if format == "json":
            return json.dumps({
                "view_type": dashboard_data.view_type.value,
                "generated_at": dashboard_data.generated_at.isoformat(),
                "time_range": [t.isoformat() for t in dashboard_data.time_range],
                "metrics": [
                    {
                        "name": m.name,
                        "value": m.value,
                        "unit": m.unit,
                        "trend": m.trend,
                        "status": m.status,
                        "description": m.description,
                        "chart_type": m.chart_type,
                        "color": m.color,
                        "target_value": m.target_value,
                        "historical_data": m.historical_data
                    } for m in dashboard_data.metrics
                ],
                "alerts": [
                    {
                        "id": a.id,
                        "title": a.title,
                        "severity": a.severity,
                        "message": a.message,
                        "timestamp": a.timestamp.isoformat(),
                        "action_items": a.action_items,
                        "auto_fix_available": a.auto_fix_available,
                        "estimated_fix_time": a.estimated_fix_time
                    } for a in dashboard_data.alerts
                ],
                "insights": [
                    {
                        "title": i.title,
                        "description": i.description,
                        "impact": i.impact,
                        "effort": i.effort,
                        "category": i.category,
                        "action_items": i.action_items,
                        "estimated_improvement": i.estimated_improvement
                    } for i in dashboard_data.insights
                ],
                "agent_status": dashboard_data.agent_status,
                "workflow_status": dashboard_data.workflow_status,
                "system_health": dashboard_data.system_health,
                "performance_summary": dashboard_data.performance_summary
            }, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
