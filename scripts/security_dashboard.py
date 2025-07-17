#!/usr/bin/env python3
"""
Security Metrics Dashboard - Real-time Security Monitoring
LeanVibe Agent Hive Foundation Epic Phase 2 - Continuous Security Monitoring

Comprehensive security dashboard with:
- Real-time security metrics visualization
- Authentication/authorization monitoring
- Compliance tracking and reporting
- Security event detection and alerting
- Threat pattern recognition
- Security KPIs integration
"""

import asyncio
import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

# Import existing security framework
from security.security_manager import SecurityManager, SecurityEvent, RiskLevel
from monitoring_core import MonitoringCore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('security_dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SecurityMetricType(Enum):
    """Security metric types for dashboard"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VULNERABILITY = "vulnerability"
    THREAT_DETECTION = "threat_detection"
    COMPLIANCE = "compliance"
    INCIDENT = "incident"
    AUDIT = "audit"


@dataclass
class SecurityMetric:
    """Security metric data structure"""
    metric_type: SecurityMetricType
    name: str
    value: float
    threshold: float
    status: str  # "healthy", "warning", "critical"
    timestamp: datetime
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['metric_type'] = self.metric_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class SecurityAlert:
    """Security alert data structure"""
    alert_id: str
    severity: str
    title: str
    description: str
    source: str
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class SecurityMetricsCollector:
    """Collects and aggregates security metrics from various sources"""
    
    def __init__(self, security_manager: SecurityManager):
        self.security_manager = security_manager
        self.metrics_db = "security_metrics.db"
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize security metrics database"""
        with sqlite3.connect(self.metrics_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS security_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT NOT NULL
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS security_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    source TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    acknowledged BOOLEAN DEFAULT 0,
                    resolved BOOLEAN DEFAULT 0
                )
            ''')
            
            conn.execute('CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON security_metrics(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON security_alerts(timestamp)')
    
    def collect_authentication_metrics(self) -> List[SecurityMetric]:
        """Collect authentication-related metrics"""
        metrics = []
        
        # Get recent authentication events
        auth_events = self.security_manager.get_security_events(
            start_time=datetime.now() - timedelta(hours=1),
            limit=1000
        )
        
        # Authentication success rate
        auth_attempts = [e for e in auth_events if e.event_type == "authentication"]
        if auth_attempts:
            success_rate = len([e for e in auth_attempts if e.result == "success"]) / len(auth_attempts) * 100
            metrics.append(SecurityMetric(
                metric_type=SecurityMetricType.AUTHENTICATION,
                name="auth_success_rate",
                value=success_rate,
                threshold=95.0,
                status="healthy" if success_rate >= 95 else "warning" if success_rate >= 85 else "critical",
                timestamp=datetime.now(),
                details={"total_attempts": len(auth_attempts), "successful": len([e for e in auth_attempts if e.result == "success"])}
            ))
        
        # Failed authentication attempts
        failed_attempts = len([e for e in auth_events if e.event_type == "authentication" and e.result == "failed"])
        metrics.append(SecurityMetric(
            metric_type=SecurityMetricType.AUTHENTICATION,
            name="failed_auth_attempts",
            value=float(failed_attempts),
            threshold=10.0,
            status="healthy" if failed_attempts < 5 else "warning" if failed_attempts < 10 else "critical",
            timestamp=datetime.now(),
            details={"count": failed_attempts, "period": "1 hour"}
        ))
        
        return metrics
    
    def collect_authorization_metrics(self) -> List[SecurityMetric]:
        """Collect authorization-related metrics"""
        metrics = []
        
        # Get recent authorization events
        auth_events = self.security_manager.get_security_events(
            start_time=datetime.now() - timedelta(hours=1),
            limit=1000
        )
        
        # Permission denied events
        permission_denied = [e for e in auth_events if e.event_type == "permission_denied"]
        metrics.append(SecurityMetric(
            metric_type=SecurityMetricType.AUTHORIZATION,
            name="permission_denied_events",
            value=float(len(permission_denied)),
            threshold=5.0,
            status="healthy" if len(permission_denied) < 3 else "warning" if len(permission_denied) < 5 else "critical",
            timestamp=datetime.now(),
            details={"count": len(permission_denied), "period": "1 hour"}
        ))
        
        # Access control violations
        violations = [e for e in auth_events if e.event_type == "access_violation"]
        metrics.append(SecurityMetric(
            metric_type=SecurityMetricType.AUTHORIZATION,
            name="access_violations",
            value=float(len(violations)),
            threshold=0.0,
            status="healthy" if len(violations) == 0 else "warning" if len(violations) < 3 else "critical",
            timestamp=datetime.now(),
            details={"count": len(violations), "period": "1 hour"}
        ))
        
        return metrics
    
    def collect_vulnerability_metrics(self) -> List[SecurityMetric]:
        """Collect vulnerability assessment metrics"""
        metrics = []
        
        # Get security summary from existing security monitoring
        try:
            from scripts.security_monitoring import SecurityMonitor
            monitor = SecurityMonitor()
            scan_results = monitor.run_comprehensive_security_scan()
            
            # Critical vulnerabilities
            critical_vulns = 0
            if scan_results.get("bandit_scan", {}).get("status") == "completed":
                critical_vulns += scan_results["bandit_scan"].get("high_severity", 0)
            if scan_results.get("safety_scan", {}).get("status") == "completed":
                critical_vulns += scan_results["safety_scan"].get("critical_vulnerabilities", 0)
            if scan_results.get("pip_audit_scan", {}).get("status") == "completed":
                critical_vulns += scan_results["pip_audit_scan"].get("total_vulnerabilities", 0)
            
            metrics.append(SecurityMetric(
                metric_type=SecurityMetricType.VULNERABILITY,
                name="critical_vulnerabilities",
                value=float(critical_vulns),
                threshold=0.0,
                status="healthy" if critical_vulns == 0 else "warning" if critical_vulns < 3 else "critical",
                timestamp=datetime.now(),
                details={"scan_results": scan_results}
            ))
            
            # Security score
            security_score = scan_results.get("security_score", 100)
            metrics.append(SecurityMetric(
                metric_type=SecurityMetricType.VULNERABILITY,
                name="security_score",
                value=security_score,
                threshold=85.0,
                status="healthy" if security_score >= 85 else "warning" if security_score >= 70 else "critical",
                timestamp=datetime.now(),
                details={"scan_results": scan_results}
            ))
            
        except Exception as e:
            logger.error(f"Error collecting vulnerability metrics: {e}")
        
        return metrics
    
    def collect_threat_detection_metrics(self) -> List[SecurityMetric]:
        """Collect threat detection metrics"""
        metrics = []
        
        # Get recent security events
        security_events = self.security_manager.get_security_events(
            start_time=datetime.now() - timedelta(hours=24),
            limit=1000
        )
        
        # High-risk events
        high_risk_events = [e for e in security_events if e.risk_level == RiskLevel.HIGH]
        metrics.append(SecurityMetric(
            metric_type=SecurityMetricType.THREAT_DETECTION,
            name="high_risk_events",
            value=float(len(high_risk_events)),
            threshold=5.0,
            status="healthy" if len(high_risk_events) < 3 else "warning" if len(high_risk_events) < 5 else "critical",
            timestamp=datetime.now(),
            details={"count": len(high_risk_events), "period": "24 hours"}
        ))
        
        # Critical risk events
        critical_risk_events = [e for e in security_events if e.risk_level == RiskLevel.CRITICAL]
        metrics.append(SecurityMetric(
            metric_type=SecurityMetricType.THREAT_DETECTION,
            name="critical_risk_events",
            value=float(len(critical_risk_events)),
            threshold=0.0,
            status="healthy" if len(critical_risk_events) == 0 else "critical",
            timestamp=datetime.now(),
            details={"count": len(critical_risk_events), "period": "24 hours"}
        ))
        
        # Suspicious activity patterns
        suspicious_patterns = self._detect_suspicious_patterns(security_events)
        metrics.append(SecurityMetric(
            metric_type=SecurityMetricType.THREAT_DETECTION,
            name="suspicious_patterns",
            value=float(len(suspicious_patterns)),
            threshold=2.0,
            status="healthy" if len(suspicious_patterns) < 1 else "warning" if len(suspicious_patterns) < 2 else "critical",
            timestamp=datetime.now(),
            details={"patterns": suspicious_patterns}
        ))
        
        return metrics
    
    def collect_compliance_metrics(self) -> List[SecurityMetric]:
        """Collect compliance monitoring metrics"""
        metrics = []
        
        # Audit log completeness
        audit_events = self.security_manager.get_security_events(
            start_time=datetime.now() - timedelta(hours=24),
            limit=10000
        )
        
        # Calculate audit coverage
        expected_events = 1000  # Expected number of events per day
        actual_events = len(audit_events)
        coverage = min(100.0, (actual_events / expected_events) * 100)
        
        metrics.append(SecurityMetric(
            metric_type=SecurityMetricType.COMPLIANCE,
            name="audit_log_completeness",
            value=coverage,
            threshold=95.0,
            status="healthy" if coverage >= 95 else "warning" if coverage >= 85 else "critical",
            timestamp=datetime.now(),
            details={"expected": expected_events, "actual": actual_events}
        ))
        
        # Security policy compliance
        policy_violations = [e for e in audit_events if e.event_type == "policy_violation"]
        metrics.append(SecurityMetric(
            metric_type=SecurityMetricType.COMPLIANCE,
            name="policy_violations",
            value=float(len(policy_violations)),
            threshold=0.0,
            status="healthy" if len(policy_violations) == 0 else "warning" if len(policy_violations) < 3 else "critical",
            timestamp=datetime.now(),
            details={"violations": len(policy_violations), "period": "24 hours"}
        ))
        
        return metrics
    
    def _detect_suspicious_patterns(self, events: List[SecurityEvent]) -> List[Dict[str, Any]]:
        """Detect suspicious activity patterns"""
        patterns = []
        
        # Pattern 1: Repeated failed attempts from same agent
        failed_attempts = {}
        for event in events:
            if event.result == "failed":
                key = event.agent_id
                failed_attempts[key] = failed_attempts.get(key, 0) + 1
        
        for agent_id, count in failed_attempts.items():
            if count >= 5:
                patterns.append({
                    "type": "repeated_failures",
                    "agent_id": agent_id,
                    "count": count,
                    "description": f"Agent {agent_id} has {count} failed attempts"
                })
        
        # Pattern 2: Unusual time-based activity
        hour_counts = {}
        for event in events:
            hour = event.timestamp.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        # Check for unusual off-hours activity (2 AM - 6 AM)
        off_hours_activity = sum(hour_counts.get(h, 0) for h in range(2, 7))
        if off_hours_activity > 50:
            patterns.append({
                "type": "off_hours_activity",
                "count": off_hours_activity,
                "description": f"High activity during off-hours: {off_hours_activity} events"
            })
        
        return patterns
    
    def store_metrics(self, metrics: List[SecurityMetric]):
        """Store metrics in database"""
        with self.lock:
            with sqlite3.connect(self.metrics_db) as conn:
                for metric in metrics:
                    conn.execute('''
                        INSERT INTO security_metrics (
                            metric_type, name, value, threshold, status, timestamp, details
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        metric.metric_type.value,
                        metric.name,
                        metric.value,
                        metric.threshold,
                        metric.status,
                        metric.timestamp.isoformat(),
                        json.dumps(metric.details)
                    ))
    
    def get_recent_metrics(self, hours: int = 24) -> List[SecurityMetric]:
        """Get recent security metrics"""
        start_time = datetime.now() - timedelta(hours=hours)
        
        with sqlite3.connect(self.metrics_db) as conn:
            cursor = conn.execute('''
                SELECT metric_type, name, value, threshold, status, timestamp, details
                FROM security_metrics
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            ''', (start_time.isoformat(),))
            
            metrics = []
            for row in cursor.fetchall():
                metric = SecurityMetric(
                    metric_type=SecurityMetricType(row[0]),
                    name=row[1],
                    value=row[2],
                    threshold=row[3],
                    status=row[4],
                    timestamp=datetime.fromisoformat(row[5]),
                    details=json.loads(row[6])
                )
                metrics.append(metric)
        
        return metrics
    
    def collect_all_metrics(self) -> List[SecurityMetric]:
        """Collect all security metrics"""
        all_metrics = []
        
        try:
            all_metrics.extend(self.collect_authentication_metrics())
            all_metrics.extend(self.collect_authorization_metrics())
            all_metrics.extend(self.collect_vulnerability_metrics())
            all_metrics.extend(self.collect_threat_detection_metrics())
            all_metrics.extend(self.collect_compliance_metrics())
            
            # Store metrics
            self.store_metrics(all_metrics)
            
        except Exception as e:
            logger.error(f"Error collecting security metrics: {e}")
        
        return all_metrics


class SecurityDashboard:
    """Security dashboard server with real-time monitoring"""
    
    def __init__(self, config_path: str = "config/security_monitoring.json"):
        self.config = self._load_config(config_path)
        self.security_manager = SecurityManager()
        self.monitoring_core = MonitoringCore()
        self.metrics_collector = SecurityMetricsCollector(self.security_manager)
        self.websocket_connections: List[WebSocket] = []
        self.security_alerts: List[SecurityAlert] = []
        
        # Create lifespan context manager
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info("Starting security dashboard monitoring tasks")
            asyncio.create_task(self._monitor_security_metrics())
            asyncio.create_task(self._monitor_alerts())
            asyncio.create_task(self._broadcast_updates())
            yield
            # Shutdown
            logger.info("Shutting down security dashboard monitoring tasks")
        
        self.app = FastAPI(
            title="LeanVibe Security Dashboard",
            description="Real-time security monitoring and alerting",
            version="1.0.0",
            lifespan=lifespan
        )
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._setup_routes()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            return {}
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_page():
            """Serve the security dashboard HTML page"""
            return await self._get_dashboard_html()
        
        @self.app.get("/api/security/metrics")
        async def get_security_metrics():
            """Get current security metrics"""
            metrics = self.metrics_collector.collect_all_metrics()
            return {"metrics": [m.to_dict() for m in metrics]}
        
        @self.app.get("/api/security/metrics/history")
        async def get_metrics_history(hours: int = 24):
            """Get security metrics history"""
            metrics = self.metrics_collector.get_recent_metrics(hours)
            return {"metrics": [m.to_dict() for m in metrics]}
        
        @self.app.get("/api/security/alerts")
        async def get_security_alerts():
            """Get current security alerts"""
            return {"alerts": [a.to_dict() for a in self.security_alerts]}
        
        @self.app.post("/api/security/alerts/{alert_id}/acknowledge")
        async def acknowledge_alert(alert_id: str):
            """Acknowledge a security alert"""
            for alert in self.security_alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    return {"message": "Alert acknowledged"}
            raise HTTPException(status_code=404, detail="Alert not found")
        
        @self.app.post("/api/security/alerts/{alert_id}/resolve")
        async def resolve_alert(alert_id: str):
            """Resolve a security alert"""
            for alert in self.security_alerts:
                if alert.alert_id == alert_id:
                    alert.resolved = True
                    return {"message": "Alert resolved"}
            raise HTTPException(status_code=404, detail="Alert not found")
        
        @self.app.get("/api/security/events")
        async def get_security_events(hours: int = 24):
            """Get recent security events"""
            events = self.security_manager.get_security_events(
                start_time=datetime.now() - timedelta(hours=hours),
                limit=1000
            )
            return {"events": [e.to_dict() for e in events]}
        
        @self.app.get("/api/security/summary")
        async def get_security_summary():
            """Get security summary"""
            return {
                "summary": self.security_manager.get_security_summary(),
                "system_health": self.monitoring_core.get_health_status()
            }
        
        @self.app.get("/api/auth/pipeline/metrics")
        async def get_auth_pipeline_metrics():
            """Get authentication pipeline metrics"""
            from auth_pipeline_monitor import auth_pipeline_monitor
            stats = auth_pipeline_monitor.get_performance_stats(hours=1)
            return {"pipeline_metrics": stats.to_dict()}
        
        @self.app.get("/api/auth/pipeline/analysis")
        async def get_auth_pipeline_analysis():
            """Get authentication pipeline critical path analysis"""
            from auth_pipeline_monitor import auth_pipeline_monitor
            analysis = auth_pipeline_monitor.get_critical_path_analysis(hours=1)
            return {"analysis": analysis}
        
        @self.app.get("/api/unified/security/metrics")
        async def get_unified_security_metrics():
            """Get unified security metrics"""
            from unified_security_metrics import unified_security_metrics
            metrics = unified_security_metrics.collect_unified_metrics()
            return {"unified_metrics": [m.to_dict() for m in metrics]}
        
        @self.app.get("/api/unified/security/dashboard")
        async def get_unified_security_dashboard():
            """Get unified security dashboard"""
            from unified_security_metrics import unified_security_metrics
            dashboard = unified_security_metrics.generate_unified_dashboard()
            return {"dashboard": dashboard.to_dict()}
        
        @self.app.get("/api/integrated/audit/statistics")
        async def get_integrated_audit_statistics():
            """Get integrated audit statistics"""
            from integrated_audit_system import integrated_audit_system
            stats = integrated_audit_system.get_audit_statistics(hours=24)
            return {"audit_statistics": stats}
        
        @self.app.get("/api/integrated/audit/correlated/{user_id}/{session_id}")
        async def get_correlated_events(user_id: str, session_id: str):
            """Get correlated audit events for user session"""
            from integrated_audit_system import integrated_audit_system
            events = integrated_audit_system.get_correlated_events(user_id, session_id, hours=1)
            return {"correlated_events": [e.to_dict() for e in events]}

        @self.app.websocket("/ws/security")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time security updates"""
            await self._handle_websocket(websocket)
    
    async def _get_dashboard_html(self) -> str:
        """Generate security dashboard HTML"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>LeanVibe Security Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }
                .container { max-width: 1400px; margin: 0 auto; }
                .header { 
                    background: linear-gradient(135deg, #dc3545, #6f42c1); 
                    color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;
                    display: flex; justify-content: space-between; align-items: center;
                }
                .status-indicator { 
                    padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold;
                    display: inline-block; margin-left: 10px;
                }
                .status-healthy { background: #28a745; color: white; }
                .status-warning { background: #ffc107; color: #212529; }
                .status-critical { background: #dc3545; color: white; }
                
                .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }
                .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .metric-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
                .metric-title { font-size: 14px; color: #666; font-weight: 600; }
                .metric-value { font-size: 28px; font-weight: bold; color: #2c3e50; }
                .metric-threshold { font-size: 12px; color: #888; }
                .metric-details { margin-top: 10px; font-size: 12px; color: #666; }
                
                .alerts-section { margin-top: 30px; }
                .alert-card { 
                    background: white; padding: 15px; border-radius: 8px; margin-bottom: 10px;
                    border-left: 4px solid #dc3545; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .alert-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
                .alert-title { font-weight: bold; color: #2c3e50; }
                .alert-severity { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
                .severity-critical { background: #dc3545; color: white; }
                .severity-high { background: #fd7e14; color: white; }
                .severity-medium { background: #ffc107; color: #212529; }
                .severity-low { background: #28a745; color: white; }
                
                .controls { display: flex; gap: 10px; margin-top: 10px; }
                .btn { padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; }
                .btn-primary { background: #007bff; color: white; }
                .btn-success { background: #28a745; color: white; }
                .btn-warning { background: #ffc107; color: #212529; }
                
                .events-section { margin-top: 30px; }
                .events-table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; }
                .events-table th, .events-table td { padding: 12px; text-align: left; border-bottom: 1px solid #dee2e6; }
                .events-table th { background: #f8f9fa; font-weight: 600; color: #495057; }
                .events-table tr:hover { background: #f8f9fa; }
                
                .chart-container { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .chart-title { font-size: 16px; font-weight: bold; margin-bottom: 15px; color: #2c3e50; }
                
                #connection-status { 
                    padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;
                }
                .connected { background: #28a745; color: white; }
                .disconnected { background: #dc3545; color: white; }
                
                .refresh-btn { 
                    background: #17a2b8; color: white; border: none; padding: 8px 16px; 
                    border-radius: 4px; cursor: pointer; font-size: 12px; margin-left: 10px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1>🔒 LeanVibe Security Dashboard</h1>
                        <span id="overall-status" class="status-indicator status-healthy">System Secure</span>
                    </div>
                    <div>
                        <span id="connection-status" class="disconnected">Disconnected</span>
                        <button class="refresh-btn" onclick="refreshData()">Refresh</button>
                    </div>
                </div>
                
                <div class="metrics-grid" id="metrics-grid">
                    <!-- Security metrics will be populated here -->
                </div>
                
                <div class="alerts-section">
                    <h2>🚨 Security Alerts</h2>
                    <div id="alerts-container">
                        <!-- Alerts will be populated here -->
                    </div>
                </div>
                
                <div class="events-section">
                    <h2>📊 Recent Security Events</h2>
                    <div class="chart-container">
                        <div class="chart-title">Security Events (Last 24 Hours)</div>
                        <table class="events-table" id="events-table">
                            <thead>
                                <tr>
                                    <th>Timestamp</th>
                                    <th>Event Type</th>
                                    <th>Agent ID</th>
                                    <th>Action</th>
                                    <th>Result</th>
                                    <th>Risk Level</th>
                                </tr>
                            </thead>
                            <tbody id="events-body">
                                <!-- Events will be populated here -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <script>
                let ws = null;
                let reconnectAttempts = 0;
                const maxReconnectAttempts = 5;
                
                function connectWebSocket() {
                    ws = new WebSocket('ws://localhost:8001/ws/security');
                    
                    ws.onopen = function() {
                        console.log('Security WebSocket connected');
                        document.getElementById('connection-status').textContent = 'Connected';
                        document.getElementById('connection-status').className = 'connected';
                        reconnectAttempts = 0;
                    };
                    
                    ws.onmessage = function(event) {
                        const data = JSON.parse(event.data);
                        if (data.type === 'metrics_update') {
                            updateMetrics(data.metrics);
                        } else if (data.type === 'alerts_update') {
                            updateAlerts(data.alerts);
                        } else if (data.type === 'events_update') {
                            updateEvents(data.events);
                        }
                    };
                    
                    ws.onclose = function() {
                        console.log('Security WebSocket disconnected');
                        document.getElementById('connection-status').textContent = 'Disconnected';
                        document.getElementById('connection-status').className = 'disconnected';
                        
                        if (reconnectAttempts < maxReconnectAttempts) {
                            reconnectAttempts++;
                            setTimeout(connectWebSocket, 2000 * reconnectAttempts);
                        }
                    };
                }
                
                function updateMetrics(metrics) {
                    const grid = document.getElementById('metrics-grid');
                    grid.innerHTML = metrics.map(metric => `
                        <div class="metric-card">
                            <div class="metric-header">
                                <div class="metric-title">${metric.name.replace(/_/g, ' ').toUpperCase()}</div>
                                <div class="status-indicator status-${metric.status}">${metric.status.toUpperCase()}</div>
                            </div>
                            <div class="metric-value">${metric.value}</div>
                            <div class="metric-threshold">Threshold: ${metric.threshold}</div>
                            <div class="metric-details">${metric.metric_type} | ${new Date(metric.timestamp).toLocaleString()}</div>
                        </div>
                    `).join('');
                    
                    // Update overall status
                    const criticalCount = metrics.filter(m => m.status === 'critical').length;
                    const warningCount = metrics.filter(m => m.status === 'warning').length;
                    const statusElement = document.getElementById('overall-status');
                    
                    if (criticalCount > 0) {
                        statusElement.textContent = `Critical Issues: ${criticalCount}`;
                        statusElement.className = 'status-indicator status-critical';
                    } else if (warningCount > 0) {
                        statusElement.textContent = `Warnings: ${warningCount}`;
                        statusElement.className = 'status-indicator status-warning';
                    } else {
                        statusElement.textContent = 'System Secure';
                        statusElement.className = 'status-indicator status-healthy';
                    }
                }
                
                function updateAlerts(alerts) {
                    const container = document.getElementById('alerts-container');
                    if (alerts.length === 0) {
                        container.innerHTML = '<p>No active security alerts</p>';
                        return;
                    }
                    
                    container.innerHTML = alerts.map(alert => `
                        <div class="alert-card">
                            <div class="alert-header">
                                <div class="alert-title">${alert.title}</div>
                                <div class="alert-severity severity-${alert.severity}">${alert.severity.toUpperCase()}</div>
                            </div>
                            <div class="alert-description">${alert.description}</div>
                            <div class="alert-details">
                                Source: ${alert.source} | ${new Date(alert.timestamp).toLocaleString()}
                            </div>
                            <div class="controls">
                                ${!alert.acknowledged ? `<button class="btn btn-warning" onclick="acknowledgeAlert('${alert.alert_id}')">Acknowledge</button>` : ''}
                                ${!alert.resolved ? `<button class="btn btn-success" onclick="resolveAlert('${alert.alert_id}')">Resolve</button>` : ''}
                            </div>
                        </div>
                    `).join('');
                }
                
                function updateEvents(events) {
                    const tbody = document.getElementById('events-body');
                    tbody.innerHTML = events.slice(0, 20).map(event => `
                        <tr>
                            <td>${new Date(event.timestamp).toLocaleString()}</td>
                            <td>${event.event_type}</td>
                            <td>${event.agent_id}</td>
                            <td>${event.action}</td>
                            <td>${event.result}</td>
                            <td><span class="status-indicator status-${event.risk_level.toLowerCase()}">${event.risk_level}</span></td>
                        </tr>
                    `).join('');
                }
                
                function acknowledgeAlert(alertId) {
                    fetch(`/api/security/alerts/${alertId}/acknowledge`, { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            console.log('Alert acknowledged:', data);
                            refreshAlerts();
                        })
                        .catch(error => console.error('Error acknowledging alert:', error));
                }
                
                function resolveAlert(alertId) {
                    fetch(`/api/security/alerts/${alertId}/resolve`, { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            console.log('Alert resolved:', data);
                            refreshAlerts();
                        })
                        .catch(error => console.error('Error resolving alert:', error));
                }
                
                function refreshData() {
                    refreshMetrics();
                    refreshAlerts();
                    refreshEvents();
                }
                
                function refreshMetrics() {
                    fetch('/api/security/metrics')
                        .then(response => response.json())
                        .then(data => updateMetrics(data.metrics))
                        .catch(error => console.error('Error loading metrics:', error));
                }
                
                function refreshAlerts() {
                    fetch('/api/security/alerts')
                        .then(response => response.json())
                        .then(data => updateAlerts(data.alerts))
                        .catch(error => console.error('Error loading alerts:', error));
                }
                
                function refreshEvents() {
                    fetch('/api/security/events')
                        .then(response => response.json())
                        .then(data => updateEvents(data.events))
                        .catch(error => console.error('Error loading events:', error));
                }
                
                // Initialize
                connectWebSocket();
                refreshData();
                
                // Auto-refresh every 30 seconds
                setInterval(refreshData, 30000);
            </script>
        </body>
        </html>
        """
    
    async def _handle_websocket(self, websocket: WebSocket):
        """Handle WebSocket connections"""
        await websocket.accept()
        self.websocket_connections.append(websocket)
        
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            if websocket in self.websocket_connections:
                self.websocket_connections.remove(websocket)
    
    async def _monitor_security_metrics(self):
        """Monitor security metrics periodically"""
        while True:
            try:
                logger.info("Collecting security metrics...")
                metrics = self.metrics_collector.collect_all_metrics()
                
                # Check for alerts
                for metric in metrics:
                    if metric.status == "critical":
                        alert = SecurityAlert(
                            alert_id=f"metric_{metric.name}_{int(time.time())}",
                            severity="critical",
                            title=f"Critical Security Metric: {metric.name}",
                            description=f"Security metric {metric.name} has reached critical threshold. Current value: {metric.value}, Threshold: {metric.threshold}",
                            source="security_metrics",
                            timestamp=datetime.now()
                        )
                        self.security_alerts.append(alert)
                        logger.warning(f"Critical security alert: {alert.title}")
                
                logger.info(f"Collected {len(metrics)} security metrics")
                
            except Exception as e:
                logger.error(f"Error monitoring security metrics: {e}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _monitor_alerts(self):
        """Monitor and manage security alerts"""
        while True:
            try:
                # Clean up resolved alerts older than 24 hours
                cutoff_time = datetime.now() - timedelta(hours=24)
                self.security_alerts = [
                    alert for alert in self.security_alerts 
                    if not (alert.resolved and alert.timestamp < cutoff_time)
                ]
                
                # Log active alerts
                active_alerts = [alert for alert in self.security_alerts if not alert.resolved]
                if active_alerts:
                    logger.info(f"Active security alerts: {len(active_alerts)}")
                
            except Exception as e:
                logger.error(f"Error monitoring alerts: {e}")
            
            await asyncio.sleep(300)  # Check every 5 minutes
    
    async def _broadcast_updates(self):
        """Broadcast updates to all WebSocket connections"""
        while True:
            try:
                if self.websocket_connections:
                    # Get current data
                    metrics = self.metrics_collector.collect_all_metrics()
                    alerts = self.security_alerts
                    events = self.security_manager.get_security_events(
                        start_time=datetime.now() - timedelta(hours=24),
                        limit=100
                    )
                    
                    # Send updates
                    updates = [
                        {"type": "metrics_update", "metrics": [m.to_dict() for m in metrics]},
                        {"type": "alerts_update", "alerts": [a.to_dict() for a in alerts]},
                        {"type": "events_update", "events": [e.to_dict() for e in events]}
                    ]
                    
                    # Broadcast to all connections
                    disconnected = []
                    for ws in self.websocket_connections:
                        try:
                            for update in updates:
                                await ws.send_text(json.dumps(update))
                        except Exception:
                            disconnected.append(ws)
                    
                    # Remove disconnected connections
                    for ws in disconnected:
                        if ws in self.websocket_connections:
                            self.websocket_connections.remove(ws)
                
            except Exception as e:
                logger.error(f"Error broadcasting updates: {e}")
            
            await asyncio.sleep(5)  # Broadcast every 5 seconds


def main():
    """Main function to run the security dashboard"""
    dashboard = SecurityDashboard()
    
    logger.info("Starting LeanVibe Security Dashboard")
    logger.info("Security dashboard available at: http://localhost:8001")
    
    uvicorn.run(dashboard.app, host="0.0.0.0", port=8001, log_level="info")


if __name__ == "__main__":
    main()