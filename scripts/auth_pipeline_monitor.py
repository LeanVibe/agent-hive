#!/usr/bin/env python3
"""
Authentication-Authorization Pipeline Monitor
LeanVibe Agent Hive - Integrated Security Monitoring

Critical monitoring for JWT + RBAC combined pipeline:
- Real-time performance tracking (<150ms target)
- PostgreSQL authentication model monitoring
- RBAC framework performance analysis
- End-to-end auth/authz flow monitoring
- Critical path latency detection
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from contextlib import asynccontextmanager
import psutil
import sqlite3

# Import existing monitoring components
from audit_logging_system import AuditLogger, AuditEvent, AuditEventType, AuditSeverity
from security_dashboard import SecurityMetricsCollector, SecurityMetric, SecurityMetricType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AuthStage(Enum):
    """Authentication/Authorization pipeline stages"""
    JWT_VALIDATION = "jwt_validation"
    POSTGRESQL_AUTH = "postgresql_auth"
    RBAC_EVALUATION = "rbac_evaluation"
    PERMISSION_CHECK = "permission_check"
    RESOURCE_ACCESS = "resource_access"
    COMPLETE = "complete"


class AuthResult(Enum):
    """Authentication/Authorization results"""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class AuthPipelineMetrics:
    """Comprehensive auth/authz pipeline metrics"""
    request_id: str
    timestamp: datetime
    user_id: str
    resource: str
    action: str
    
    # Timing metrics (milliseconds)
    total_time: float
    jwt_time: float
    postgresql_time: float
    rbac_time: float
    permission_time: float
    
    # Stage results
    jwt_result: AuthResult
    postgresql_result: AuthResult
    rbac_result: AuthResult
    permission_result: AuthResult
    final_result: AuthResult
    
    # Performance indicators
    exceeded_sla: bool  # >150ms
    critical_path: str  # Slowest stage
    
    # Security indicators
    suspicious_patterns: List[str]
    risk_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['jwt_result'] = self.jwt_result.value
        data['postgresql_result'] = self.postgresql_result.value
        data['rbac_result'] = self.rbac_result.value
        data['permission_result'] = self.permission_result.value
        data['final_result'] = self.final_result.value
        return data


@dataclass
class AuthPerformanceStats:
    """Authentication/Authorization performance statistics"""
    period_start: datetime
    period_end: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_total_time: float
    p95_total_time: float
    p99_total_time: float
    sla_violations: int
    sla_compliance_rate: float
    
    # Stage-specific metrics
    jwt_avg_time: float
    postgresql_avg_time: float
    rbac_avg_time: float
    permission_avg_time: float
    
    # Security metrics
    suspicious_activity_count: int
    high_risk_requests: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['period_start'] = self.period_start.isoformat()
        data['period_end'] = self.period_end.isoformat()
        return data


class AuthPipelineMonitor:
    """Comprehensive monitoring for integrated auth/authz pipeline"""
    
    def __init__(self):
        self.db_path = "auth_pipeline_metrics.db"
        self.audit_logger = AuditLogger()
        self.metrics_collector = SecurityMetricsCollector(None)
        self.lock = threading.Lock()
        
        # Performance targets
        self.sla_target_ms = 150  # <150ms total target
        self.warning_threshold_ms = 120  # Warning at 120ms
        self.critical_threshold_ms = 200  # Critical at 200ms
        
        # Initialize database
        self._init_database()
        
        # Start monitoring tasks
        self._start_monitoring_tasks()
    
    def _init_database(self):
        """Initialize auth pipeline monitoring database"""
        with sqlite3.connect(self.db_path) as conn:
            # Main metrics table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS auth_pipeline_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    action TEXT NOT NULL,
                    total_time REAL NOT NULL,
                    jwt_time REAL NOT NULL,
                    postgresql_time REAL NOT NULL,
                    rbac_time REAL NOT NULL,
                    permission_time REAL NOT NULL,
                    jwt_result TEXT NOT NULL,
                    postgresql_result TEXT NOT NULL,
                    rbac_result TEXT NOT NULL,
                    permission_result TEXT NOT NULL,
                    final_result TEXT NOT NULL,
                    exceeded_sla BOOLEAN NOT NULL,
                    critical_path TEXT NOT NULL,
                    suspicious_patterns TEXT,
                    risk_score REAL NOT NULL
                )
            ''')
            
            # Performance statistics table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS auth_performance_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    total_requests INTEGER NOT NULL,
                    successful_requests INTEGER NOT NULL,
                    failed_requests INTEGER NOT NULL,
                    avg_total_time REAL NOT NULL,
                    p95_total_time REAL NOT NULL,
                    p99_total_time REAL NOT NULL,
                    sla_violations INTEGER NOT NULL,
                    sla_compliance_rate REAL NOT NULL,
                    jwt_avg_time REAL NOT NULL,
                    postgresql_avg_time REAL NOT NULL,
                    rbac_avg_time REAL NOT NULL,
                    permission_avg_time REAL NOT NULL,
                    suspicious_activity_count INTEGER NOT NULL,
                    high_risk_requests INTEGER NOT NULL
                )
            ''')
            
            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON auth_pipeline_metrics(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON auth_pipeline_metrics(user_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_total_time ON auth_pipeline_metrics(total_time)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_exceeded_sla ON auth_pipeline_metrics(exceeded_sla)')
    
    def record_auth_pipeline_metrics(self, metrics: AuthPipelineMetrics) -> bool:
        """Record authentication pipeline metrics"""
        try:
            with self.lock:
                # Store in database
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT INTO auth_pipeline_metrics (
                            request_id, timestamp, user_id, resource, action,
                            total_time, jwt_time, postgresql_time, rbac_time, permission_time,
                            jwt_result, postgresql_result, rbac_result, permission_result, final_result,
                            exceeded_sla, critical_path, suspicious_patterns, risk_score
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        metrics.request_id,
                        metrics.timestamp.isoformat(),
                        metrics.user_id,
                        metrics.resource,
                        metrics.action,
                        metrics.total_time,
                        metrics.jwt_time,
                        metrics.postgresql_time,
                        metrics.rbac_time,
                        metrics.permission_time,
                        metrics.jwt_result.value,
                        metrics.postgresql_result.value,
                        metrics.rbac_result.value,
                        metrics.permission_result.value,
                        metrics.final_result.value,
                        metrics.exceeded_sla,
                        metrics.critical_path,
                        json.dumps(metrics.suspicious_patterns),
                        metrics.risk_score
                    ))
                
                # Log to audit system
                self._log_auth_event(metrics)
                
                # Check for alerts
                self._check_performance_alerts(metrics)
                
                logger.debug(f"Recorded auth pipeline metrics: {metrics.request_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to record auth pipeline metrics: {e}")
            return False
    
    def _log_auth_event(self, metrics: AuthPipelineMetrics):
        """Log authentication event to audit system"""
        severity = AuditSeverity.INFO
        if metrics.exceeded_sla:
            severity = AuditSeverity.WARNING
        if metrics.final_result == AuthResult.FAILURE:
            severity = AuditSeverity.ERROR
        if metrics.risk_score > 0.7:
            severity = AuditSeverity.CRITICAL
        
        event = AuditEvent(
            event_id=f"auth_pipeline_{metrics.request_id}",
            timestamp=metrics.timestamp,
            event_type=AuditEventType.AUTHENTICATION,
            severity=severity,
            actor_id=metrics.user_id,
            actor_type="user",
            target_resource=metrics.resource,
            action=metrics.action,
            outcome=metrics.final_result.value,
            details={
                "total_time": metrics.total_time,
                "jwt_time": metrics.jwt_time,
                "postgresql_time": metrics.postgresql_time,
                "rbac_time": metrics.rbac_time,
                "permission_time": metrics.permission_time,
                "exceeded_sla": metrics.exceeded_sla,
                "critical_path": metrics.critical_path,
                "risk_score": metrics.risk_score
            },
            risk_indicators=metrics.suspicious_patterns,
            compliance_tags=["authentication", "authorization", "performance"]
        )
        
        self.audit_logger.log_event(event)
    
    def _check_performance_alerts(self, metrics: AuthPipelineMetrics):
        """Check for performance alerts and trigger notifications"""
        alerts = []
        
        # SLA violation alert
        if metrics.exceeded_sla:
            alerts.append(f"SLA VIOLATION: Auth pipeline took {metrics.total_time:.1f}ms (target: {self.sla_target_ms}ms)")
        
        # Critical performance alert
        if metrics.total_time > self.critical_threshold_ms:
            alerts.append(f"CRITICAL: Auth pipeline severely degraded: {metrics.total_time:.1f}ms")
        
        # Stage-specific alerts
        if metrics.jwt_time > 50:
            alerts.append(f"JWT validation slow: {metrics.jwt_time:.1f}ms")
        if metrics.postgresql_time > 75:
            alerts.append(f"PostgreSQL authentication slow: {metrics.postgresql_time:.1f}ms")
        if metrics.rbac_time > 30:
            alerts.append(f"RBAC evaluation slow: {metrics.rbac_time:.1f}ms")
        
        # Security alerts
        if metrics.risk_score > 0.7:
            alerts.append(f"HIGH RISK: Authentication request risk score: {metrics.risk_score:.2f}")
        
        if metrics.suspicious_patterns:
            alerts.append(f"SUSPICIOUS ACTIVITY: {', '.join(metrics.suspicious_patterns)}")
        
        # Log alerts
        for alert in alerts:
            logger.warning(f"AUTH PIPELINE ALERT: {alert}")
    
    def get_performance_stats(self, hours: int = 1) -> AuthPerformanceStats:
        """Get authentication pipeline performance statistics"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN final_result = 'success' THEN 1 ELSE 0 END) as successful_requests,
                    SUM(CASE WHEN final_result = 'failure' THEN 1 ELSE 0 END) as failed_requests,
                    AVG(total_time) as avg_total_time,
                    AVG(jwt_time) as jwt_avg_time,
                    AVG(postgresql_time) as postgresql_avg_time,
                    AVG(rbac_time) as rbac_avg_time,
                    AVG(permission_time) as permission_avg_time,
                    SUM(CASE WHEN exceeded_sla = 1 THEN 1 ELSE 0 END) as sla_violations,
                    SUM(CASE WHEN risk_score > 0.7 THEN 1 ELSE 0 END) as high_risk_requests
                FROM auth_pipeline_metrics
                WHERE timestamp >= ? AND timestamp <= ?
            ''', (start_time.isoformat(), end_time.isoformat()))
            
            row = cursor.fetchone()
            
            if row[0] == 0:  # No data
                return AuthPerformanceStats(
                    period_start=start_time,
                    period_end=end_time,
                    total_requests=0,
                    successful_requests=0,
                    failed_requests=0,
                    avg_total_time=0.0,
                    p95_total_time=0.0,
                    p99_total_time=0.0,
                    sla_violations=0,
                    sla_compliance_rate=100.0,
                    jwt_avg_time=0.0,
                    postgresql_avg_time=0.0,
                    rbac_avg_time=0.0,
                    permission_avg_time=0.0,
                    suspicious_activity_count=0,
                    high_risk_requests=0
                )
            
            # Calculate percentiles
            cursor = conn.execute('''
                SELECT total_time FROM auth_pipeline_metrics
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY total_time
            ''', (start_time.isoformat(), end_time.isoformat()))
            
            times = [row[0] for row in cursor.fetchall()]
            p95_time = times[int(len(times) * 0.95)] if times else 0.0
            p99_time = times[int(len(times) * 0.99)] if times else 0.0
            
            # Count suspicious activity
            cursor = conn.execute('''
                SELECT COUNT(*) FROM auth_pipeline_metrics
                WHERE timestamp >= ? AND timestamp <= ?
                AND suspicious_patterns != '[]'
            ''', (start_time.isoformat(), end_time.isoformat()))
            
            suspicious_count = cursor.fetchone()[0]
            
            total_requests = row[0]
            successful_requests = row[1]
            sla_violations = row[8]
            sla_compliance_rate = ((total_requests - sla_violations) / total_requests * 100) if total_requests > 0 else 100.0
            
            return AuthPerformanceStats(
                period_start=start_time,
                period_end=end_time,
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=row[2],
                avg_total_time=row[3] or 0.0,
                p95_total_time=p95_time,
                p99_total_time=p99_time,
                sla_violations=sla_violations,
                sla_compliance_rate=sla_compliance_rate,
                jwt_avg_time=row[4] or 0.0,
                postgresql_avg_time=row[5] or 0.0,
                rbac_avg_time=row[6] or 0.0,
                permission_avg_time=row[7] or 0.0,
                suspicious_activity_count=suspicious_count,
                high_risk_requests=row[9]
            )
    
    def get_critical_path_analysis(self, hours: int = 1) -> Dict[str, Any]:
        """Analyze critical path performance bottlenecks"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            # Get stage timing analysis
            cursor = conn.execute('''
                SELECT 
                    AVG(jwt_time) as avg_jwt,
                    AVG(postgresql_time) as avg_postgresql,
                    AVG(rbac_time) as avg_rbac,
                    AVG(permission_time) as avg_permission,
                    MAX(jwt_time) as max_jwt,
                    MAX(postgresql_time) as max_postgresql,
                    MAX(rbac_time) as max_rbac,
                    MAX(permission_time) as max_permission
                FROM auth_pipeline_metrics
                WHERE timestamp >= ? AND timestamp <= ?
            ''', (start_time.isoformat(), end_time.isoformat()))
            
            row = cursor.fetchone()
            
            if not row:
                return {"error": "No data available for analysis"}
            
            # Critical path frequency
            cursor = conn.execute('''
                SELECT critical_path, COUNT(*) as count
                FROM auth_pipeline_metrics
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY critical_path
                ORDER BY count DESC
            ''', (start_time.isoformat(), end_time.isoformat()))
            
            critical_path_freq = dict(cursor.fetchall())
            
            # Performance bottleneck analysis
            stage_times = {
                'jwt_validation': {'avg': row[0] or 0, 'max': row[4] or 0},
                'postgresql_auth': {'avg': row[1] or 0, 'max': row[5] or 0},
                'rbac_evaluation': {'avg': row[2] or 0, 'max': row[6] or 0},
                'permission_check': {'avg': row[3] or 0, 'max': row[7] or 0}
            }
            
            # Identify bottlenecks
            bottlenecks = []
            if (row[1] or 0) > 75:  # PostgreSQL > 75ms
                bottlenecks.append("PostgreSQL authentication is the primary bottleneck")
            if (row[0] or 0) > 50:  # JWT > 50ms
                bottlenecks.append("JWT validation is slower than expected")
            if (row[2] or 0) > 30:  # RBAC > 30ms
                bottlenecks.append("RBAC evaluation needs optimization")
            
            return {
                'analysis_period': f"{hours} hours",
                'stage_performance': stage_times,
                'critical_path_frequency': critical_path_freq,
                'bottlenecks': bottlenecks,
                'recommendations': self._generate_performance_recommendations(stage_times)
            }
    
    def _generate_performance_recommendations(self, stage_times: Dict[str, Dict[str, float]]) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # PostgreSQL recommendations
        if stage_times['postgresql_auth']['avg'] > 75:
            recommendations.append("Optimize PostgreSQL authentication queries - consider connection pooling")
            recommendations.append("Review database indexes for authentication tables")
        
        # JWT recommendations
        if stage_times['jwt_validation']['avg'] > 50:
            recommendations.append("Optimize JWT validation - consider caching public keys")
            recommendations.append("Review JWT payload size and complexity")
        
        # RBAC recommendations
        if stage_times['rbac_evaluation']['avg'] > 30:
            recommendations.append("Optimize RBAC rule evaluation - consider caching permissions")
            recommendations.append("Review RBAC rule complexity and hierarchy")
        
        # General recommendations
        total_avg = sum(stage['avg'] for stage in stage_times.values())
        if total_avg > 150:
            recommendations.append("Consider parallel processing for independent auth stages")
            recommendations.append("Implement performance monitoring dashboards")
        
        return recommendations
    
    def _start_monitoring_tasks(self):
        """Start background monitoring tasks"""
        def monitoring_worker():
            while True:
                try:
                    # Generate periodic performance reports
                    stats = self.get_performance_stats(hours=1)
                    
                    # Check for performance degradation
                    if stats.sla_compliance_rate < 95:
                        logger.warning(f"AUTH PIPELINE DEGRADATION: SLA compliance at {stats.sla_compliance_rate:.1f}%")
                    
                    # Check for security issues
                    if stats.high_risk_requests > 0:
                        logger.warning(f"HIGH RISK AUTH REQUESTS: {stats.high_risk_requests} in last hour")
                    
                    # Store periodic stats
                    self._store_performance_stats(stats)
                    
                    # Sleep for 5 minutes
                    time.sleep(300)
                    
                except Exception as e:
                    logger.error(f"Monitoring task error: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=monitoring_worker, daemon=True)
        thread.start()
        logger.info("Auth pipeline monitoring tasks started")
    
    def _store_performance_stats(self, stats: AuthPerformanceStats):
        """Store performance statistics in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO auth_performance_stats (
                    period_start, period_end, total_requests, successful_requests, failed_requests,
                    avg_total_time, p95_total_time, p99_total_time, sla_violations, sla_compliance_rate,
                    jwt_avg_time, postgresql_avg_time, rbac_avg_time, permission_avg_time,
                    suspicious_activity_count, high_risk_requests
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                stats.period_start.isoformat(),
                stats.period_end.isoformat(),
                stats.total_requests,
                stats.successful_requests,
                stats.failed_requests,
                stats.avg_total_time,
                stats.p95_total_time,
                stats.p99_total_time,
                stats.sla_violations,
                stats.sla_compliance_rate,
                stats.jwt_avg_time,
                stats.postgresql_avg_time,
                stats.rbac_avg_time,
                stats.permission_avg_time,
                stats.suspicious_activity_count,
                stats.high_risk_requests
            ))
    
    def simulate_auth_request(self, user_id: str, resource: str, action: str) -> AuthPipelineMetrics:
        """Simulate an authentication request for testing"""
        import random
        
        request_id = f"auth_sim_{int(time.time() * 1000)}"
        
        # Simulate timing
        jwt_time = random.uniform(20, 60)
        postgresql_time = random.uniform(30, 90)
        rbac_time = random.uniform(15, 45)
        permission_time = random.uniform(10, 25)
        total_time = jwt_time + postgresql_time + rbac_time + permission_time
        
        # Simulate results
        jwt_result = AuthResult.SUCCESS if random.random() > 0.02 else AuthResult.FAILURE
        postgresql_result = AuthResult.SUCCESS if random.random() > 0.01 else AuthResult.FAILURE
        rbac_result = AuthResult.SUCCESS if random.random() > 0.01 else AuthResult.FAILURE
        permission_result = AuthResult.SUCCESS if random.random() > 0.005 else AuthResult.FAILURE
        
        final_result = AuthResult.SUCCESS if all(r == AuthResult.SUCCESS for r in [jwt_result, postgresql_result, rbac_result, permission_result]) else AuthResult.FAILURE
        
        # Determine critical path
        stage_times = {
            'jwt_validation': jwt_time,
            'postgresql_auth': postgresql_time,
            'rbac_evaluation': rbac_time,
            'permission_check': permission_time
        }
        critical_path = max(stage_times.keys(), key=lambda k: stage_times[k])
        
        # Simulate suspicious patterns
        suspicious_patterns = []
        if random.random() < 0.05:  # 5% chance
            suspicious_patterns.append("unusual_timing_pattern")
        if random.random() < 0.02:  # 2% chance
            suspicious_patterns.append("repeated_failures")
        
        risk_score = random.random() * 0.3  # Usually low risk
        if suspicious_patterns:
            risk_score += 0.4
        
        return AuthPipelineMetrics(
            request_id=request_id,
            timestamp=datetime.now(),
            user_id=user_id,
            resource=resource,
            action=action,
            total_time=total_time,
            jwt_time=jwt_time,
            postgresql_time=postgresql_time,
            rbac_time=rbac_time,
            permission_time=permission_time,
            jwt_result=jwt_result,
            postgresql_result=postgresql_result,
            rbac_result=rbac_result,
            permission_result=permission_result,
            final_result=final_result,
            exceeded_sla=total_time > self.sla_target_ms,
            critical_path=critical_path,
            suspicious_patterns=suspicious_patterns,
            risk_score=risk_score
        )


# Global auth pipeline monitor instance
auth_pipeline_monitor = AuthPipelineMonitor()


# Integration functions for Security and Infrastructure agents
def record_jwt_validation_time(request_id: str, user_id: str, validation_time: float, result: AuthResult):
    """Record JWT validation timing - called by Security Agent"""
    logger.info(f"JWT validation for {user_id}: {validation_time:.1f}ms - {result.value}")

def record_postgresql_auth_time(request_id: str, user_id: str, auth_time: float, result: AuthResult):
    """Record PostgreSQL authentication timing - called by Infrastructure Agent"""
    logger.info(f"PostgreSQL auth for {user_id}: {auth_time:.1f}ms - {result.value}")

def record_rbac_evaluation_time(request_id: str, user_id: str, rbac_time: float, result: AuthResult):
    """Record RBAC evaluation timing - called by Infrastructure Agent"""
    logger.info(f"RBAC evaluation for {user_id}: {rbac_time:.1f}ms - {result.value}")


if __name__ == "__main__":
    # Test the auth pipeline monitor
    print("Authentication Pipeline Monitor Test")
    print("=" * 50)
    
    # Simulate some auth requests
    for i in range(10):
        metrics = auth_pipeline_monitor.simulate_auth_request(
            user_id=f"user_{i}",
            resource="api/data",
            action="read"
        )
        auth_pipeline_monitor.record_auth_pipeline_metrics(metrics)
        print(f"Request {i+1}: {metrics.total_time:.1f}ms - {metrics.final_result.value}")
    
    # Get performance stats
    stats = auth_pipeline_monitor.get_performance_stats(hours=1)
    print(f"\nPerformance Stats:")
    print(f"Total Requests: {stats.total_requests}")
    print(f"Success Rate: {stats.successful_requests / stats.total_requests * 100:.1f}%")
    print(f"Average Time: {stats.avg_total_time:.1f}ms")
    print(f"SLA Compliance: {stats.sla_compliance_rate:.1f}%")
    
    # Critical path analysis
    analysis = auth_pipeline_monitor.get_critical_path_analysis(hours=1)
    print(f"\nCritical Path Analysis:")
    print(f"Bottlenecks: {analysis.get('bottlenecks', [])}")
    print(f"Recommendations: {analysis.get('recommendations', [])}")
    
    print("\nAuth pipeline monitoring ready for integration!")