#!/usr/bin/env python3
"""
Monitoring Health Validation System
Foundation Epic Phase 1: System monitoring and health validation

Provides comprehensive health validation endpoints and real-time monitoring
integration for the agent orchestration system.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
from enum import Enum

from observability.baseline_metrics import metrics_collector, baseline_analyzer
from observability.hook_manager import hook_manager
from performance_monitoring_optimization import PerformanceMonitoringOptimization

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"  
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status for a system component."""
    component_name: str
    status: HealthStatus
    score: float  # 0.0 to 1.0
    message: str
    metrics: Dict[str, Any]
    last_check: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_name": self.component_name,
            "status": self.status.value,
            "score": self.score,
            "message": self.message,
            "metrics": self.metrics,
            "last_check": self.last_check.isoformat()
        }


@dataclass
class SystemHealthReport:
    """Comprehensive system health report."""
    overall_status: HealthStatus
    overall_score: float
    component_health: List[ComponentHealth]
    active_alerts: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
    recommendations: List[str]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "overall_score": self.overall_score,
            "component_health": [c.to_dict() for c in self.component_health],
            "active_alerts": self.active_alerts,
            "performance_metrics": self.performance_metrics,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat()
        }


class MonitoringHealthValidator:
    """System monitoring and health validation coordinator."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.performance_monitor = PerformanceMonitoringOptimization()
        self.health_history: List[SystemHealthReport] = []
        self.validation_interval = 30  # seconds
        self.running = False
        
    async def start_monitoring(self):
        """Start health validation monitoring."""
        if self.running:
            return
            
        self.running = True
        
        # Start baseline metrics collection
        metrics_collector.start_collection()
        
        # Start hook manager
        await hook_manager.start()
        
        # Start performance monitoring
        await self.performance_monitor.start_monitoring()
        
        # Start health validation loop
        asyncio.create_task(self._health_validation_loop())
        
        self.logger.info("Monitoring health validation started")
    
    async def stop_monitoring(self):
        """Stop health validation monitoring."""
        if not self.running:
            return
            
        self.running = False
        
        # Stop components
        metrics_collector.stop_collection()
        await hook_manager.stop()
        await self.performance_monitor.stop_monitoring()
        
        self.logger.info("Monitoring health validation stopped")
    
    async def get_system_health(self) -> SystemHealthReport:
        """Get comprehensive system health report."""
        timestamp = datetime.now()
        
        # Collect component health
        component_health = await self._collect_component_health()
        
        # Calculate overall health
        overall_score = sum(c.score for c in component_health) / len(component_health)
        overall_status = self._determine_overall_status(overall_score, component_health)
        
        # Get active alerts
        active_alerts = await self._get_active_alerts()
        
        # Get performance metrics
        performance_metrics = await self._get_performance_metrics()
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(component_health, performance_metrics)
        
        report = SystemHealthReport(
            overall_status=overall_status,
            overall_score=overall_score,
            component_health=component_health,
            active_alerts=active_alerts,
            performance_metrics=performance_metrics,
            recommendations=recommendations,
            timestamp=timestamp
        )
        
        # Store in history
        self.health_history.append(report)
        if len(self.health_history) > 100:
            self.health_history.pop(0)
        
        return report
    
    async def validate_monitoring_systems(self) -> Dict[str, Any]:
        """Validate all monitoring systems are functioning."""
        validation_results = {}
        
        # Validate baseline metrics
        try:
            baseline_report = baseline_analyzer.generate_baseline_report()
            validation_results["baseline_metrics"] = {
                "status": "healthy",
                "metrics_collected": baseline_report["system_summary"]["metrics_collected"],
                "collection_running": baseline_report["system_summary"]["collection_running"]
            }
        except Exception as e:
            validation_results["baseline_metrics"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Validate hook manager
        try:
            hook_metrics = hook_manager.get_system_metrics()
            validation_results["hook_manager"] = {
                "status": "healthy" if hook_metrics["hook_manager"]["running"] else "stopped",
                "websocket_clients": hook_metrics["event_stream"]["websocket_clients"],
                "tracked_agents": hook_metrics["agent_monitor"]["tracked_agents"]
            }
        except Exception as e:
            validation_results["hook_manager"] = {
                "status": "error", 
                "error": str(e)
            }
        
        # Validate performance monitoring
        try:
            perf_summary = self.performance_monitor.get_monitoring_summary()
            validation_results["performance_monitoring"] = {
                "status": "healthy" if perf_summary["monitoring_active"] else "stopped",
                "metrics_tracked": perf_summary["metric_types_tracked"],
                "active_alerts": perf_summary["active_alerts"]
            }
        except Exception as e:
            validation_results["performance_monitoring"] = {
                "status": "error",
                "error": str(e)
            }
        
        return validation_results
    
    async def _collect_component_health(self) -> List[ComponentHealth]:
        """Collect health status for all system components."""
        components = []
        now = datetime.now()
        
        # Baseline metrics health
        try:
            baseline_report = baseline_analyzer.generate_baseline_report()
            opportunities = baseline_report["performance_opportunities"]
            
            score = 0.8 if opportunities["overall_health"] == "good" else 0.4
            status = HealthStatus.HEALTHY if score > 0.7 else HealthStatus.WARNING
            
            components.append(ComponentHealth(
                component_name="baseline_metrics",
                status=status,
                score=score,
                message=f"Collected {baseline_report['system_summary']['metrics_collected']} metrics",
                metrics=baseline_report["system_summary"]["key_metrics"],
                last_check=now
            ))
        except Exception as e:
            components.append(ComponentHealth(
                component_name="baseline_metrics",
                status=HealthStatus.CRITICAL,
                score=0.0,
                message=f"Failed to collect baseline metrics: {str(e)}",
                metrics={},
                last_check=now
            ))
        
        # Hook manager health
        try:
            hook_metrics = hook_manager.get_system_metrics()
            
            score = 0.9 if hook_metrics["hook_manager"]["running"] else 0.0
            status = HealthStatus.HEALTHY if score > 0.7 else HealthStatus.CRITICAL
            
            components.append(ComponentHealth(
                component_name="hook_manager",
                status=status,
                score=score,
                message=f"Running with {hook_metrics['event_stream']['websocket_clients']} clients",
                metrics=hook_metrics,
                last_check=now
            ))
        except Exception as e:
            components.append(ComponentHealth(
                component_name="hook_manager",
                status=HealthStatus.CRITICAL,
                score=0.0,
                message=f"Hook manager error: {str(e)}",
                metrics={},
                last_check=now
            ))
        
        # Performance monitoring health
        try:
            perf_summary = self.performance_monitor.get_monitoring_summary()
            
            score = 0.8 if perf_summary["monitoring_active"] else 0.0
            status = HealthStatus.HEALTHY if score > 0.7 else HealthStatus.CRITICAL
            
            components.append(ComponentHealth(
                component_name="performance_monitoring",
                status=status,
                score=score,
                message=f"Tracking {perf_summary['metric_types_tracked']} metric types",
                metrics=perf_summary,
                last_check=now
            ))
        except Exception as e:
            components.append(ComponentHealth(
                component_name="performance_monitoring",
                status=HealthStatus.CRITICAL,
                score=0.0,
                message=f"Performance monitoring error: {str(e)}",
                metrics={},
                last_check=now
            ))
        
        # System resources health
        try:
            system_stats = metrics_collector.get_metric_stats("cpu_usage_percent")
            memory_stats = metrics_collector.get_metric_stats("memory_usage_mb")
            
            if "error" not in system_stats and "error" not in memory_stats:
                cpu_score = max(0, 1.0 - (system_stats["latest"] / 100))
                memory_score = max(0, 1.0 - (memory_stats["latest"] / 32000))  # 32GB baseline
                score = (cpu_score + memory_score) / 2
                
                status = HealthStatus.HEALTHY if score > 0.7 else HealthStatus.WARNING if score > 0.4 else HealthStatus.CRITICAL
                
                components.append(ComponentHealth(
                    component_name="system_resources",
                    status=status,
                    score=score,
                    message=f"CPU: {system_stats['latest']:.1f}%, Memory: {memory_stats['latest']:.0f}MB",
                    metrics={"cpu": system_stats, "memory": memory_stats},
                    last_check=now
                ))
            else:
                components.append(ComponentHealth(
                    component_name="system_resources", 
                    status=HealthStatus.UNKNOWN,
                    score=0.5,
                    message="Insufficient metrics data",
                    metrics={},
                    last_check=now
                ))
        except Exception as e:
            components.append(ComponentHealth(
                component_name="system_resources",
                status=HealthStatus.CRITICAL,
                score=0.0,
                message=f"System resources error: {str(e)}",
                metrics={},
                last_check=now
            ))
        
        return components
    
    def _determine_overall_status(self, overall_score: float, components: List[ComponentHealth]) -> HealthStatus:
        """Determine overall system health status."""
        # Check for any critical components
        critical_components = [c for c in components if c.status == HealthStatus.CRITICAL]
        if critical_components:
            return HealthStatus.CRITICAL
        
        # Check overall score
        if overall_score >= 0.8:
            return HealthStatus.HEALTHY
        elif overall_score >= 0.6:
            return HealthStatus.WARNING
        else:
            return HealthStatus.CRITICAL
    
    async def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active system alerts."""
        alerts = []
        
        try:
            # Get performance monitoring alerts
            system_health = await self.performance_monitor.get_system_health()
            alerts.extend([alert.to_dict() for alert in system_health.active_alerts])
        except Exception as e:
            self.logger.error(f"Failed to get performance alerts: {e}")
        
        return alerts
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        try:
            system_health = await self.performance_monitor.get_system_health()
            # Convert PerformanceMetricType keys to strings
            return {k.value if hasattr(k, 'value') else str(k): v for k, v in system_health.recent_metrics.items()}
        except Exception as e:
            self.logger.error(f"Failed to get performance metrics: {e}")
            return {}
    
    async def _generate_recommendations(self, components: List[ComponentHealth], metrics: Dict[str, Any]) -> List[str]:
        """Generate health improvement recommendations."""
        recommendations = []
        
        # Component-based recommendations
        for component in components:
            if component.status == HealthStatus.CRITICAL:
                recommendations.append(f"CRITICAL: Resolve {component.component_name} issues - {component.message}")
            elif component.status == HealthStatus.WARNING:
                recommendations.append(f"WARNING: Monitor {component.component_name} - {component.message}")
        
        # Performance-based recommendations
        try:
            perf_recommendations = await self.performance_monitor.optimize_performance()
            for rec in perf_recommendations[:3]:  # Top 3 recommendations
                recommendations.append(f"OPTIMIZATION: {rec.description}")
        except Exception as e:
            self.logger.error(f"Failed to get performance recommendations: {e}")
        
        return recommendations
    
    async def _health_validation_loop(self):
        """Background health validation loop."""
        while self.running:
            try:
                # Perform health check
                health_report = await self.get_system_health()
                
                # Log critical issues
                if health_report.overall_status == HealthStatus.CRITICAL:
                    self.logger.critical(f"System health critical: {health_report.overall_score:.2f}")
                
                # Store health report
                await self._store_health_report(health_report)
                
                await asyncio.sleep(self.validation_interval)
            except Exception as e:
                self.logger.error(f"Health validation loop error: {e}")
                await asyncio.sleep(self.validation_interval)
    
    async def _store_health_report(self, report: SystemHealthReport):
        """Store health report for historical analysis."""
        try:
            # Store in SQLite database
            db_path = "monitoring_health_validation.db"
            
            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS health_reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        overall_status TEXT NOT NULL,
                        overall_score REAL NOT NULL,
                        component_count INTEGER NOT NULL,
                        alert_count INTEGER NOT NULL,
                        report_data TEXT NOT NULL
                    )
                ''')
                
                conn.execute('''
                    INSERT INTO health_reports 
                    (timestamp, overall_status, overall_score, component_count, alert_count, report_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    report.timestamp.isoformat(),
                    report.overall_status.value,
                    report.overall_score,
                    len(report.component_health),
                    len(report.active_alerts),
                    json.dumps(report.to_dict())
                ))
                
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to store health report: {e}")


# Global instance
health_validator = MonitoringHealthValidator()


# API endpoints for health validation
async def get_health_status() -> Dict[str, Any]:
    """Get current system health status."""
    health_report = await health_validator.get_system_health()
    return health_report.to_dict()


async def validate_monitoring() -> Dict[str, Any]:
    """Validate monitoring systems."""
    return await health_validator.validate_monitoring_systems()


async def get_health_history(hours: int = 24) -> List[Dict[str, Any]]:
    """Get health history for specified hours."""
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    recent_reports = [
        report.to_dict() for report in health_validator.health_history
        if report.timestamp >= cutoff_time
    ]
    
    return recent_reports


if __name__ == "__main__":
    async def main():
        print("Foundation Epic Phase 1: System Monitoring and Health Validation")
        print("=" * 60)
        
        # Start monitoring
        await health_validator.start_monitoring()
        
        # Wait for metrics collection
        print("Collecting initial metrics...")
        await asyncio.sleep(35)
        
        # Get health status
        print("\nSystem Health Status:")
        health_status = await get_health_status()
        print(json.dumps(health_status, indent=2))
        
        # Validate monitoring systems
        print("\nMonitoring Systems Validation:")
        validation_results = await validate_monitoring()
        print(json.dumps(validation_results, indent=2))
        
        # Get baseline report
        print("\nBaseline Performance Report:")
        baseline_report = baseline_analyzer.generate_baseline_report()
        print(f"Overall Health: {baseline_report['performance_opportunities']['overall_health']}")
        print(f"Opportunities: {baseline_report['performance_opportunities']['opportunities_count']}")
        
        # Stop monitoring
        await health_validator.stop_monitoring()
        
        print("\nFoundation Epic Phase 1 validation complete!")
    
    asyncio.run(main())