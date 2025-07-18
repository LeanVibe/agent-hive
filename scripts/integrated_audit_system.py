#!/usr/bin/env python3
"""
Integrated Audit System - Security + Infrastructure Coordination
LeanVibe Agent Hive - Unified Audit Trail for PostgreSQL + RBAC Integration

Comprehensive audit integration:
- PostgreSQL authentication audit logging
- RBAC authorization audit trails
- Cross-system event correlation
- Unified audit dashboard
- Compliance-ready audit streams
- Real-time audit event processing
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
import hashlib
import sqlite3

# Import audit logging components
from audit_logging_system import AuditLogger, AuditEvent, AuditEventType, AuditSeverity
from auth_pipeline_monitor import AuthPipelineMonitor, AuthPipelineMetrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntegratedAuditEventType(Enum):
    """Integrated audit event types for cross-system correlation"""
    JWT_VALIDATION = "jwt_validation"
    POSTGRESQL_AUTH = "postgresql_auth"
    RBAC_EVALUATION = "rbac_evaluation"
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_DENY = "permission_deny"
    RESOURCE_ACCESS = "resource_access"
    SECURITY_INCIDENT = "security_incident"
    PERFORMANCE_ALERT = "performance_alert"
    COMPLIANCE_CHECK = "compliance_check"
    AUDIT_CORRELATION = "audit_correlation"


@dataclass
class IntegratedAuditEvent:
    """Integrated audit event with cross-system correlation"""
    event_id: str
    timestamp: datetime
    event_type: IntegratedAuditEventType
    severity: AuditSeverity
    
    # Core authentication/authorization context
    user_id: str
    session_id: str
    resource: str
    action: str
    outcome: str
    
    # System correlation
    jwt_event_id: Optional[str] = None
    postgresql_event_id: Optional[str] = None
    rbac_event_id: Optional[str] = None
    
    # Performance context
    total_time: Optional[float] = None
    stage_times: Optional[Dict[str, float]] = None
    
    # Security context
    risk_level: str = "low"
    threat_indicators: List[str] = None
    
    # Compliance context
    compliance_tags: List[str] = None
    regulatory_impact: Optional[str] = None
    
    # Additional context
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.threat_indicators is None:
            self.threat_indicators = []
        if self.compliance_tags is None:
            self.compliance_tags = []
        if self.details is None:
            self.details = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        return data


@dataclass
class AuditCorrelationRule:
    """Rule for correlating audit events across systems"""
    rule_id: str
    name: str
    description: str
    
    # Matching criteria
    time_window_seconds: int
    matching_fields: List[str]  # Fields that must match (e.g., user_id, session_id)
    
    # Event types to correlate
    primary_event_type: IntegratedAuditEventType
    secondary_event_types: List[IntegratedAuditEventType]
    
    # Correlation actions
    create_summary_event: bool = True
    alert_on_anomaly: bool = True
    compliance_reporting: bool = True
    
    # Thresholds
    max_correlation_delay: int = 5000  # milliseconds
    anomaly_threshold: float = 0.8  # correlation score threshold


class IntegratedAuditSystem:
    """Integrated audit system for Security + Infrastructure coordination"""
    
    def __init__(self):
        self.base_audit_logger = AuditLogger()
        self.auth_monitor = AuthPipelineMonitor()
        self.db_path = "integrated_audit.db"
        self.lock = threading.Lock()
        
        # Correlation rules
        self.correlation_rules = self._load_correlation_rules()
        
        # Event correlation cache
        self.correlation_cache = {}
        self.cache_expiry = 300  # 5 minutes
        
        # Initialize database
        self._init_database()
        
        # Start correlation engine
        self._start_correlation_engine()
    
    def _init_database(self):
        """Initialize integrated audit database"""
        with sqlite3.connect(self.db_path) as conn:
            # Integrated audit events table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS integrated_audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    action TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    jwt_event_id TEXT,
                    postgresql_event_id TEXT,
                    rbac_event_id TEXT,
                    total_time REAL,
                    stage_times TEXT,
                    risk_level TEXT NOT NULL,
                    threat_indicators TEXT,
                    compliance_tags TEXT,
                    regulatory_impact TEXT,
                    details TEXT
                )
            ''')
            
            # Event correlations table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS event_correlations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    correlation_id TEXT UNIQUE NOT NULL,
                    primary_event_id TEXT NOT NULL,
                    secondary_event_ids TEXT NOT NULL,
                    correlation_type TEXT NOT NULL,
                    correlation_score REAL NOT NULL,
                    time_span_ms INTEGER NOT NULL,
                    anomaly_detected BOOLEAN NOT NULL,
                    created_at TEXT NOT NULL,
                    details TEXT
                )
            ''')
            
            # Audit correlation rules table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS correlation_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    time_window_seconds INTEGER NOT NULL,
                    matching_fields TEXT NOT NULL,
                    primary_event_type TEXT NOT NULL,
                    secondary_event_types TEXT NOT NULL,
                    create_summary_event BOOLEAN NOT NULL,
                    alert_on_anomaly BOOLEAN NOT NULL,
                    compliance_reporting BOOLEAN NOT NULL,
                    max_correlation_delay INTEGER NOT NULL,
                    anomaly_threshold REAL NOT NULL,
                    enabled BOOLEAN NOT NULL DEFAULT 1
                )
            ''')
            
            # Create indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_integrated_timestamp ON integrated_audit_events(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_integrated_user_id ON integrated_audit_events(user_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_integrated_session_id ON integrated_audit_events(session_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_integrated_event_type ON integrated_audit_events(event_type)')
    
    def _load_correlation_rules(self) -> List[AuditCorrelationRule]:
        """Load audit correlation rules"""
        rules = []
        
        # Authentication flow correlation
        auth_flow_rule = AuditCorrelationRule(
            rule_id="auth_flow_correlation",
            name="Authentication Flow Correlation",
            description="Correlate JWT validation, PostgreSQL auth, and RBAC evaluation",
            time_window_seconds=10,
            matching_fields=["user_id", "session_id"],
            primary_event_type=IntegratedAuditEventType.JWT_VALIDATION,
            secondary_event_types=[
                IntegratedAuditEventType.POSTGRESQL_AUTH,
                IntegratedAuditEventType.RBAC_EVALUATION
            ],
            create_summary_event=True,
            alert_on_anomaly=True,
            compliance_reporting=True,
            max_correlation_delay=5000,
            anomaly_threshold=0.8
        )
        rules.append(auth_flow_rule)
        
        # Permission evaluation correlation
        permission_rule = AuditCorrelationRule(
            rule_id="permission_evaluation_correlation",
            name="Permission Evaluation Correlation",
            description="Correlate RBAC evaluation with permission grants/denies",
            time_window_seconds=5,
            matching_fields=["user_id", "resource", "action"],
            primary_event_type=IntegratedAuditEventType.RBAC_EVALUATION,
            secondary_event_types=[
                IntegratedAuditEventType.PERMISSION_GRANT,
                IntegratedAuditEventType.PERMISSION_DENY
            ],
            create_summary_event=True,
            alert_on_anomaly=True,
            compliance_reporting=True,
            max_correlation_delay=2000,
            anomaly_threshold=0.9
        )
        rules.append(permission_rule)
        
        # Security incident correlation
        security_incident_rule = AuditCorrelationRule(
            rule_id="security_incident_correlation",
            name="Security Incident Correlation",
            description="Correlate security incidents with auth/authz events",
            time_window_seconds=30,
            matching_fields=["user_id"],
            primary_event_type=IntegratedAuditEventType.SECURITY_INCIDENT,
            secondary_event_types=[
                IntegratedAuditEventType.JWT_VALIDATION,
                IntegratedAuditEventType.POSTGRESQL_AUTH,
                IntegratedAuditEventType.RBAC_EVALUATION
            ],
            create_summary_event=True,
            alert_on_anomaly=True,
            compliance_reporting=True,
            max_correlation_delay=10000,
            anomaly_threshold=0.7
        )
        rules.append(security_incident_rule)
        
        return rules
    
    def log_integrated_event(self, event: IntegratedAuditEvent) -> bool:
        """Log integrated audit event"""
        try:
            with self.lock:
                # Store in database
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT INTO integrated_audit_events (
                            event_id, timestamp, event_type, severity, user_id, session_id,
                            resource, action, outcome, jwt_event_id, postgresql_event_id,
                            rbac_event_id, total_time, stage_times, risk_level,
                            threat_indicators, compliance_tags, regulatory_impact, details
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        event.event_id,
                        event.timestamp.isoformat(),
                        event.event_type.value,
                        event.severity.value,
                        event.user_id,
                        event.session_id,
                        event.resource,
                        event.action,
                        event.outcome,
                        event.jwt_event_id,
                        event.postgresql_event_id,
                        event.rbac_event_id,
                        event.total_time,
                        json.dumps(event.stage_times) if event.stage_times else None,
                        event.risk_level,
                        json.dumps(event.threat_indicators),
                        json.dumps(event.compliance_tags),
                        event.regulatory_impact,
                        json.dumps(event.details)
                    ))
                
                # Log to base audit system
                base_audit_event = AuditEvent(
                    event_id=event.event_id,
                    timestamp=event.timestamp,
                    event_type=AuditEventType.SECURITY_EVENT,
                    severity=event.severity,
                    actor_id=event.user_id,
                    actor_type="user",
                    target_resource=event.resource,
                    action=event.action,
                    outcome=event.outcome,
                    session_id=event.session_id,
                    details=event.details,
                    risk_indicators=event.threat_indicators,
                    compliance_tags=event.compliance_tags
                )
                self.base_audit_logger.log_event(base_audit_event)
                
                # Add to correlation cache
                self._add_to_correlation_cache(event)
                
                logger.debug(f"Logged integrated audit event: {event.event_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to log integrated audit event: {e}")
            return False
    
    def correlate_auth_pipeline_event(self, pipeline_metrics: AuthPipelineMetrics):
        """Correlate auth pipeline event with individual stage events"""
        try:
            # Create JWT validation event
            jwt_event = IntegratedAuditEvent(
                event_id=f"jwt_{pipeline_metrics.request_id}",
                timestamp=pipeline_metrics.timestamp,
                event_type=IntegratedAuditEventType.JWT_VALIDATION,
                severity=AuditSeverity.INFO if pipeline_metrics.jwt_result.value == "success" else AuditSeverity.WARNING,
                user_id=pipeline_metrics.user_id,
                session_id=pipeline_metrics.request_id,
                resource=pipeline_metrics.resource,
                action=pipeline_metrics.action,
                outcome=pipeline_metrics.jwt_result.value,
                total_time=pipeline_metrics.jwt_time,
                stage_times={"jwt_validation": pipeline_metrics.jwt_time},
                risk_level=self._calculate_risk_level(pipeline_metrics),
                threat_indicators=pipeline_metrics.suspicious_patterns,
                compliance_tags=["jwt", "authentication", "security"],
                details={"stage": "jwt_validation", "parent_request": pipeline_metrics.request_id}
            )
            self.log_integrated_event(jwt_event)
            
            # Create PostgreSQL auth event
            postgresql_event = IntegratedAuditEvent(
                event_id=f"postgresql_{pipeline_metrics.request_id}",
                timestamp=pipeline_metrics.timestamp + timedelta(milliseconds=pipeline_metrics.jwt_time),
                event_type=IntegratedAuditEventType.POSTGRESQL_AUTH,
                severity=AuditSeverity.INFO if pipeline_metrics.postgresql_result.value == "success" else AuditSeverity.ERROR,
                user_id=pipeline_metrics.user_id,
                session_id=pipeline_metrics.request_id,
                resource=pipeline_metrics.resource,
                action=pipeline_metrics.action,
                outcome=pipeline_metrics.postgresql_result.value,
                jwt_event_id=jwt_event.event_id,
                total_time=pipeline_metrics.postgresql_time,
                stage_times={"postgresql_auth": pipeline_metrics.postgresql_time},
                risk_level=self._calculate_risk_level(pipeline_metrics),
                threat_indicators=pipeline_metrics.suspicious_patterns,
                compliance_tags=["postgresql", "authentication", "database"],
                details={"stage": "postgresql_auth", "parent_request": pipeline_metrics.request_id}
            )
            self.log_integrated_event(postgresql_event)
            
            # Create RBAC evaluation event
            rbac_event = IntegratedAuditEvent(
                event_id=f"rbac_{pipeline_metrics.request_id}",
                timestamp=pipeline_metrics.timestamp + timedelta(milliseconds=pipeline_metrics.jwt_time + pipeline_metrics.postgresql_time),
                event_type=IntegratedAuditEventType.RBAC_EVALUATION,
                severity=AuditSeverity.INFO if pipeline_metrics.rbac_result.value == "success" else AuditSeverity.WARNING,
                user_id=pipeline_metrics.user_id,
                session_id=pipeline_metrics.request_id,
                resource=pipeline_metrics.resource,
                action=pipeline_metrics.action,
                outcome=pipeline_metrics.rbac_result.value,
                jwt_event_id=jwt_event.event_id,
                postgresql_event_id=postgresql_event.event_id,
                total_time=pipeline_metrics.rbac_time,
                stage_times={"rbac_evaluation": pipeline_metrics.rbac_time},
                risk_level=self._calculate_risk_level(pipeline_metrics),
                threat_indicators=pipeline_metrics.suspicious_patterns,
                compliance_tags=["rbac", "authorization", "permissions"],
                details={"stage": "rbac_evaluation", "parent_request": pipeline_metrics.request_id}
            )
            self.log_integrated_event(rbac_event)
            
            # Create summary correlation event
            summary_event = IntegratedAuditEvent(
                event_id=f"auth_summary_{pipeline_metrics.request_id}",
                timestamp=pipeline_metrics.timestamp + timedelta(milliseconds=pipeline_metrics.total_time),
                event_type=IntegratedAuditEventType.AUDIT_CORRELATION,
                severity=AuditSeverity.INFO if pipeline_metrics.final_result.value == "success" else AuditSeverity.ERROR,
                user_id=pipeline_metrics.user_id,
                session_id=pipeline_metrics.request_id,
                resource=pipeline_metrics.resource,
                action=pipeline_metrics.action,
                outcome=pipeline_metrics.final_result.value,
                jwt_event_id=jwt_event.event_id,
                postgresql_event_id=postgresql_event.event_id,
                rbac_event_id=rbac_event.event_id,
                total_time=pipeline_metrics.total_time,
                stage_times={
                    "jwt_validation": pipeline_metrics.jwt_time,
                    "postgresql_auth": pipeline_metrics.postgresql_time,
                    "rbac_evaluation": pipeline_metrics.rbac_time,
                    "permission_check": pipeline_metrics.permission_time
                },
                risk_level=self._calculate_risk_level(pipeline_metrics),
                threat_indicators=pipeline_metrics.suspicious_patterns,
                compliance_tags=["authentication", "authorization", "audit_trail"],
                regulatory_impact="gdpr" if pipeline_metrics.exceeded_sla else None,
                details={
                    "correlation_type": "auth_pipeline",
                    "exceeded_sla": pipeline_metrics.exceeded_sla,
                    "critical_path": pipeline_metrics.critical_path,
                    "risk_score": pipeline_metrics.risk_score
                }
            )
            self.log_integrated_event(summary_event)
            
            logger.info(f"Correlated auth pipeline event: {pipeline_metrics.request_id}")
            
        except Exception as e:
            logger.error(f"Error correlating auth pipeline event: {e}")
    
    def _calculate_risk_level(self, metrics: AuthPipelineMetrics) -> str:
        """Calculate risk level based on pipeline metrics"""
        if metrics.risk_score > 0.8:
            return "critical"
        elif metrics.risk_score > 0.6:
            return "high"
        elif metrics.risk_score > 0.3:
            return "medium"
        else:
            return "low"
    
    def _add_to_correlation_cache(self, event: IntegratedAuditEvent):
        """Add event to correlation cache for real-time correlation"""
        cache_key = f"{event.user_id}_{event.session_id}"
        
        if cache_key not in self.correlation_cache:
            self.correlation_cache[cache_key] = []
        
        self.correlation_cache[cache_key].append({
            'event': event,
            'timestamp': time.time()
        })
        
        # Clean up old entries
        current_time = time.time()
        self.correlation_cache[cache_key] = [
            entry for entry in self.correlation_cache[cache_key]
            if current_time - entry['timestamp'] < self.cache_expiry
        ]
    
    def get_correlated_events(self, user_id: str, session_id: str, hours: int = 1) -> List[IntegratedAuditEvent]:
        """Get correlated events for a user session"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        events = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT * FROM integrated_audit_events
                WHERE user_id = ? AND session_id = ?
                AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp
            ''', (user_id, session_id, start_time.isoformat(), end_time.isoformat()))
            
            for row in cursor.fetchall():
                event = IntegratedAuditEvent(
                    event_id=row[1],
                    timestamp=datetime.fromisoformat(row[2]),
                    event_type=IntegratedAuditEventType(row[3]),
                    severity=AuditSeverity(row[4]),
                    user_id=row[5],
                    session_id=row[6],
                    resource=row[7],
                    action=row[8],
                    outcome=row[9],
                    jwt_event_id=row[10],
                    postgresql_event_id=row[11],
                    rbac_event_id=row[12],
                    total_time=row[13],
                    stage_times=json.loads(row[14]) if row[14] else None,
                    risk_level=row[15],
                    threat_indicators=json.loads(row[16]) if row[16] else [],
                    compliance_tags=json.loads(row[17]) if row[17] else [],
                    regulatory_impact=row[18],
                    details=json.loads(row[19]) if row[19] else {}
                )
                events.append(event)
        
        return events
    
    def get_audit_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get integrated audit statistics"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            # Total events
            cursor = conn.execute('''
                SELECT COUNT(*) FROM integrated_audit_events
                WHERE timestamp >= ? AND timestamp <= ?
            ''', (start_time.isoformat(), end_time.isoformat()))
            total_events = cursor.fetchone()[0]
            
            # Events by type
            cursor = conn.execute('''
                SELECT event_type, COUNT(*) 
                FROM integrated_audit_events
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY event_type
            ''', (start_time.isoformat(), end_time.isoformat()))
            events_by_type = dict(cursor.fetchall())
            
            # Events by outcome
            cursor = conn.execute('''
                SELECT outcome, COUNT(*) 
                FROM integrated_audit_events
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY outcome
            ''', (start_time.isoformat(), end_time.isoformat()))
            events_by_outcome = dict(cursor.fetchall())
            
            # Average processing times
            cursor = conn.execute('''
                SELECT AVG(total_time) as avg_time,
                       MIN(total_time) as min_time,
                       MAX(total_time) as max_time
                FROM integrated_audit_events
                WHERE timestamp >= ? AND timestamp <= ?
                AND total_time IS NOT NULL
            ''', (start_time.isoformat(), end_time.isoformat()))
            time_stats = cursor.fetchone()
            
            # High-risk events
            cursor = conn.execute('''
                SELECT COUNT(*) FROM integrated_audit_events
                WHERE timestamp >= ? AND timestamp <= ?
                AND risk_level IN ('high', 'critical')
            ''', (start_time.isoformat(), end_time.isoformat()))
            high_risk_events = cursor.fetchone()[0]
            
            # Correlations
            cursor = conn.execute('''
                SELECT COUNT(*) FROM event_correlations
                WHERE created_at >= ?
            ''', (start_time.isoformat(),))
            correlations_count = cursor.fetchone()[0]
            
            return {
                'period_hours': hours,
                'total_events': total_events,
                'events_by_type': events_by_type,
                'events_by_outcome': events_by_outcome,
                'processing_time_stats': {
                    'average_ms': time_stats[0] or 0,
                    'min_ms': time_stats[1] or 0,
                    'max_ms': time_stats[2] or 0
                },
                'high_risk_events': high_risk_events,
                'correlations_created': correlations_count,
                'generated_at': datetime.now().isoformat()
            }
    
    def _start_correlation_engine(self):
        """Start background correlation engine"""
        def correlation_worker():
            while True:
                try:
                    # Process correlation cache
                    self._process_correlations()
                    
                    # Clean up old cache entries
                    self._cleanup_correlation_cache()
                    
                    # Sleep for 10 seconds
                    time.sleep(10)
                    
                except Exception as e:
                    logger.error(f"Correlation engine error: {e}")
                    time.sleep(30)
        
        thread = threading.Thread(target=correlation_worker, daemon=True)
        thread.start()
        logger.info("Integrated audit correlation engine started")
    
    def _process_correlations(self):
        """Process pending correlations"""
        current_time = time.time()
        
        for cache_key, cached_events in self.correlation_cache.items():
            if len(cached_events) >= 2:  # Need at least 2 events to correlate
                # Process correlations for this cache key
                self._correlate_cached_events(cache_key, cached_events)
    
    def _correlate_cached_events(self, cache_key: str, cached_events: List[Dict]):
        """Correlate cached events based on correlation rules"""
        try:
            events = [entry['event'] for entry in cached_events]
            
            for rule in self.correlation_rules:
                # Find primary events
                primary_events = [e for e in events if e.event_type == rule.primary_event_type]
                
                for primary_event in primary_events:
                    # Find secondary events within time window
                    secondary_events = []
                    for event in events:
                        if (event.event_type in rule.secondary_event_types and
                            abs((event.timestamp - primary_event.timestamp).total_seconds()) <= rule.time_window_seconds):
                            secondary_events.append(event)
                    
                    if secondary_events:
                        # Create correlation
                        correlation_id = f"corr_{rule.rule_id}_{primary_event.event_id}"
                        self._create_correlation(
                            correlation_id,
                            primary_event,
                            secondary_events,
                            rule
                        )
        
        except Exception as e:
            logger.error(f"Error correlating cached events: {e}")
    
    def _create_correlation(self, correlation_id: str, primary_event: IntegratedAuditEvent,
                           secondary_events: List[IntegratedAuditEvent], rule: AuditCorrelationRule):
        """Create event correlation"""
        try:
            # Calculate correlation score
            correlation_score = self._calculate_correlation_score(primary_event, secondary_events, rule)
            
            # Calculate time span
            all_events = [primary_event] + secondary_events
            timestamps = [e.timestamp for e in all_events]
            time_span_ms = int((max(timestamps) - min(timestamps)).total_seconds() * 1000)
            
            # Detect anomalies
            anomaly_detected = correlation_score < rule.anomaly_threshold
            
            # Store correlation
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO event_correlations (
                        correlation_id, primary_event_id, secondary_event_ids,
                        correlation_type, correlation_score, time_span_ms,
                        anomaly_detected, created_at, details
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    correlation_id,
                    primary_event.event_id,
                    json.dumps([e.event_id for e in secondary_events]),
                    rule.rule_id,
                    correlation_score,
                    time_span_ms,
                    anomaly_detected,
                    datetime.now().isoformat(),
                    json.dumps({
                        'rule_name': rule.name,
                        'event_count': len(secondary_events) + 1,
                        'anomaly_details': f"Score {correlation_score:.2f} below threshold {rule.anomaly_threshold}"
                    })
                ))
            
            # Alert on anomaly
            if anomaly_detected and rule.alert_on_anomaly:
                logger.warning(f"AUDIT CORRELATION ANOMALY: {rule.name} - Score: {correlation_score:.2f}")
            
            logger.debug(f"Created correlation: {correlation_id}")
            
        except Exception as e:
            logger.error(f"Error creating correlation: {e}")
    
    def _calculate_correlation_score(self, primary_event: IntegratedAuditEvent,
                                   secondary_events: List[IntegratedAuditEvent],
                                   rule: AuditCorrelationRule) -> float:
        """Calculate correlation score between events"""
        try:
            score = 1.0
            
            # Check timing correlation
            for event in secondary_events:
                time_diff = abs((event.timestamp - primary_event.timestamp).total_seconds() * 1000)
                if time_diff > rule.max_correlation_delay:
                    score *= 0.5  # Penalty for timing issues
            
            # Check outcome correlation
            if primary_event.outcome == "success":
                success_count = sum(1 for e in secondary_events if e.outcome == "success")
                if success_count < len(secondary_events):
                    score *= 0.7  # Penalty for inconsistent outcomes
            
            # Check risk level correlation
            if primary_event.risk_level == "high" or primary_event.risk_level == "critical":
                if any(e.risk_level in ["high", "critical"] for e in secondary_events):
                    score *= 1.1  # Bonus for consistent high risk
            
            return min(1.0, score)
            
        except Exception as e:
            logger.error(f"Error calculating correlation score: {e}")
            return 0.0
    
    def _cleanup_correlation_cache(self):
        """Clean up old correlation cache entries"""
        current_time = time.time()
        
        for cache_key in list(self.correlation_cache.keys()):
            self.correlation_cache[cache_key] = [
                entry for entry in self.correlation_cache[cache_key]
                if current_time - entry['timestamp'] < self.cache_expiry
            ]
            
            if not self.correlation_cache[cache_key]:
                del self.correlation_cache[cache_key]


# Global integrated audit system instance
integrated_audit_system = IntegratedAuditSystem()


# Integration functions for Security and Infrastructure agents
def log_jwt_validation_event(user_id: str, session_id: str, resource: str, action: str, 
                           outcome: str, processing_time: float, details: Dict[str, Any] = None):
    """Log JWT validation event - called by Security Agent"""
    event = IntegratedAuditEvent(
        event_id=f"jwt_{session_id}_{int(time.time() * 1000)}",
        timestamp=datetime.now(),
        event_type=IntegratedAuditEventType.JWT_VALIDATION,
        severity=AuditSeverity.INFO if outcome == "success" else AuditSeverity.WARNING,
        user_id=user_id,
        session_id=session_id,
        resource=resource,
        action=action,
        outcome=outcome,
        total_time=processing_time,
        compliance_tags=["jwt", "authentication"],
        details=details or {}
    )
    integrated_audit_system.log_integrated_event(event)


def log_postgresql_auth_event(user_id: str, session_id: str, resource: str, action: str,
                            outcome: str, processing_time: float, details: Dict[str, Any] = None):
    """Log PostgreSQL authentication event - called by Infrastructure Agent"""
    event = IntegratedAuditEvent(
        event_id=f"postgresql_{session_id}_{int(time.time() * 1000)}",
        timestamp=datetime.now(),
        event_type=IntegratedAuditEventType.POSTGRESQL_AUTH,
        severity=AuditSeverity.INFO if outcome == "success" else AuditSeverity.ERROR,
        user_id=user_id,
        session_id=session_id,
        resource=resource,
        action=action,
        outcome=outcome,
        total_time=processing_time,
        compliance_tags=["postgresql", "authentication"],
        details=details or {}
    )
    integrated_audit_system.log_integrated_event(event)


def log_rbac_evaluation_event(user_id: str, session_id: str, resource: str, action: str,
                            outcome: str, processing_time: float, details: Dict[str, Any] = None):
    """Log RBAC evaluation event - called by Infrastructure Agent"""
    event = IntegratedAuditEvent(
        event_id=f"rbac_{session_id}_{int(time.time() * 1000)}",
        timestamp=datetime.now(),
        event_type=IntegratedAuditEventType.RBAC_EVALUATION,
        severity=AuditSeverity.INFO if outcome == "success" else AuditSeverity.WARNING,
        user_id=user_id,
        session_id=session_id,
        resource=resource,
        action=action,
        outcome=outcome,
        total_time=processing_time,
        compliance_tags=["rbac", "authorization"],
        details=details or {}
    )
    integrated_audit_system.log_integrated_event(event)


if __name__ == "__main__":
    # Test integrated audit system
    print("Integrated Audit System Test")
    print("=" * 50)
    
    # Simulate auth pipeline correlation
    from auth_pipeline_monitor import AuthPipelineMonitor
    
    auth_monitor = AuthPipelineMonitor()
    
    # Simulate auth request
    pipeline_metrics = auth_monitor.simulate_auth_request(
        user_id="test_user",
        resource="api/secure_data",
        action="read"
    )
    
    # Correlate the pipeline event
    integrated_audit_system.correlate_auth_pipeline_event(pipeline_metrics)
    
    # Get statistics
    stats = integrated_audit_system.get_audit_statistics(hours=1)
    print(f"Audit Statistics:")
    print(f"- Total Events: {stats['total_events']}")
    print(f"- Events by Type: {stats['events_by_type']}")
    print(f"- High Risk Events: {stats['high_risk_events']}")
    print(f"- Correlations: {stats['correlations_created']}")
    
    # Get correlated events
    correlated_events = integrated_audit_system.get_correlated_events(
        user_id="test_user",
        session_id=pipeline_metrics.request_id,
        hours=1
    )
    print(f"\nCorrelated Events: {len(correlated_events)}")
    for event in correlated_events:
        print(f"- {event.event_type.value}: {event.outcome} ({event.total_time:.1f}ms)")
    
    print("\nIntegrated audit system ready for production!")