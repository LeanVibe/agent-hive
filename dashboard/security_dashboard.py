#!/usr/bin/env python3
"""
Security Dashboard for Real-Time Monitoring

Comprehensive security dashboard for LeanVibe Agent Hive with:
- Real-time security metrics and visualizations
- Interactive incident management interface
- Live threat monitoring and alerting
- Compliance reporting and analytics
- Integration with all security monitoring components
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

from security.audit_logger import (
    SecurityAuditLogger, SecurityEvent, SecurityEventType, 
    SecuritySeverity, audit_logger
)
from security.security_monitor import (
    SecurityMonitor, SecurityAnomaly, SecurityIncident, 
    ThreatLevel, IncidentStatus, security_monitor
)


logger = logging.getLogger(__name__)


@dataclass
class DashboardMetrics:
    """Dashboard metrics snapshot."""
    timestamp: datetime
    
    # Event metrics
    total_events: int
    events_per_hour: int
    events_by_severity: Dict[str, int]
    events_by_type: Dict[str, int]
    
    # Security metrics
    active_anomalies: int
    active_incidents: int
    threat_level: str
    security_score: float
    
    # Performance metrics
    avg_processing_time_ms: float
    queue_size: int
    error_rate: float
    
    # User metrics
    active_users: int
    suspicious_users: List[str]
    
    # System health
    system_status: str
    compliance_status: str


@dataclass
class SecurityAlert:
    """Security alert for dashboard."""
    alert_id: str
    timestamp: datetime
    severity: SecuritySeverity
    title: str
    description: str
    source: str
    affected_entities: List[str]
    requires_action: bool
    auto_resolved: bool = False


class SecurityDashboard:
    """
    Real-time security dashboard with comprehensive monitoring.
    
    Features:
    - Real-time metrics aggregation and display
    - Interactive incident management
    - Live threat monitoring with alerts
    - Historical analytics and reporting
    - Compliance status tracking
    - Performance monitoring
    """
    
    def __init__(self, 
                 audit_logger: SecurityAuditLogger,
                 security_monitor: SecurityMonitor,
                 config: Optional[Dict[str, Any]] = None):
        """Initialize security dashboard."""
        self.audit_logger = audit_logger
        self.security_monitor = security_monitor
        self.config = config or self._get_default_config()
        
        # Dashboard state
        self.current_metrics = None
        self.historical_metrics = []
        self.active_alerts = {}
        self.dashboard_sessions = {}
        
        # Metrics aggregation
        self.metrics_history = defaultdict(list)
        self.last_metrics_update = datetime.utcnow()
        
        # Performance tracking
        self.dashboard_performance = {
            "requests_served": 0,
            "avg_response_time_ms": 0.0,
            "error_count": 0
        }
        
        # Start background tasks
        self._metrics_task = None
        self._start_metrics_collection()
        
        logger.info("SecurityDashboard initialized with real-time monitoring")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default dashboard configuration."""
        return {
            "update_interval_seconds": 30,
            "metrics_retention_hours": 24,
            "alert_retention_hours": 72,
            "max_historical_points": 1000,
            "real_time_updates": True,
            "auto_refresh": True,
            "performance_monitoring": True
        }
    
    def _start_metrics_collection(self):
        """Start background metrics collection."""
        async def collect_metrics():
            while True:
                try:
                    await self._update_metrics()
                    await asyncio.sleep(self.config.get("update_interval_seconds", 30))
                except Exception as e:
                    logger.error(f"Metrics collection error: {e}")
                    await asyncio.sleep(60)  # Wait longer on error
        
        try:
            loop = asyncio.get_running_loop()
            self._metrics_task = loop.create_task(collect_metrics())
            logger.info("Dashboard metrics collection started")
        except RuntimeError:
            logger.info("No event loop running, metrics will be collected on demand")
    
    async def _update_metrics(self):
        """Update dashboard metrics."""
        try:
            current_time = datetime.utcnow()
            
            # Get audit log statistics
            audit_stats = await self.audit_logger.get_statistics(hours=1)
            
            # Get monitoring status
            monitor_status = self.security_monitor.get_monitoring_status()
            
            # Get recent events for rate calculation
            recent_events = self.audit_logger.get_recent_events(1000)
            hour_ago = current_time - timedelta(hours=1)
            events_last_hour = len([e for e in recent_events if e.timestamp >= hour_ago])
            
            # Calculate security metrics
            active_anomalies = len([
                a for a in self.security_monitor.detected_anomalies.values()
                if a.detected_at >= current_time - timedelta(hours=24)
            ])
            
            active_incidents = len([
                i for i in self.security_monitor.active_incidents.values()
                if i.status not in [IncidentStatus.RESOLVED, IncidentStatus.FALSE_POSITIVE]
            ])
            
            # Get suspicious users
            suspicious_users = self._identify_suspicious_users(recent_events)
            
            # Calculate error rate
            total_events = monitor_status["performance"]["events_processed"]
            processing_errors = monitor_status["performance"].get("error_count", 0)
            error_rate = (processing_errors / max(total_events, 1)) * 100
            
            # Create metrics snapshot
            metrics = DashboardMetrics(
                timestamp=current_time,
                total_events=audit_stats.total_events,
                events_per_hour=events_last_hour,
                events_by_severity=audit_stats.events_by_severity,
                events_by_type=audit_stats.events_by_type,
                active_anomalies=active_anomalies,
                active_incidents=active_incidents,
                threat_level=monitor_status["current_threats"]["threat_level"],
                security_score=audit_stats.security_score,
                avg_processing_time_ms=monitor_status["performance"]["avg_processing_time_ms"],
                queue_size=monitor_status["performance"]["queue_size"],
                error_rate=error_rate,
                active_users=len(audit_stats.top_users),
                suspicious_users=suspicious_users,
                system_status=self._calculate_system_status(audit_stats, monitor_status),
                compliance_status=audit_stats.compliance_status
            )
            
            # Update dashboard state
            self.current_metrics = metrics
            self.historical_metrics.append(metrics)
            
            # Maintain history size
            max_history = self.config.get("max_historical_points", 1000)
            if len(self.historical_metrics) > max_history:
                self.historical_metrics = self.historical_metrics[-max_history:]
            
            # Update time-series data
            self._update_time_series_data(metrics)
            
            # Check for alert conditions
            await self._check_alert_conditions(metrics)
            
            self.last_metrics_update = current_time
            
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
    
    def _identify_suspicious_users(self, recent_events: List[SecurityEvent]) -> List[str]:
        """Identify users with suspicious activity patterns."""
        user_activity = defaultdict(lambda: {
            "events": 0,
            "violations": 0,
            "failed_auths": 0,
            "rate_limits": 0
        })
        
        for event in recent_events:
            if event.user_id:
                user_activity[event.user_id]["events"] += 1
                
                if event.event_type in [
                    SecurityEventType.SECURITY_COMMAND_BLOCKED,
                    SecurityEventType.SECURITY_INJECTION_ATTEMPT,
                    SecurityEventType.SECURITY_XSS_ATTEMPT
                ]:
                    user_activity[event.user_id]["violations"] += 1
                
                if event.event_type in [
                    SecurityEventType.AUTH_LOGIN_FAILURE,
                    SecurityEventType.AUTHZ_PERMISSION_DENIED
                ]:
                    user_activity[event.user_id]["failed_auths"] += 1
                
                if event.event_type == SecurityEventType.RATE_LIMIT_EXCEEDED:
                    user_activity[event.user_id]["rate_limits"] += 1
        
        # Identify suspicious users based on thresholds
        suspicious = []
        for user_id, activity in user_activity.items():
            if (activity["violations"] >= 3 or 
                activity["failed_auths"] >= 5 or 
                activity["rate_limits"] >= 10):
                suspicious.append(user_id)
        
        return suspicious[:10]  # Limit to top 10
    
    def _calculate_system_status(self, audit_stats, monitor_status) -> str:
        """Calculate overall system security status."""
        critical_events = audit_stats.events_by_severity.get("critical", 0)
        high_events = audit_stats.events_by_severity.get("high", 0)
        active_incidents = monitor_status["current_threats"]["active_incidents"]
        
        if critical_events > 0 or active_incidents.get("critical", 0) > 0:
            return "CRITICAL"
        elif high_events > 5 or active_incidents.get("high", 0) > 0:
            return "WARNING"
        elif high_events > 0 or active_incidents.get("medium", 0) > 0:
            return "MONITORING"
        else:
            return "HEALTHY"
    
    def _update_time_series_data(self, metrics: DashboardMetrics):
        """Update time-series data for charting."""
        timestamp = metrics.timestamp.isoformat()
        
        # Store key metrics for time-series visualization
        self.metrics_history["timestamp"].append(timestamp)
        self.metrics_history["events_per_hour"].append(metrics.events_per_hour)
        self.metrics_history["security_score"].append(metrics.security_score)
        self.metrics_history["active_anomalies"].append(metrics.active_anomalies)
        self.metrics_history["active_incidents"].append(metrics.active_incidents)
        self.metrics_history["processing_time"].append(metrics.avg_processing_time_ms)
        
        # Maintain time-series size
        max_points = self.config.get("max_historical_points", 1000)
        for key in self.metrics_history:
            if len(self.metrics_history[key]) > max_points:
                self.metrics_history[key] = self.metrics_history[key][-max_points:]
    
    async def _check_alert_conditions(self, metrics: DashboardMetrics):
        """Check for alert conditions and create alerts."""
        alerts_created = []
        
        # High event rate alert
        if metrics.events_per_hour > 500:
            alert = SecurityAlert(
                alert_id=f"high_event_rate_{int(time.time())}",
                timestamp=metrics.timestamp,
                severity=SecuritySeverity.MEDIUM,
                title="High Event Rate Detected",
                description=f"Event rate: {metrics.events_per_hour} events/hour",
                source="dashboard",
                affected_entities=["system"],
                requires_action=True
            )
            alerts_created.append(alert)
        
        # Low security score alert
        if metrics.security_score < 70:
            alert = SecurityAlert(
                alert_id=f"low_security_score_{int(time.time())}",
                timestamp=metrics.timestamp,
                severity=SecuritySeverity.HIGH,
                title="Low Security Score",
                description=f"Security score: {metrics.security_score}%",
                source="dashboard",
                affected_entities=["system"],
                requires_action=True
            )
            alerts_created.append(alert)
        
        # High error rate alert
        if metrics.error_rate > 5.0:
            alert = SecurityAlert(
                alert_id=f"high_error_rate_{int(time.time())}",
                timestamp=metrics.timestamp,
                severity=SecuritySeverity.MEDIUM,
                title="High Processing Error Rate",
                description=f"Error rate: {metrics.error_rate:.1f}%",
                source="dashboard",
                affected_entities=["monitoring_system"],
                requires_action=True
            )
            alerts_created.append(alert)
        
        # Critical system status alert
        if metrics.system_status == "CRITICAL":
            alert = SecurityAlert(
                alert_id=f"critical_system_status_{int(time.time())}",
                timestamp=metrics.timestamp,
                severity=SecuritySeverity.CRITICAL,
                title="Critical System Status",
                description="System security status is critical",
                source="dashboard",
                affected_entities=["system"],
                requires_action=True
            )
            alerts_created.append(alert)
        
        # Store new alerts
        for alert in alerts_created:
            self.active_alerts[alert.alert_id] = alert
            
        # Clean up old alerts
        await self._cleanup_old_alerts()
    
    async def _cleanup_old_alerts(self):
        """Clean up old alerts based on retention policy."""
        cutoff_time = datetime.utcnow() - timedelta(
            hours=self.config.get("alert_retention_hours", 72)
        )
        
        expired_alerts = [
            alert_id for alert_id, alert in self.active_alerts.items()
            if alert.timestamp < cutoff_time
        ]
        
        for alert_id in expired_alerts:
            del self.active_alerts[alert_id]
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        try:
            # Ensure metrics are up to date
            if (not self.current_metrics or 
                datetime.utcnow() - self.last_metrics_update > 
                timedelta(seconds=self.config.get("update_interval_seconds", 30) * 2)):
                await self._update_metrics()
            
            # Get recent incidents
            recent_incidents = [
                self._incident_to_dict(incident)
                for incident in self.security_monitor.active_incidents.values()
                if incident.created_at >= datetime.utcnow() - timedelta(hours=24)
            ]
            
            # Get recent anomalies
            recent_anomalies = [
                self._anomaly_to_dict(anomaly)
                for anomaly in self.security_monitor.detected_anomalies.values()
                if anomaly.detected_at >= datetime.utcnow() - timedelta(hours=24)
            ]
            
            # Get active alerts
            active_alerts = [
                asdict(alert) for alert in self.active_alerts.values()
                if not alert.auto_resolved
            ]
            
            # Get time-series data for charts
            time_series_data = dict(self.metrics_history)
            
            dashboard_data = {
                "status": "active",
                "last_updated": datetime.utcnow().isoformat(),
                "current_metrics": asdict(self.current_metrics) if self.current_metrics else None,
                "recent_incidents": recent_incidents,
                "recent_anomalies": recent_anomalies,
                "active_alerts": active_alerts,
                "time_series": time_series_data,
                "system_health": {
                    "status": self.current_metrics.system_status if self.current_metrics else "UNKNOWN",
                    "threat_level": self.current_metrics.threat_level if self.current_metrics else "UNKNOWN",
                    "compliance_status": self.current_metrics.compliance_status if self.current_metrics else "UNKNOWN",
                    "security_score": self.current_metrics.security_score if self.current_metrics else 0
                },
                "performance": self.dashboard_performance,
                "configuration": {
                    "auto_refresh": self.config.get("auto_refresh", True),
                    "update_interval": self.config.get("update_interval_seconds", 30),
                    "real_time_updates": self.config.get("real_time_updates", True)
                }
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return {
                "status": "error",
                "error": str(e),
                "last_updated": datetime.utcnow().isoformat()
            }
    
    def _incident_to_dict(self, incident: SecurityIncident) -> Dict[str, Any]:
        """Convert incident to dictionary for API response."""
        return {
            "incident_id": incident.incident_id,
            "title": incident.title,
            "description": incident.description,
            "severity": incident.severity.value,
            "status": incident.status.value,
            "threat_level": incident.threat_level.value,
            "created_at": incident.created_at.isoformat(),
            "first_seen": incident.first_seen.isoformat(),
            "last_seen": incident.last_seen.isoformat(),
            "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
            "incident_type": incident.incident_type,
            "attack_vector": incident.attack_vector,
            "affected_systems": incident.affected_systems,
            "affected_users": incident.affected_users,
            "indicators_of_compromise": incident.indicators_of_compromise,
            "response_actions": incident.response_actions,
            "assigned_to": incident.assigned_to,
            "escalated": incident.escalated,
            "metadata": incident.metadata
        }
    
    def _anomaly_to_dict(self, anomaly: SecurityAnomaly) -> Dict[str, Any]:
        """Convert anomaly to dictionary for API response."""
        return {
            "anomaly_id": anomaly.anomaly_id,
            "anomaly_type": anomaly.anomaly_type.value,
            "severity": anomaly.severity.value,
            "confidence": anomaly.confidence,
            "detected_at": anomaly.detected_at.isoformat(),
            "description": anomaly.description,
            "affected_entities": anomaly.affected_entities,
            "detection_rules": anomaly.detection_rules,
            "threat_indicators": anomaly.threat_indicators,
            "risk_score": anomaly.risk_score,
            "auto_response_taken": anomaly.auto_response_taken,
            "response_actions": anomaly.response_actions,
            "requires_human_review": anomaly.requires_human_review,
            "metadata": anomaly.metadata
        }
    
    async def get_security_overview(self) -> Dict[str, Any]:
        """Get security overview summary."""
        try:
            if not self.current_metrics:
                await self._update_metrics()
            
            # Calculate trends
            trends = self._calculate_trends()
            
            overview = {
                "security_score": self.current_metrics.security_score,
                "threat_level": self.current_metrics.threat_level,
                "system_status": self.current_metrics.system_status,
                "compliance_status": self.current_metrics.compliance_status,
                "active_incidents": self.current_metrics.active_incidents,
                "active_anomalies": self.current_metrics.active_anomalies,
                "events_last_hour": self.current_metrics.events_per_hour,
                "suspicious_users": len(self.current_metrics.suspicious_users),
                "trends": trends,
                "last_updated": self.current_metrics.timestamp.isoformat()
            }
            
            return overview
            
        except Exception as e:
            logger.error(f"Failed to get security overview: {e}")
            return {"error": str(e)}
    
    def _calculate_trends(self) -> Dict[str, str]:
        """Calculate trends from historical data."""
        if len(self.historical_metrics) < 2:
            return {}
        
        current = self.historical_metrics[-1]
        previous = self.historical_metrics[-2]
        
        trends = {}
        
        # Security score trend
        if current.security_score > previous.security_score:
            trends["security_score"] = "improving"
        elif current.security_score < previous.security_score:
            trends["security_score"] = "declining"
        else:
            trends["security_score"] = "stable"
        
        # Event rate trend
        if current.events_per_hour > previous.events_per_hour * 1.2:
            trends["event_rate"] = "increasing"
        elif current.events_per_hour < previous.events_per_hour * 0.8:
            trends["event_rate"] = "decreasing"
        else:
            trends["event_rate"] = "stable"
        
        # Incident trend
        if current.active_incidents > previous.active_incidents:
            trends["incidents"] = "increasing"
        elif current.active_incidents < previous.active_incidents:
            trends["incidents"] = "decreasing"
        else:
            trends["incidents"] = "stable"
        
        return trends
    
    async def get_incident_details(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed incident information."""
        incident = self.security_monitor.active_incidents.get(incident_id)
        if not incident:
            return None
        
        # Get related events
        related_events = []
        if incident.related_events:
            recent_events = self.audit_logger.get_recent_events(5000)
            related_events = [
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "timestamp": event.timestamp.isoformat(),
                    "severity": event.severity.value,
                    "description": f"{event.action or ''} {event.resource or ''}".strip()
                }
                for event in recent_events
                if event.event_id in incident.related_events
            ]
        
        # Get related anomalies
        related_anomalies = []
        if incident.related_anomalies:
            related_anomalies = [
                self._anomaly_to_dict(anomaly)
                for anomaly_id, anomaly in self.security_monitor.detected_anomalies.items()
                if anomaly_id in incident.related_anomalies
            ]
        
        incident_details = self._incident_to_dict(incident)
        incident_details["related_events"] = related_events
        incident_details["related_anomalies"] = related_anomalies
        
        return incident_details
    
    async def update_incident_status(self, incident_id: str, status: str, 
                                   assigned_to: Optional[str] = None,
                                   notes: Optional[str] = None) -> bool:
        """Update incident status."""
        try:
            incident = self.security_monitor.active_incidents.get(incident_id)
            if not incident:
                return False
            
            # Update incident
            incident.status = IncidentStatus(status)
            if assigned_to:
                incident.assigned_to = assigned_to
            
            if status in ["resolved", "false_positive"]:
                incident.resolved_at = datetime.utcnow()
            
            if notes:
                incident.metadata["status_notes"] = notes
                incident.metadata["last_updated"] = datetime.utcnow().isoformat()
            
            # Log the status update
            from security.audit_logger import create_security_event
            status_event = create_security_event(
                SecurityEventType.SYSTEM_SECURITY_UPDATE,
                SecuritySeverity.INFO,
                "dashboard",
                action="incident_status_updated",
                resource=incident_id,
                result=status,
                metadata={
                    "incident_id": incident_id,
                    "new_status": status,
                    "assigned_to": assigned_to,
                    "notes": notes
                }
            )
            await self.audit_logger.log_event(status_event)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update incident status: {e}")
            return False
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        try:
            alert = self.active_alerts.get(alert_id)
            if not alert:
                return False
            
            alert.auto_resolved = True
            alert.requires_action = False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            return False
    
    def get_dashboard_health(self) -> Dict[str, Any]:
        """Get dashboard system health."""
        return {
            "status": "healthy",
            "uptime_seconds": (datetime.utcnow() - self.last_metrics_update).total_seconds(),
            "metrics_collection": "active" if self._metrics_task else "inactive",
            "last_update": self.last_metrics_update.isoformat(),
            "performance": self.dashboard_performance,
            "data_points": {
                "current_metrics": bool(self.current_metrics),
                "historical_metrics": len(self.historical_metrics),
                "active_alerts": len(self.active_alerts),
                "time_series_points": len(self.metrics_history.get("timestamp", []))
            }
        }


# Global dashboard instance
dashboard = SecurityDashboard(audit_logger, security_monitor)


# REST API endpoint functions for easy integration
async def get_dashboard_api_data() -> Dict[str, Any]:
    """API endpoint for dashboard data."""
    return await dashboard.get_dashboard_data()


async def get_security_overview_api() -> Dict[str, Any]:
    """API endpoint for security overview."""
    return await dashboard.get_security_overview()


async def get_incident_details_api(incident_id: str) -> Dict[str, Any]:
    """API endpoint for incident details."""
    details = await dashboard.get_incident_details(incident_id)
    return details or {"error": "Incident not found"}


async def update_incident_api(incident_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """API endpoint for incident updates."""
    success = await dashboard.update_incident_status(
        incident_id=incident_id,
        status=updates.get("status"),
        assigned_to=updates.get("assigned_to"),
        notes=updates.get("notes")
    )
    return {"success": success}


def get_dashboard_health_api() -> Dict[str, Any]:
    """API endpoint for dashboard health."""
    return dashboard.get_dashboard_health()


if __name__ == "__main__":
    # Example usage and testing
    async def main():
        # Initialize components
        from security.audit_logger import SecurityAuditLogger, create_security_event
        from security.security_monitor import SecurityMonitor
        
        audit = SecurityAuditLogger()
        monitor = SecurityMonitor()
        dash = SecurityDashboard(audit, monitor)
        
        # Generate some test data
        test_events = [
            create_security_event(
                SecurityEventType.AUTH_LOGIN_SUCCESS,
                SecuritySeverity.INFO,
                "auth_service",
                user_id="test_user"
            ),
            create_security_event(
                SecurityEventType.SECURITY_COMMAND_BLOCKED,
                SecuritySeverity.HIGH,
                "security_manager",
                user_id="test_user",
                action="rm -rf /"
            )
        ]
        
        print("Logging test events...")
        for event in test_events:
            await audit.log_event(event)
            await monitor.process_security_event(event)
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Get dashboard data
        dashboard_data = await dash.get_dashboard_data()
        print(f"\nDashboard Status: {dashboard_data['status']}")
        
        if dashboard_data.get("current_metrics"):
            metrics = dashboard_data["current_metrics"]
            print(f"Total Events: {metrics['total_events']}")
            print(f"Security Score: {metrics['security_score']}")
            print(f"System Status: {metrics['system_status']}")
            print(f"Active Incidents: {metrics['active_incidents']}")
        
        # Get security overview
        overview = await dash.get_security_overview()
        print(f"\nSecurity Overview:")
        print(f"Threat Level: {overview.get('threat_level', 'Unknown')}")
        print(f"Compliance Status: {overview.get('compliance_status', 'Unknown')}")
        
        # Dashboard health
        health = dash.get_dashboard_health()
        print(f"\nDashboard Health: {health['status']}")
    
    # Run test
    asyncio.run(main())