#!/usr/bin/env python3
"""
Unified Security Metrics - JWT + RBAC Performance Monitoring
LeanVibe Agent Hive - Integrated Security Performance Analysis

Critical metrics for unified authentication/authorization system:
- JWT validation performance tracking
- RBAC evaluation metrics
- Combined pipeline performance (<150ms SLA)
- Security vs Performance correlation analysis
- Real-time performance dashboards
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import statistics
import sqlite3

# Import monitoring components
from auth_pipeline_monitor import AuthPipelineMonitor, AuthPipelineMetrics, AuthPerformanceStats
from security_dashboard import SecurityMetric, SecurityMetricType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SecurityPerformanceMetricType(Enum):
    """Security performance metric types"""
    JWT_VALIDATION_TIME = "jwt_validation_time"
    RBAC_EVALUATION_TIME = "rbac_evaluation_time"
    COMBINED_AUTH_TIME = "combined_auth_time"
    SECURITY_THROUGHPUT = "security_throughput"
    AUTH_SUCCESS_RATE = "auth_success_rate"
    SECURITY_LATENCY_P95 = "security_latency_p95"
    SECURITY_LATENCY_P99 = "security_latency_p99"
    SLA_COMPLIANCE_RATE = "sla_compliance_rate"
    SECURITY_OVERHEAD = "security_overhead"
    RBAC_CACHE_HIT_RATE = "rbac_cache_hit_rate"


@dataclass
class SecurityPerformanceMetric:
    """Security performance metric with business correlation"""
    metric_type: SecurityPerformanceMetricType
    value: float
    timestamp: datetime
    target_value: float
    threshold_warning: float
    threshold_critical: float
    unit: str
    description: str
    
    # Performance context
    request_volume: int
    concurrent_users: int
    
    # Security context
    security_level: str  # "low", "medium", "high"
    threat_level: str    # "low", "medium", "high", "critical"
    
    # Business impact
    user_experience_impact: float  # 0-1 scale
    business_risk_score: float     # 0-1 scale
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['metric_type'] = self.metric_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def get_status(self) -> str:
        """Get metric status based on thresholds"""
        if self.value >= self.threshold_critical:
            return "critical"
        elif self.value >= self.threshold_warning:
            return "warning"
        else:
            return "healthy"


@dataclass
class UnifiedSecurityDashboard:
    """Unified security performance dashboard data"""
    timestamp: datetime
    
    # Core Performance Metrics
    jwt_avg_time: float
    rbac_avg_time: float
    total_auth_time: float
    sla_compliance_rate: float
    
    # Throughput Metrics
    requests_per_second: float
    concurrent_sessions: int
    
    # Security Metrics
    auth_success_rate: float
    security_incidents: int
    threat_level: str
    
    # Business Impact
    user_satisfaction_score: float
    business_continuity_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class UnifiedSecurityMetrics:
    """Unified security metrics collection and analysis"""
    
    def __init__(self):
        self.auth_monitor = AuthPipelineMonitor()
        self.db_path = "unified_security_metrics.db"
        self.lock = threading.Lock()
        
        # Performance targets
        self.sla_target_ms = 150
        self.jwt_target_ms = 50
        self.rbac_target_ms = 30
        self.throughput_target_rps = 1000
        
        # Initialize database
        self._init_database()
        
        # Start metrics collection
        self._start_metrics_collection()
    
    def _init_database(self):
        """Initialize unified security metrics database"""
        with sqlite3.connect(self.db_path) as conn:
            # Security performance metrics table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS security_performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    target_value REAL NOT NULL,
                    threshold_warning REAL NOT NULL,
                    threshold_critical REAL NOT NULL,
                    unit TEXT NOT NULL,
                    description TEXT NOT NULL,
                    request_volume INTEGER NOT NULL,
                    concurrent_users INTEGER NOT NULL,
                    security_level TEXT NOT NULL,
                    threat_level TEXT NOT NULL,
                    user_experience_impact REAL NOT NULL,
                    business_risk_score REAL NOT NULL
                )
            ''')
            
            # Dashboard snapshots table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS security_dashboard_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    jwt_avg_time REAL NOT NULL,
                    rbac_avg_time REAL NOT NULL,
                    total_auth_time REAL NOT NULL,
                    sla_compliance_rate REAL NOT NULL,
                    requests_per_second REAL NOT NULL,
                    concurrent_sessions INTEGER NOT NULL,
                    auth_success_rate REAL NOT NULL,
                    security_incidents INTEGER NOT NULL,
                    threat_level TEXT NOT NULL,
                    user_satisfaction_score REAL NOT NULL,
                    business_continuity_score REAL NOT NULL
                )
            ''')
            
            # Create indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_security_timestamp ON security_performance_metrics(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_security_metric_type ON security_performance_metrics(metric_type)')
    
    def collect_unified_metrics(self) -> List[SecurityPerformanceMetric]:
        """Collect all unified security performance metrics"""
        metrics = []
        
        try:
            # Get auth pipeline performance
            auth_stats = self.auth_monitor.get_performance_stats(hours=1)
            
            # Calculate current load
            current_load = self._calculate_current_load()
            
            # Determine security and threat levels
            security_level = self._assess_security_level(auth_stats)
            threat_level = self._assess_threat_level(auth_stats)
            
            # JWT Validation Time
            jwt_metric = SecurityPerformanceMetric(
                metric_type=SecurityPerformanceMetricType.JWT_VALIDATION_TIME,
                value=auth_stats.jwt_avg_time,
                timestamp=datetime.now(),
                target_value=self.jwt_target_ms,
                threshold_warning=self.jwt_target_ms * 0.8,
                threshold_critical=self.jwt_target_ms * 1.2,
                unit="ms",
                description="Average JWT validation time",
                request_volume=auth_stats.total_requests,
                concurrent_users=current_load['concurrent_users'],
                security_level=security_level,
                threat_level=threat_level,
                user_experience_impact=self._calculate_ux_impact(auth_stats.jwt_avg_time, self.jwt_target_ms),
                business_risk_score=self._calculate_business_risk(auth_stats.jwt_avg_time, self.jwt_target_ms)
            )
            metrics.append(jwt_metric)
            
            # RBAC Evaluation Time
            rbac_metric = SecurityPerformanceMetric(
                metric_type=SecurityPerformanceMetricType.RBAC_EVALUATION_TIME,
                value=auth_stats.rbac_avg_time,
                timestamp=datetime.now(),
                target_value=self.rbac_target_ms,
                threshold_warning=self.rbac_target_ms * 0.8,
                threshold_critical=self.rbac_target_ms * 1.2,
                unit="ms",
                description="Average RBAC evaluation time",
                request_volume=auth_stats.total_requests,
                concurrent_users=current_load['concurrent_users'],
                security_level=security_level,
                threat_level=threat_level,
                user_experience_impact=self._calculate_ux_impact(auth_stats.rbac_avg_time, self.rbac_target_ms),
                business_risk_score=self._calculate_business_risk(auth_stats.rbac_avg_time, self.rbac_target_ms)
            )
            metrics.append(rbac_metric)
            
            # Combined Auth Time
            combined_metric = SecurityPerformanceMetric(
                metric_type=SecurityPerformanceMetricType.COMBINED_AUTH_TIME,
                value=auth_stats.avg_total_time,
                timestamp=datetime.now(),
                target_value=self.sla_target_ms,
                threshold_warning=self.sla_target_ms * 0.8,
                threshold_critical=self.sla_target_ms * 1.2,
                unit="ms",
                description="Combined authentication/authorization time",
                request_volume=auth_stats.total_requests,
                concurrent_users=current_load['concurrent_users'],
                security_level=security_level,
                threat_level=threat_level,
                user_experience_impact=self._calculate_ux_impact(auth_stats.avg_total_time, self.sla_target_ms),
                business_risk_score=self._calculate_business_risk(auth_stats.avg_total_time, self.sla_target_ms)
            )
            metrics.append(combined_metric)
            
            # SLA Compliance Rate
            sla_metric = SecurityPerformanceMetric(
                metric_type=SecurityPerformanceMetricType.SLA_COMPLIANCE_RATE,
                value=auth_stats.sla_compliance_rate,
                timestamp=datetime.now(),
                target_value=99.0,
                threshold_warning=95.0,
                threshold_critical=90.0,
                unit="%",
                description="SLA compliance rate (<150ms)",
                request_volume=auth_stats.total_requests,
                concurrent_users=current_load['concurrent_users'],
                security_level=security_level,
                threat_level=threat_level,
                user_experience_impact=self._calculate_ux_impact(100 - auth_stats.sla_compliance_rate, 1.0),
                business_risk_score=self._calculate_business_risk(100 - auth_stats.sla_compliance_rate, 1.0)
            )
            metrics.append(sla_metric)
            
            # Security Throughput
            throughput_rps = auth_stats.total_requests / 1.0 if auth_stats.total_requests > 0 else 0  # per hour to RPS approximation
            throughput_metric = SecurityPerformanceMetric(
                metric_type=SecurityPerformanceMetricType.SECURITY_THROUGHPUT,
                value=throughput_rps,
                timestamp=datetime.now(),
                target_value=self.throughput_target_rps,
                threshold_warning=self.throughput_target_rps * 0.7,
                threshold_critical=self.throughput_target_rps * 0.5,
                unit="req/s",
                description="Security system throughput",
                request_volume=auth_stats.total_requests,
                concurrent_users=current_load['concurrent_users'],
                security_level=security_level,
                threat_level=threat_level,
                user_experience_impact=self._calculate_throughput_ux_impact(throughput_rps),
                business_risk_score=self._calculate_throughput_business_risk(throughput_rps)
            )
            metrics.append(throughput_metric)
            
            # Auth Success Rate
            auth_success_rate = (auth_stats.successful_requests / auth_stats.total_requests * 100) if auth_stats.total_requests > 0 else 100
            success_metric = SecurityPerformanceMetric(
                metric_type=SecurityPerformanceMetricType.AUTH_SUCCESS_RATE,
                value=auth_success_rate,
                timestamp=datetime.now(),
                target_value=99.5,
                threshold_warning=98.0,
                threshold_critical=95.0,
                unit="%",
                description="Authentication success rate",
                request_volume=auth_stats.total_requests,
                concurrent_users=current_load['concurrent_users'],
                security_level=security_level,
                threat_level=threat_level,
                user_experience_impact=self._calculate_ux_impact(100 - auth_success_rate, 0.5),
                business_risk_score=self._calculate_business_risk(100 - auth_success_rate, 0.5)
            )
            metrics.append(success_metric)
            
            # Store metrics
            self._store_metrics(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting unified security metrics: {e}")
            return []
    
    def _calculate_current_load(self) -> Dict[str, Any]:
        """Calculate current system load indicators"""
        # This would integrate with system monitoring
        # For now, return simulated values
        return {
            'concurrent_users': 150,
            'requests_per_second': 45.2,
            'cpu_usage': 35.5,
            'memory_usage': 62.1
        }
    
    def _assess_security_level(self, auth_stats: AuthPerformanceStats) -> str:
        """Assess current security level based on auth statistics"""
        if auth_stats.high_risk_requests > 5:
            return "high"
        elif auth_stats.suspicious_activity_count > 2:
            return "medium"
        else:
            return "low"
    
    def _assess_threat_level(self, auth_stats: AuthPerformanceStats) -> str:
        """Assess current threat level"""
        if auth_stats.high_risk_requests > 10:
            return "critical"
        elif auth_stats.high_risk_requests > 5:
            return "high"
        elif auth_stats.suspicious_activity_count > 0:
            return "medium"
        else:
            return "low"
    
    def _calculate_ux_impact(self, actual_value: float, target_value: float) -> float:
        """Calculate user experience impact (0-1 scale)"""
        if actual_value <= target_value:
            return 0.0
        
        # Exponential impact - performance degradation hurts UX exponentially
        impact_factor = (actual_value - target_value) / target_value
        return min(1.0, impact_factor ** 0.5)
    
    def _calculate_business_risk(self, actual_value: float, target_value: float) -> float:
        """Calculate business risk score (0-1 scale)"""
        if actual_value <= target_value:
            return 0.0
        
        # Business risk increases more gradually than UX impact
        risk_factor = (actual_value - target_value) / target_value
        return min(1.0, risk_factor * 0.3)
    
    def _calculate_throughput_ux_impact(self, throughput_rps: float) -> float:
        """Calculate UX impact for throughput metrics"""
        if throughput_rps >= self.throughput_target_rps:
            return 0.0
        
        impact_factor = (self.throughput_target_rps - throughput_rps) / self.throughput_target_rps
        return min(1.0, impact_factor * 0.8)
    
    def _calculate_throughput_business_risk(self, throughput_rps: float) -> float:
        """Calculate business risk for throughput metrics"""
        if throughput_rps >= self.throughput_target_rps * 0.8:
            return 0.0
        
        risk_factor = (self.throughput_target_rps - throughput_rps) / self.throughput_target_rps
        return min(1.0, risk_factor * 0.6)
    
    def _store_metrics(self, metrics: List[SecurityPerformanceMetric]):
        """Store metrics in database"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                for metric in metrics:
                    conn.execute('''
                        INSERT INTO security_performance_metrics (
                            metric_type, value, timestamp, target_value, threshold_warning,
                            threshold_critical, unit, description, request_volume, concurrent_users,
                            security_level, threat_level, user_experience_impact, business_risk_score
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        metric.metric_type.value,
                        metric.value,
                        metric.timestamp.isoformat(),
                        metric.target_value,
                        metric.threshold_warning,
                        metric.threshold_critical,
                        metric.unit,
                        metric.description,
                        metric.request_volume,
                        metric.concurrent_users,
                        metric.security_level,
                        metric.threat_level,
                        metric.user_experience_impact,
                        metric.business_risk_score
                    ))
    
    def generate_unified_dashboard(self) -> UnifiedSecurityDashboard:
        """Generate unified security dashboard data"""
        try:
            # Get latest metrics
            auth_stats = self.auth_monitor.get_performance_stats(hours=1)
            current_load = self._calculate_current_load()
            
            # Calculate user satisfaction (inverse of UX impact)
            avg_ux_impact = self._calculate_ux_impact(auth_stats.avg_total_time, self.sla_target_ms)
            user_satisfaction = max(0.0, 1.0 - avg_ux_impact)
            
            # Calculate business continuity score
            business_continuity = self._calculate_business_continuity_score(auth_stats)
            
            dashboard = UnifiedSecurityDashboard(
                timestamp=datetime.now(),
                jwt_avg_time=auth_stats.jwt_avg_time,
                rbac_avg_time=auth_stats.rbac_avg_time,
                total_auth_time=auth_stats.avg_total_time,
                sla_compliance_rate=auth_stats.sla_compliance_rate,
                requests_per_second=current_load['requests_per_second'],
                concurrent_sessions=current_load['concurrent_users'],
                auth_success_rate=(auth_stats.successful_requests / auth_stats.total_requests * 100) if auth_stats.total_requests > 0 else 100,
                security_incidents=auth_stats.high_risk_requests,
                threat_level=self._assess_threat_level(auth_stats),
                user_satisfaction_score=user_satisfaction * 100,
                business_continuity_score=business_continuity * 100
            )
            
            # Store dashboard snapshot
            self._store_dashboard_snapshot(dashboard)
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Error generating unified dashboard: {e}")
            return UnifiedSecurityDashboard(
                timestamp=datetime.now(),
                jwt_avg_time=0.0,
                rbac_avg_time=0.0,
                total_auth_time=0.0,
                sla_compliance_rate=0.0,
                requests_per_second=0.0,
                concurrent_sessions=0,
                auth_success_rate=0.0,
                security_incidents=0,
                threat_level="unknown",
                user_satisfaction_score=0.0,
                business_continuity_score=0.0
            )
    
    def _calculate_business_continuity_score(self, auth_stats: AuthPerformanceStats) -> float:
        """Calculate business continuity score based on auth performance"""
        factors = []
        
        # SLA compliance factor
        factors.append(auth_stats.sla_compliance_rate / 100.0)
        
        # Success rate factor
        success_rate = (auth_stats.successful_requests / auth_stats.total_requests) if auth_stats.total_requests > 0 else 1.0
        factors.append(success_rate)
        
        # Security incident factor
        incident_factor = max(0.0, 1.0 - (auth_stats.high_risk_requests / 10.0))
        factors.append(incident_factor)
        
        # Average the factors
        return sum(factors) / len(factors)
    
    def _store_dashboard_snapshot(self, dashboard: UnifiedSecurityDashboard):
        """Store dashboard snapshot in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO security_dashboard_snapshots (
                    timestamp, jwt_avg_time, rbac_avg_time, total_auth_time,
                    sla_compliance_rate, requests_per_second, concurrent_sessions,
                    auth_success_rate, security_incidents, threat_level,
                    user_satisfaction_score, business_continuity_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                dashboard.timestamp.isoformat(),
                dashboard.jwt_avg_time,
                dashboard.rbac_avg_time,
                dashboard.total_auth_time,
                dashboard.sla_compliance_rate,
                dashboard.requests_per_second,
                dashboard.concurrent_sessions,
                dashboard.auth_success_rate,
                dashboard.security_incidents,
                dashboard.threat_level,
                dashboard.user_satisfaction_score,
                dashboard.business_continuity_score
            ))
    
    def get_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance trends over time"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            # Get JWT validation trends
            cursor = conn.execute('''
                SELECT timestamp, value FROM security_performance_metrics
                WHERE metric_type = 'jwt_validation_time' AND timestamp >= ?
                ORDER BY timestamp
            ''', (start_time.isoformat(),))
            jwt_trend = [(row[0], row[1]) for row in cursor.fetchall()]
            
            # Get RBAC evaluation trends
            cursor = conn.execute('''
                SELECT timestamp, value FROM security_performance_metrics
                WHERE metric_type = 'rbac_evaluation_time' AND timestamp >= ?
                ORDER BY timestamp
            ''', (start_time.isoformat(),))
            rbac_trend = [(row[0], row[1]) for row in cursor.fetchall()]
            
            # Get combined auth time trends
            cursor = conn.execute('''
                SELECT timestamp, value FROM security_performance_metrics
                WHERE metric_type = 'combined_auth_time' AND timestamp >= ?
                ORDER BY timestamp
            ''', (start_time.isoformat(),))
            combined_trend = [(row[0], row[1]) for row in cursor.fetchall()]
            
            # Get SLA compliance trends
            cursor = conn.execute('''
                SELECT timestamp, value FROM security_performance_metrics
                WHERE metric_type = 'sla_compliance_rate' AND timestamp >= ?
                ORDER BY timestamp
            ''', (start_time.isoformat(),))
            sla_trend = [(row[0], row[1]) for row in cursor.fetchall()]
            
            return {
                'period_hours': hours,
                'jwt_validation_trend': jwt_trend,
                'rbac_evaluation_trend': rbac_trend,
                'combined_auth_trend': combined_trend,
                'sla_compliance_trend': sla_trend,
                'analysis': self._analyze_trends(jwt_trend, rbac_trend, combined_trend, sla_trend)
            }
    
    def _analyze_trends(self, jwt_trend: List[Tuple], rbac_trend: List[Tuple], 
                       combined_trend: List[Tuple], sla_trend: List[Tuple]) -> Dict[str, Any]:
        """Analyze performance trends"""
        analysis = {
            'jwt_trend_direction': 'stable',
            'rbac_trend_direction': 'stable',
            'combined_trend_direction': 'stable',
            'sla_trend_direction': 'stable',
            'alerts': []
        }
        
        # Analyze JWT trend
        if len(jwt_trend) >= 2:
            jwt_values = [t[1] for t in jwt_trend]
            if len(jwt_values) >= 3:
                recent_avg = statistics.mean(jwt_values[-3:])
                earlier_avg = statistics.mean(jwt_values[:3])
                
                if recent_avg > earlier_avg * 1.1:
                    analysis['jwt_trend_direction'] = 'degrading'
                    analysis['alerts'].append('JWT validation performance degrading')
                elif recent_avg < earlier_avg * 0.9:
                    analysis['jwt_trend_direction'] = 'improving'
        
        # Analyze RBAC trend
        if len(rbac_trend) >= 2:
            rbac_values = [t[1] for t in rbac_trend]
            if len(rbac_values) >= 3:
                recent_avg = statistics.mean(rbac_values[-3:])
                earlier_avg = statistics.mean(rbac_values[:3])
                
                if recent_avg > earlier_avg * 1.1:
                    analysis['rbac_trend_direction'] = 'degrading'
                    analysis['alerts'].append('RBAC evaluation performance degrading')
                elif recent_avg < earlier_avg * 0.9:
                    analysis['rbac_trend_direction'] = 'improving'
        
        # Analyze combined trend
        if len(combined_trend) >= 2:
            combined_values = [t[1] for t in combined_trend]
            if len(combined_values) >= 3:
                recent_avg = statistics.mean(combined_values[-3:])
                earlier_avg = statistics.mean(combined_values[:3])
                
                if recent_avg > earlier_avg * 1.1:
                    analysis['combined_trend_direction'] = 'degrading'
                    analysis['alerts'].append('Overall auth performance degrading')
                elif recent_avg < earlier_avg * 0.9:
                    analysis['combined_trend_direction'] = 'improving'
        
        # Analyze SLA trend
        if len(sla_trend) >= 2:
            sla_values = [t[1] for t in sla_trend]
            if len(sla_values) >= 3:
                recent_avg = statistics.mean(sla_values[-3:])
                
                if recent_avg < 95.0:
                    analysis['sla_trend_direction'] = 'degrading'
                    analysis['alerts'].append('SLA compliance below target')
        
        return analysis
    
    def _start_metrics_collection(self):
        """Start background metrics collection"""
        def metrics_worker():
            while True:
                try:
                    # Collect unified metrics
                    metrics = self.collect_unified_metrics()
                    
                    # Generate dashboard
                    dashboard = self.generate_unified_dashboard()
                    
                    # Log summary
                    logger.info(f"Unified Security Metrics: Auth={dashboard.total_auth_time:.1f}ms, "
                              f"SLA={dashboard.sla_compliance_rate:.1f}%, "
                              f"Success={dashboard.auth_success_rate:.1f}%")
                    
                    # Check for alerts
                    for metric in metrics:
                        if metric.get_status() == "critical":
                            logger.critical(f"CRITICAL SECURITY METRIC: {metric.metric_type.value} = {metric.value} {metric.unit}")
                        elif metric.get_status() == "warning":
                            logger.warning(f"WARNING SECURITY METRIC: {metric.metric_type.value} = {metric.value} {metric.unit}")
                    
                    # Sleep for 1 minute
                    time.sleep(60)
                    
                except Exception as e:
                    logger.error(f"Metrics collection error: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=metrics_worker, daemon=True)
        thread.start()
        logger.info("Unified security metrics collection started")


# Global unified security metrics instance
unified_security_metrics = UnifiedSecurityMetrics()


if __name__ == "__main__":
    # Test unified security metrics
    print("Unified Security Metrics Test")
    print("=" * 50)
    
    # Collect metrics
    metrics = unified_security_metrics.collect_unified_metrics()
    print(f"Collected {len(metrics)} security performance metrics")
    
    for metric in metrics:
        print(f"- {metric.metric_type.value}: {metric.value} {metric.unit} ({metric.get_status()})")
    
    # Generate dashboard
    dashboard = unified_security_metrics.generate_unified_dashboard()
    print(f"\nUnified Security Dashboard:")
    print(f"- Total Auth Time: {dashboard.total_auth_time:.1f}ms")
    print(f"- SLA Compliance: {dashboard.sla_compliance_rate:.1f}%")
    print(f"- User Satisfaction: {dashboard.user_satisfaction_score:.1f}%")
    print(f"- Business Continuity: {dashboard.business_continuity_score:.1f}%")
    
    # Get performance trends
    trends = unified_security_metrics.get_performance_trends(hours=1)
    print(f"\nPerformance Trends Analysis:")
    print(f"- JWT Trend: {trends['analysis']['jwt_trend_direction']}")
    print(f"- RBAC Trend: {trends['analysis']['rbac_trend_direction']}")
    print(f"- Combined Trend: {trends['analysis']['combined_trend_direction']}")
    
    if trends['analysis']['alerts']:
        print(f"- Alerts: {trends['analysis']['alerts']}")
    
    print("\nUnified security metrics ready for production monitoring!")