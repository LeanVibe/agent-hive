"""
Production-Ready Monitoring Framework Integration.

Integrates all monitoring components into a unified system with:
- Business metrics monitoring
- Proactive alerting with anomaly detection  
- Distributed tracing for end-to-end visibility
- Health checks and system validation
- API endpoints for monitoring dashboards
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import json
import threading
from collections import defaultdict
import psutil

from business_metrics_monitor import BusinessMetricsMonitor, BusinessMetric, BusinessMetricType
from proactive_alerting_system import ProactiveAlertingSystem, AlertSeverity, AlertCategory
from distributed_tracing_system import DistributedTracingSystem, WorkflowType
from monitoring_core import SystemMonitor
from monitoring_alerts import AlertManager


@dataclass
class MonitoringSystemHealth:
    """Overall monitoring system health status."""
    status: str  # "healthy", "degraded", "critical"
    timestamp: datetime
    business_metrics_status: str
    alerting_status: str
    tracing_status: str
    system_metrics_status: str
    active_alerts_count: int
    active_traces_count: int
    system_health_score: float
    recommendations: List[str]


class MonitoringIntegrationFramework:
    """Unified production-ready monitoring framework."""
    
    def __init__(self, service_name: str = "agent-hive-monitoring"):
        self.logger = logging.getLogger(__name__)
        self.service_name = service_name
        
        # Initialize monitoring components
        self.business_metrics = BusinessMetricsMonitor(enable_tracing=True)
        self.system_monitor = SystemMonitor()
        self.alert_manager = AlertManager()
        
        # Initialize distributed tracing
        self.tracing_system = DistributedTracingSystem(
            service_name=service_name,
            enable_console_export=False
        )
        
        # Initialize proactive alerting with business metrics integration
        self.proactive_alerting = ProactiveAlertingSystem(self.business_metrics)
        
        # Health monitoring
        self.health_checks: Dict[str, bool] = {
            "business_metrics": False,
            "system_monitor": False,
            "alert_manager": False,
            "tracing_system": False,
            "proactive_alerting": False
        }
        
        # Performance tracking
        self.start_time = datetime.now()
        self.metrics_processed = 0
        self.alerts_generated = 0
        self.traces_completed = 0
        
        # Configuration
        self.monitoring_interval = 30  # seconds
        self.health_check_interval = 60  # seconds
        
        # Thread management
        self.running = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.health_check_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        self.logger.info("MonitoringIntegrationFramework initialized")
    
    async def initialize(self) -> None:
        """Initialize all monitoring components."""
        try:
            # Start business metrics monitoring
            self.business_metrics.start_monitoring()
            self.health_checks["business_metrics"] = True
            self.logger.info("Business metrics monitoring started")
            
            # Start system monitoring
            await self.system_monitor.start_monitoring()
            self.health_checks["system_monitor"] = True
            self.logger.info("System monitoring started")
            
            # Alert manager is always ready
            self.health_checks["alert_manager"] = True
            self.logger.info("Alert manager ready")
            
            # Tracing system is initialized during construction
            self.health_checks["tracing_system"] = True
            self.logger.info("Distributed tracing ready")
            
            # Start proactive alerting
            self.proactive_alerting.start_monitoring()
            self.health_checks["proactive_alerting"] = True
            self.logger.info("Proactive alerting started")
            
            # Start integrated monitoring loops
            self.running = True
            self.monitoring_thread = threading.Thread(target=self._integrated_monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
            self.health_check_thread.start()
            
            self.logger.info("Monitoring integration framework fully initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring framework: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Gracefully shutdown all monitoring components."""
        self.logger.info("Shutting down monitoring integration framework")
        
        self.running = False
        
        # Stop monitoring threads
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5.0)
        
        # Stop individual components
        self.business_metrics.stop_monitoring()
        await self.system_monitor.stop_monitoring()
        self.proactive_alerting.stop_monitoring()
        self.tracing_system.shutdown()
        
        self.logger.info("Monitoring integration framework shutdown complete")
    
    def _integrated_monitoring_loop(self) -> None:
        """Main integrated monitoring loop."""
        while self.running:
            try:
                # Collect system metrics
                system_metrics = self._collect_system_metrics()
                
                # Process metrics through all systems
                self._process_metrics_pipeline(system_metrics)
                
                # Generate integrated insights
                self._generate_integrated_insights()
                
                # Update performance counters
                with self.lock:
                    self.metrics_processed += 1
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in integrated monitoring loop: {e}")
                time.sleep(5)
    
    def _health_check_loop(self) -> None:
        """Health check monitoring loop."""
        while self.running:
            try:
                self._perform_health_checks()
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                time.sleep(10)
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive system metrics."""
        try:
            # Get system resource metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get process-specific metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # Get business metrics
            business_dashboard = self.business_metrics.get_real_time_dashboard()
            
            # Get alerting metrics
            alert_summary = self.alert_manager.get_alert_summary()
            
            # Get tracing metrics
            trace_overview = self.tracing_system.get_system_trace_overview()
            
            return {
                # System metrics
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available": memory.available,
                "disk_percent": disk.percent,
                "disk_free": disk.free,
                
                # Process metrics
                "process_memory_rss": process_memory.rss,
                "process_memory_vms": process_memory.vms,
                
                # Business metrics
                "active_tasks": business_dashboard.get("active_tasks", 0),
                "active_conflicts": business_dashboard.get("active_conflicts", 0),
                "total_hourly_throughput": business_dashboard.get("total_hourly_throughput", 0),
                "system_health": business_dashboard.get("system_health", "unknown"),
                
                # Alerting metrics
                "active_alerts_total": alert_summary.get("active_alerts_total", 0),
                "critical_alerts": alert_summary.get("active_by_level", {}).get("critical", 0),
                "warning_alerts": alert_summary.get("active_by_level", {}).get("warning", 0),
                
                # Tracing metrics
                "active_workflows": trace_overview.get("active_workflows", 0),
                "active_agents": trace_overview.get("active_agents", 0),
                "total_active_spans": trace_overview.get("total_active_spans", 0),
                "workflow_success_rate": trace_overview.get("workflow_success_rate", 0.0),
                
                # Framework metrics
                "monitoring_uptime": (datetime.now() - self.start_time).total_seconds(),
                "metrics_processed": self.metrics_processed,
                "alerts_generated": self.alerts_generated,
                "traces_completed": self.traces_completed
            }
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            return {}
    
    def _process_metrics_pipeline(self, metrics: Dict[str, Any]) -> None:
        """Process metrics through the integrated pipeline."""
        try:
            # 1. Send metrics to proactive alerting system
            self.proactive_alerting.process_metrics(metrics)
            
            # 2. Check traditional alert thresholds
            traditional_alerts = self.alert_manager.check_metrics({
                k: v for k, v in metrics.items() 
                if isinstance(v, (int, float))
            })
            
            if traditional_alerts:
                with self.lock:
                    self.alerts_generated += len(traditional_alerts)
            
            # 3. Record business metrics if applicable
            current_time = datetime.now()
            
            # Task throughput
            if "total_hourly_throughput" in metrics:
                self.business_metrics.record_business_metric(BusinessMetric(
                    metric_type=BusinessMetricType.TASK_THROUGHPUT,
                    value=float(metrics["total_hourly_throughput"]),
                    timestamp=current_time,
                    agent_id="system",
                    collaboration_context={"source": "integrated_monitoring"}
                ))
            
            # System utilization
            if "cpu_percent" in metrics:
                utilization = 1.0 - (metrics["cpu_percent"] / 100.0)  # Inverse for "higher is better"
                self.business_metrics.record_business_metric(BusinessMetric(
                    metric_type=BusinessMetricType.AGENT_UTILIZATION,
                    value=utilization,
                    timestamp=current_time,
                    agent_id="system",
                    collaboration_context={"cpu_percent": metrics["cpu_percent"]}
                ))
            
        except Exception as e:
            self.logger.error(f"Error in metrics processing pipeline: {e}")
    
    def _generate_integrated_insights(self) -> None:
        """Generate insights from integrated monitoring data."""
        try:
            # Get data from all systems
            predictive_alerts = self.proactive_alerting.get_active_predictive_alerts()
            system_health_data = self.proactive_alerting.get_system_health_dashboard()
            
            # Generate cross-system insights
            insights = []
            
            # Alert correlation analysis
            critical_alerts = [a for a in predictive_alerts if a.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]]
            if len(critical_alerts) > 3:
                insights.append("Multiple critical alerts detected - potential system-wide issue")
            
            # Performance trend analysis
            health_score = system_health_data.get("system_health_score", 0.5)
            if health_score < 0.4:
                insights.append("System health degrading - investigate resource constraints")
            
            # Workflow efficiency analysis
            workflow_success_rate = system_health_data.get("next_predictions", [])
            low_success_predictions = [p for p in workflow_success_rate if p.get("confidence", 0) < 0.5]
            if len(low_success_predictions) > 2:
                insights.append("Workflow predictions showing low confidence - review coordination patterns")
            
            # Log insights
            for insight in insights:
                self.logger.info(f"Monitoring Insight: {insight}")
                
        except Exception as e:
            self.logger.error(f"Error generating integrated insights: {e}")
    
    def _perform_health_checks(self) -> None:
        """Perform health checks on all monitoring components."""
        try:
            # Check business metrics monitoring
            business_dashboard = self.business_metrics.get_real_time_dashboard()
            self.health_checks["business_metrics"] = business_dashboard.get("system_health") != "error"
            
            # Check system monitoring
            try:
                system_metrics = self.system_monitor.get_latest_metrics()
                self.health_checks["system_monitor"] = system_metrics is not None
            except:
                self.health_checks["system_monitor"] = False
            
            # Check alert manager
            try:
                alert_summary = self.alert_manager.get_alert_summary()
                self.health_checks["alert_manager"] = alert_summary is not None
            except:
                self.health_checks["alert_manager"] = False
            
            # Check tracing system
            try:
                trace_overview = self.tracing_system.get_system_trace_overview()
                self.health_checks["tracing_system"] = trace_overview.get("tracing_enabled", False)
            except:
                self.health_checks["tracing_system"] = False
            
            # Check proactive alerting
            try:
                health_dashboard = self.proactive_alerting.get_system_health_dashboard()
                self.health_checks["proactive_alerting"] = health_dashboard is not None
            except:
                self.health_checks["proactive_alerting"] = False
            
            # Log health status
            healthy_components = sum(self.health_checks.values())
            total_components = len(self.health_checks)
            
            if healthy_components == total_components:
                self.logger.debug("All monitoring components healthy")
            else:
                unhealthy = [name for name, status in self.health_checks.items() if not status]
                self.logger.warning(f"Unhealthy monitoring components: {unhealthy}")
                
        except Exception as e:
            self.logger.error(f"Error performing health checks: {e}")
    
    def get_monitoring_system_health(self) -> MonitoringSystemHealth:
        """Get comprehensive monitoring system health."""
        current_time = datetime.now()
        
        # Determine overall status
        healthy_components = sum(self.health_checks.values())
        total_components = len(self.health_checks)
        health_ratio = healthy_components / total_components
        
        if health_ratio >= 1.0:
            status = "healthy"
        elif health_ratio >= 0.8:
            status = "degraded"
        else:
            status = "critical"
        
        # Get component statuses
        component_statuses = {
            "business_metrics_status": "healthy" if self.health_checks["business_metrics"] else "unhealthy",
            "alerting_status": "healthy" if self.health_checks["alert_manager"] else "unhealthy",
            "tracing_status": "healthy" if self.health_checks["tracing_system"] else "unhealthy",
            "system_metrics_status": "healthy" if self.health_checks["system_monitor"] else "unhealthy"
        }
        
        # Get counts
        try:
            alert_summary = self.alert_manager.get_alert_summary()
            active_alerts_count = alert_summary.get("active_alerts_total", 0)
        except:
            active_alerts_count = 0
        
        try:
            trace_overview = self.tracing_system.get_system_trace_overview()
            active_traces_count = trace_overview.get("active_workflows", 0)
        except:
            active_traces_count = 0
        
        # Calculate system health score
        try:
            health_dashboard = self.proactive_alerting.get_system_health_dashboard()
            system_health_score = health_dashboard.get("system_health_score", 0.5)
        except:
            system_health_score = health_ratio  # Fallback to component health ratio
        
        # Generate recommendations
        recommendations = []
        if not self.health_checks["business_metrics"]:
            recommendations.append("Restart business metrics monitoring")
        if not self.health_checks["system_monitor"]:
            recommendations.append("Check system monitor connectivity")
        if not self.health_checks["tracing_system"]:
            recommendations.append("Verify Jaeger/OTLP exporter configuration")
        if active_alerts_count > 10:
            recommendations.append("High alert volume - investigate root causes")
        if system_health_score < 0.5:
            recommendations.append("System health critically low - immediate attention required")
        
        return MonitoringSystemHealth(
            status=status,
            timestamp=current_time,
            active_alerts_count=active_alerts_count,
            active_traces_count=active_traces_count,
            system_health_score=system_health_score,
            recommendations=recommendations,
            **component_statuses
        )
    
    def get_comprehensive_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive monitoring dashboard data."""
        try:
            # Get data from all systems
            business_dashboard = self.business_metrics.get_real_time_dashboard()
            alert_summary = self.alert_manager.get_alert_summary()
            trace_overview = self.tracing_system.get_system_trace_overview()
            health_dashboard = self.proactive_alerting.get_system_health_dashboard()
            system_health = self.get_monitoring_system_health()
            
            # Get recent metrics
            recent_metrics = self._collect_system_metrics()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "monitoring_framework": {
                    "status": system_health.status,
                    "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                    "metrics_processed": self.metrics_processed,
                    "alerts_generated": self.alerts_generated,
                    "traces_completed": self.traces_completed,
                    "component_health": self.health_checks
                },
                "business_metrics": business_dashboard,
                "alerts": {
                    "summary": alert_summary,
                    "predictive_alerts": len(self.proactive_alerting.get_active_predictive_alerts()),
                    "critical_conditions": health_dashboard.get("critical_conditions_active", 0)
                },
                "distributed_tracing": trace_overview,
                "system_health": {
                    "overall_score": system_health.system_health_score,
                    "status": system_health.status,
                    "recommendations": system_health.recommendations
                },
                "system_metrics": {
                    "cpu_percent": recent_metrics.get("cpu_percent"),
                    "memory_percent": recent_metrics.get("memory_percent"),
                    "disk_percent": recent_metrics.get("disk_percent"),
                    "active_tasks": recent_metrics.get("active_tasks"),
                    "throughput": recent_metrics.get("total_hourly_throughput")
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error generating comprehensive dashboard: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "monitoring_framework": {"status": "error"}
            }
    
    # API methods for external integration
    
    def start_workflow_monitoring(self, workflow_id: str, workflow_type: str,
                                participating_agents: List[str]) -> str:
        """Start monitoring a new workflow."""
        workflow_type_enum = WorkflowType(workflow_type)
        return self.tracing_system.start_workflow_trace(
            workflow_id, workflow_type_enum, participating_agents
        )
    
    def complete_workflow_monitoring(self, workflow_id: str, status: str = "completed") -> None:
        """Complete workflow monitoring."""
        self.tracing_system.complete_workflow_trace(workflow_id, status)
        with self.lock:
            self.traces_completed += 1
    
    def record_agent_task(self, agent_id: str, task_id: str, task_type: str,
                         success: bool = True, duration: Optional[float] = None) -> None:
        """Record agent task completion."""
        if duration is not None:
            # If we have duration, simulate start/complete cycle
            start_time = datetime.now() - timedelta(seconds=duration)
            self.business_metrics.start_task(agent_id, task_id, task_type)
            self.business_metrics.complete_task(task_id, success)
        else:
            # Just record completion
            self.business_metrics.complete_task(task_id, success)
    
    def record_conflict_resolution(self, conflict_id: str, participating_agents: List[str],
                                 resolution_time: float, success: bool = True) -> None:
        """Record conflict resolution."""
        self.business_metrics.start_conflict_resolution(
            conflict_id, participating_agents, "coordination_conflict"
        )
        self.business_metrics.resolve_conflict(
            conflict_id, "automated_resolution", success
        )
    
    def get_agent_performance(self, agent_id: str) -> Dict[str, Any]:
        """Get agent performance metrics."""
        throughput_report = self.business_metrics.get_agent_throughput_report(agent_id)
        trace_summary = self.tracing_system.get_agent_trace_summary(agent_id)
        
        return {
            "agent_id": agent_id,
            "throughput": throughput_report,
            "tracing": trace_summary,
            "timestamp": datetime.now().isoformat()
        }
    
    def validate_integration(self) -> Dict[str, Any]:
        """Validate the complete monitoring integration."""
        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "validation_status": "passed",
            "checks": {},
            "recommendations": []
        }
        
        try:
            # Test business metrics
            test_metric = BusinessMetric(
                metric_type=BusinessMetricType.TASK_THROUGHPUT,
                value=1.0,
                timestamp=datetime.now(),
                agent_id="test_agent"
            )
            self.business_metrics.record_business_metric(test_metric)
            validation_results["checks"]["business_metrics"] = "passed"
            
        except Exception as e:
            validation_results["checks"]["business_metrics"] = f"failed: {e}"
            validation_results["validation_status"] = "failed"
        
        try:
            # Test alerting
            test_metrics = {"test_metric": 99.0}
            alerts = self.alert_manager.check_metrics(test_metrics)
            validation_results["checks"]["alerting"] = "passed"
            
        except Exception as e:
            validation_results["checks"]["alerting"] = f"failed: {e}"
            validation_results["validation_status"] = "failed"
        
        try:
            # Test tracing
            trace_id = self.tracing_system.start_workflow_trace(
                "test_workflow", WorkflowType.TASK_EXECUTION, ["test_agent"]
            )
            self.tracing_system.complete_workflow_trace("test_workflow", "completed")
            validation_results["checks"]["tracing"] = "passed"
            
        except Exception as e:
            validation_results["checks"]["tracing"] = f"failed: {e}"
            validation_results["validation_status"] = "failed"
        
        try:
            # Test health monitoring
            health = self.get_monitoring_system_health()
            validation_results["checks"]["health_monitoring"] = "passed"
            validation_results["system_health"] = asdict(health)
            
        except Exception as e:
            validation_results["checks"]["health_monitoring"] = f"failed: {e}"
            validation_results["validation_status"] = "failed"
        
        # Add recommendations based on validation
        if validation_results["validation_status"] == "failed":
            validation_results["recommendations"].append("Fix failed validation checks before production deployment")
        
        if any("failed" in result for result in validation_results["checks"].values()):
            validation_results["recommendations"].append("Review component configurations and dependencies")
        
        return validation_results