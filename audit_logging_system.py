#!/usr/bin/env python3
"""
Enhanced Audit Logging System - Security Event Capture
LeanVibe Agent Hive Foundation Epic Phase 2 - Continuous Security Monitoring

Comprehensive audit logging system with:
- Structured security event logging
- Real-time event streaming
- Compliance audit trails
- Event correlation and analysis
- Retention and archival policies
- Audit log integrity verification
"""

import json
import logging
import sqlite3
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import asyncio
from contextlib import contextmanager
import gzip
import shutil

# Import existing security framework
from security.security_manager import SecurityEvent, RiskLevel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Audit event types for comprehensive logging"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM_CHANGE = "system_change"
    SECURITY_EVENT = "security_event"
    COMPLIANCE_CHECK = "compliance_check"
    POLICY_VIOLATION = "policy_violation"
    ADMIN_ACTION = "admin_action"
    USER_ACTION = "user_action"
    AGENT_ACTION = "agent_action"
    API_CALL = "api_call"
    ERROR_EVENT = "error_event"
    PERFORMANCE_EVENT = "performance_event"


class AuditSeverity(Enum):
    """Audit event severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Comprehensive audit event structure"""
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    actor_id: str  # User, agent, or system identifier
    actor_type: str  # "user", "agent", "system"
    target_resource: str  # Resource being accessed/modified
    action: str  # Specific action performed
    outcome: str  # "success", "failure", "partial"
    session_id: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    risk_indicators: Optional[List[str]] = None
    compliance_tags: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())
    
    def compute_hash(self) -> str:
        """Compute hash for integrity verification"""
        data = self.to_dict()
        # Remove mutable fields for consistent hashing
        data.pop('details', None)
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()


@dataclass
class AuditLogEntry:
    """Audit log entry with integrity verification"""
    sequence_number: int
    event: AuditEvent
    event_hash: str
    previous_hash: Optional[str] = None
    integrity_hash: Optional[str] = None
    
    def __post_init__(self):
        """Compute integrity hash after initialization"""
        if self.integrity_hash is None:
            self.integrity_hash = self._compute_integrity_hash()
    
    def _compute_integrity_hash(self) -> str:
        """Compute integrity hash for tamper detection"""
        data = {
            'sequence_number': self.sequence_number,
            'event_hash': self.event_hash,
            'previous_hash': self.previous_hash or ""
        }
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        """Verify integrity of the log entry"""
        expected_hash = self._compute_integrity_hash()
        return self.integrity_hash == expected_hash


class AuditRetentionPolicy:
    """Audit log retention and archival policy"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.retention_days = config.get('retention_days', 2555)  # ~7 years default
        self.archive_days = config.get('archive_days', 90)  # Archive after 90 days
        self.compression_enabled = config.get('compression', True)
        self.compliance_retention = config.get('compliance_retention', {})
    
    def should_archive(self, event: AuditEvent) -> bool:
        """Check if event should be archived"""
        age_days = (datetime.now() - event.timestamp).days
        return age_days >= self.archive_days
    
    def should_delete(self, event: AuditEvent) -> bool:
        """Check if event should be deleted"""
        age_days = (datetime.now() - event.timestamp).days
        
        # Check compliance-specific retention
        for tag in event.compliance_tags or []:
            if tag in self.compliance_retention:
                retention_days = self.compliance_retention[tag]
                if age_days < retention_days:
                    return False
        
        return age_days >= self.retention_days
    
    def get_archive_path(self, event: AuditEvent) -> Path:
        """Get archive path for event"""
        base_path = Path("audit_archives")
        year_month = event.timestamp.strftime("%Y-%m")
        return base_path / year_month / f"{event.event_type.value}.json.gz"


class AuditLogger:
    """Enhanced audit logging system with security event capture"""
    
    def __init__(self, db_path: str = "audit_log.db", config: Dict[str, Any] = None):
        self.db_path = db_path
        self.config = config or {}
        self.retention_policy = AuditRetentionPolicy(self.config.get('retention', {}))
        self.lock = threading.Lock()
        self.sequence_counter = 0
        self.last_hash = None
        self.event_cache: List[AuditEvent] = []
        self.cache_size = self.config.get('cache_size', 1000)
        self.integrity_check_interval = self.config.get('integrity_check_hours', 24)
        
        # Initialize database
        self._init_database()
        
        # Load last sequence number and hash
        self._load_sequence_state()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _init_database(self):
        """Initialize audit database with comprehensive schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Main audit events table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sequence_number INTEGER UNIQUE NOT NULL,
                    event_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    actor_type TEXT NOT NULL,
                    target_resource TEXT NOT NULL,
                    action TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    session_id TEXT,
                    source_ip TEXT,
                    user_agent TEXT,
                    details TEXT,
                    risk_indicators TEXT,
                    compliance_tags TEXT,
                    event_hash TEXT NOT NULL,
                    previous_hash TEXT,
                    integrity_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Audit log integrity table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_integrity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    check_timestamp TEXT NOT NULL,
                    start_sequence INTEGER NOT NULL,
                    end_sequence INTEGER NOT NULL,
                    total_events INTEGER NOT NULL,
                    integrity_status TEXT NOT NULL,
                    hash_chain_valid BOOLEAN NOT NULL,
                    anomalies_detected INTEGER DEFAULT 0,
                    details TEXT
                )
            ''')
            
            # Audit configuration table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_event_type ON audit_events(event_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_actor_id ON audit_events(actor_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_severity ON audit_events(severity)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_outcome ON audit_events(outcome)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sequence ON audit_events(sequence_number)')
    
    def _load_sequence_state(self):
        """Load last sequence number and hash from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT sequence_number, integrity_hash 
                FROM audit_events 
                ORDER BY sequence_number DESC 
                LIMIT 1
            ''')
            result = cursor.fetchone()
            
            if result:
                self.sequence_counter = result[0]
                self.last_hash = result[1]
            else:
                self.sequence_counter = 0
                self.last_hash = None
    
    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        def background_worker():
            while True:
                try:
                    # Periodic integrity check
                    self._perform_integrity_check()
                    
                    # Retention policy enforcement
                    self._enforce_retention_policy()
                    
                    # Cache maintenance
                    self._maintain_cache()
                    
                except Exception as e:
                    logger.error(f"Background task error: {e}")
                
                # Sleep for an hour
                time.sleep(3600)
        
        thread = threading.Thread(target=background_worker, daemon=True)
        thread.start()
    
    def log_event(self, event: AuditEvent) -> bool:
        """Log an audit event with integrity verification"""
        try:
            with self.lock:
                # Assign sequence number
                self.sequence_counter += 1
                
                # Compute event hash
                event_hash = event.compute_hash()
                
                # Create log entry with integrity chain
                log_entry = AuditLogEntry(
                    sequence_number=self.sequence_counter,
                    event=event,
                    event_hash=event_hash,
                    previous_hash=self.last_hash
                )
                
                # Store in database
                self._store_log_entry(log_entry)
                
                # Update chain state
                self.last_hash = log_entry.integrity_hash
                
                # Add to cache
                self.event_cache.append(event)
                if len(self.event_cache) > self.cache_size:
                    self.event_cache.pop(0)
                
                logger.debug(f"Logged audit event: {event.event_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return False
    
    def _store_log_entry(self, log_entry: AuditLogEntry):
        """Store log entry in database"""
        event = log_entry.event
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO audit_events (
                    sequence_number, event_id, timestamp, event_type, severity,
                    actor_id, actor_type, target_resource, action, outcome,
                    session_id, source_ip, user_agent, details, risk_indicators,
                    compliance_tags, event_hash, previous_hash, integrity_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                log_entry.sequence_number,
                event.event_id,
                event.timestamp.isoformat(),
                event.event_type.value,
                event.severity.value,
                event.actor_id,
                event.actor_type,
                event.target_resource,
                event.action,
                event.outcome,
                event.session_id,
                event.source_ip,
                event.user_agent,
                json.dumps(event.details) if event.details else None,
                json.dumps(event.risk_indicators) if event.risk_indicators else None,
                json.dumps(event.compliance_tags) if event.compliance_tags else None,
                log_entry.event_hash,
                log_entry.previous_hash,
                log_entry.integrity_hash
            ))
    
    def log_security_event(self, security_event: SecurityEvent):
        """Log a security event from the security manager"""
        audit_event = AuditEvent(
            event_id=security_event.event_id,
            timestamp=security_event.timestamp,
            event_type=AuditEventType.SECURITY_EVENT,
            severity=self._map_risk_to_severity(security_event.risk_level),
            actor_id=security_event.agent_id,
            actor_type="agent",
            target_resource=security_event.action,
            action=security_event.event_type,
            outcome=security_event.result,
            session_id=security_event.session_id,
            source_ip=security_event.ip_address,
            details=security_event.details,
            risk_indicators=[security_event.risk_level.value],
            compliance_tags=["security_monitoring"]
        )
        
        return self.log_event(audit_event)
    
    def _map_risk_to_severity(self, risk_level: RiskLevel) -> AuditSeverity:
        """Map security risk level to audit severity"""
        mapping = {
            RiskLevel.LOW: AuditSeverity.INFO,
            RiskLevel.MEDIUM: AuditSeverity.WARNING,
            RiskLevel.HIGH: AuditSeverity.ERROR,
            RiskLevel.CRITICAL: AuditSeverity.CRITICAL
        }
        return mapping.get(risk_level, AuditSeverity.INFO)
    
    def search_events(self, 
                     start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None,
                     event_type: Optional[AuditEventType] = None,
                     severity: Optional[AuditSeverity] = None,
                     actor_id: Optional[str] = None,
                     outcome: Optional[str] = None,
                     limit: int = 1000) -> List[AuditEvent]:
        """Search audit events with filters"""
        
        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)
        
        if severity:
            query += " AND severity = ?"
            params.append(severity.value)
        
        if actor_id:
            query += " AND actor_id = ?"
            params.append(actor_id)
        
        if outcome:
            query += " AND outcome = ?"
            params.append(outcome)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            events = []
            
            for row in cursor.fetchall():
                event = AuditEvent(
                    event_id=row[2],
                    timestamp=datetime.fromisoformat(row[3]),
                    event_type=AuditEventType(row[4]),
                    severity=AuditSeverity(row[5]),
                    actor_id=row[6],
                    actor_type=row[7],
                    target_resource=row[8],
                    action=row[9],
                    outcome=row[10],
                    session_id=row[11],
                    source_ip=row[12],
                    user_agent=row[13],
                    details=json.loads(row[14]) if row[14] else None,
                    risk_indicators=json.loads(row[15]) if row[15] else None,
                    compliance_tags=json.loads(row[16]) if row[16] else None
                )
                events.append(event)
        
        return events
    
    def get_audit_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get audit statistics for the specified time period"""
        start_time = datetime.now() - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            # Total events
            cursor = conn.execute(
                "SELECT COUNT(*) FROM audit_events WHERE timestamp >= ?",
                (start_time.isoformat(),)
            )
            total_events = cursor.fetchone()[0]
            
            # Events by type
            cursor = conn.execute('''
                SELECT event_type, COUNT(*) 
                FROM audit_events 
                WHERE timestamp >= ? 
                GROUP BY event_type
            ''', (start_time.isoformat(),))
            events_by_type = dict(cursor.fetchall())
            
            # Events by severity
            cursor = conn.execute('''
                SELECT severity, COUNT(*) 
                FROM audit_events 
                WHERE timestamp >= ? 
                GROUP BY severity
            ''', (start_time.isoformat(),))
            events_by_severity = dict(cursor.fetchall())
            
            # Events by outcome
            cursor = conn.execute('''
                SELECT outcome, COUNT(*) 
                FROM audit_events 
                WHERE timestamp >= ? 
                GROUP BY outcome
            ''', (start_time.isoformat(),))
            events_by_outcome = dict(cursor.fetchall())
            
            # Top actors
            cursor = conn.execute('''
                SELECT actor_id, COUNT(*) 
                FROM audit_events 
                WHERE timestamp >= ? 
                GROUP BY actor_id 
                ORDER BY COUNT(*) DESC 
                LIMIT 10
            ''', (start_time.isoformat(),))
            top_actors = dict(cursor.fetchall())
        
        return {
            'period_hours': hours,
            'total_events': total_events,
            'events_by_type': events_by_type,
            'events_by_severity': events_by_severity,
            'events_by_outcome': events_by_outcome,
            'top_actors': top_actors,
            'generated_at': datetime.now().isoformat()
        }
    
    def _perform_integrity_check(self) -> Dict[str, Any]:
        """Perform comprehensive integrity check of audit log"""
        logger.info("Starting audit log integrity check...")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT sequence_number, event_hash, previous_hash, integrity_hash
                FROM audit_events 
                ORDER BY sequence_number
            ''')
            
            entries = cursor.fetchall()
            
            if not entries:
                return {"status": "no_events", "message": "No audit events to check"}
            
            # Verify hash chain
            anomalies = []
            previous_hash = None
            
            for i, (seq_num, event_hash, prev_hash, integrity_hash) in enumerate(entries):
                # Check hash chain continuity
                if i > 0 and prev_hash != previous_hash:
                    anomalies.append(f"Hash chain break at sequence {seq_num}")
                
                # Verify integrity hash
                expected_integrity = hashlib.sha256(
                    json.dumps({
                        'sequence_number': seq_num,
                        'event_hash': event_hash,
                        'previous_hash': prev_hash or ""
                    }, sort_keys=True).encode()
                ).hexdigest()
                
                if integrity_hash != expected_integrity:
                    anomalies.append(f"Integrity hash mismatch at sequence {seq_num}")
                
                previous_hash = integrity_hash
            
            # Store integrity check result
            check_result = {
                'check_timestamp': datetime.now().isoformat(),
                'start_sequence': entries[0][0],
                'end_sequence': entries[-1][0],
                'total_events': len(entries),
                'integrity_status': 'valid' if not anomalies else 'compromised',
                'hash_chain_valid': len(anomalies) == 0,
                'anomalies_detected': len(anomalies),
                'details': json.dumps(anomalies) if anomalies else None
            }
            
            conn.execute('''
                INSERT INTO audit_integrity (
                    check_timestamp, start_sequence, end_sequence, total_events,
                    integrity_status, hash_chain_valid, anomalies_detected, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                check_result['check_timestamp'],
                check_result['start_sequence'],
                check_result['end_sequence'],
                check_result['total_events'],
                check_result['integrity_status'],
                check_result['hash_chain_valid'],
                check_result['anomalies_detected'],
                check_result['details']
            ))
            
            if anomalies:
                logger.warning(f"Integrity check found {len(anomalies)} anomalies")
            else:
                logger.info("Integrity check passed - audit log is valid")
            
            return check_result
    
    def _enforce_retention_policy(self):
        """Enforce retention policy - archive and delete old events"""
        logger.info("Enforcing audit retention policy...")
        
        try:
            # Get events that need archiving
            events_to_archive = self.search_events(
                end_time=datetime.now() - timedelta(days=self.retention_policy.archive_days),
                limit=10000
            )
            
            # Archive events
            archived_count = 0
            for event in events_to_archive:
                if self._archive_event(event):
                    archived_count += 1
            
            # Delete events past retention period
            cutoff_time = datetime.now() - timedelta(days=self.retention_policy.retention_days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM audit_events WHERE timestamp < ?",
                    (cutoff_time.isoformat(),)
                )
                deleted_count = cursor.rowcount
            
            logger.info(f"Retention policy: archived {archived_count}, deleted {deleted_count} events")
            
        except Exception as e:
            logger.error(f"Error enforcing retention policy: {e}")
    
    def _archive_event(self, event: AuditEvent) -> bool:
        """Archive a single event"""
        try:
            archive_path = self.retention_policy.get_archive_path(event)
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Compress and store
            event_data = event.to_json()
            
            if self.retention_policy.compression_enabled:
                with gzip.open(archive_path, 'at', encoding='utf-8') as f:
                    f.write(event_data + '\n')
            else:
                with open(archive_path.with_suffix('.json'), 'a', encoding='utf-8') as f:
                    f.write(event_data + '\n')
            
            return True
            
        except Exception as e:
            logger.error(f"Error archiving event {event.event_id}: {e}")
            return False
    
    def _maintain_cache(self):
        """Maintain in-memory event cache"""
        if len(self.event_cache) > self.cache_size:
            excess = len(self.event_cache) - self.cache_size
            self.event_cache = self.event_cache[excess:]
    
    def get_compliance_report(self, compliance_tag: str, days: int = 30) -> Dict[str, Any]:
        """Generate compliance report for specific tag"""
        start_time = datetime.now() - timedelta(days=days)
        
        # Search for events with specific compliance tag
        events = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT * FROM audit_events 
                WHERE timestamp >= ? AND compliance_tags LIKE ?
                ORDER BY timestamp DESC
            ''', (start_time.isoformat(), f'%{compliance_tag}%'))
            
            for row in cursor.fetchall():
                event = AuditEvent(
                    event_id=row[2],
                    timestamp=datetime.fromisoformat(row[3]),
                    event_type=AuditEventType(row[4]),
                    severity=AuditSeverity(row[5]),
                    actor_id=row[6],
                    actor_type=row[7],
                    target_resource=row[8],
                    action=row[9],
                    outcome=row[10],
                    session_id=row[11],
                    source_ip=row[12],
                    user_agent=row[13],
                    details=json.loads(row[14]) if row[14] else None,
                    risk_indicators=json.loads(row[15]) if row[15] else None,
                    compliance_tags=json.loads(row[16]) if row[16] else None
                )
                events.append(event)
        
        # Analyze events
        total_events = len(events)
        successful_events = len([e for e in events if e.outcome == "success"])
        failed_events = len([e for e in events if e.outcome == "failure"])
        
        severity_breakdown = {}
        for event in events:
            severity = event.severity.value
            severity_breakdown[severity] = severity_breakdown.get(severity, 0) + 1
        
        return {
            'compliance_tag': compliance_tag,
            'report_period_days': days,
            'total_events': total_events,
            'successful_events': successful_events,
            'failed_events': failed_events,
            'success_rate': (successful_events / total_events * 100) if total_events > 0 else 0,
            'severity_breakdown': severity_breakdown,
            'generated_at': datetime.now().isoformat()
        }


# Global audit logger instance
audit_logger = AuditLogger()


# Convenience functions for common audit operations
def log_authentication_event(user_id: str, outcome: str, details: Dict[str, Any] = None):
    """Log authentication event"""
    event = AuditEvent(
        event_id=f"auth_{user_id}_{int(time.time() * 1000)}",
        timestamp=datetime.now(),
        event_type=AuditEventType.AUTHENTICATION,
        severity=AuditSeverity.INFO if outcome == "success" else AuditSeverity.WARNING,
        actor_id=user_id,
        actor_type="user",
        target_resource="authentication_system",
        action="login",
        outcome=outcome,
        details=details,
        compliance_tags=["authentication", "access_control"]
    )
    return audit_logger.log_event(event)


def log_authorization_event(user_id: str, resource: str, action: str, outcome: str, details: Dict[str, Any] = None):
    """Log authorization event"""
    event = AuditEvent(
        event_id=f"authz_{user_id}_{int(time.time() * 1000)}",
        timestamp=datetime.now(),
        event_type=AuditEventType.AUTHORIZATION,
        severity=AuditSeverity.INFO if outcome == "success" else AuditSeverity.WARNING,
        actor_id=user_id,
        actor_type="user",
        target_resource=resource,
        action=action,
        outcome=outcome,
        details=details,
        compliance_tags=["authorization", "access_control"]
    )
    return audit_logger.log_event(event)


def log_data_access_event(user_id: str, resource: str, action: str, outcome: str, details: Dict[str, Any] = None):
    """Log data access event"""
    event = AuditEvent(
        event_id=f"data_{user_id}_{int(time.time() * 1000)}",
        timestamp=datetime.now(),
        event_type=AuditEventType.DATA_ACCESS,
        severity=AuditSeverity.INFO if outcome == "success" else AuditSeverity.ERROR,
        actor_id=user_id,
        actor_type="user",
        target_resource=resource,
        action=action,
        outcome=outcome,
        details=details,
        compliance_tags=["data_access", "privacy"]
    )
    return audit_logger.log_event(event)


def log_admin_action(admin_id: str, action: str, target: str, outcome: str, details: Dict[str, Any] = None):
    """Log administrative action"""
    event = AuditEvent(
        event_id=f"admin_{admin_id}_{int(time.time() * 1000)}",
        timestamp=datetime.now(),
        event_type=AuditEventType.ADMIN_ACTION,
        severity=AuditSeverity.WARNING,
        actor_id=admin_id,
        actor_type="admin",
        target_resource=target,
        action=action,
        outcome=outcome,
        details=details,
        compliance_tags=["admin_actions", "privileged_access"]
    )
    return audit_logger.log_event(event)


if __name__ == "__main__":
    # Test the audit logging system
    print("Audit Logging System Test")
    print("=" * 40)
    
    # Test logging various events
    log_authentication_event("user123", "success", {"login_method": "password"})
    log_authorization_event("user123", "document.pdf", "read", "success")
    log_data_access_event("user123", "customer_data", "query", "success", {"query": "SELECT * FROM customers LIMIT 10"})
    log_admin_action("admin456", "user_delete", "user789", "success", {"reason": "account_cleanup"})
    
    # Get statistics
    stats = audit_logger.get_audit_statistics(hours=1)
    print(f"Audit Statistics: {json.dumps(stats, indent=2)}")
    
    # Perform integrity check
    integrity_result = audit_logger._perform_integrity_check()
    print(f"Integrity Check: {integrity_result}")
    
    print("\nAudit logging system test complete!")