#!/usr/bin/env python3
"""
Compliance Monitoring Framework
LeanVibe Agent Hive Foundation Epic Phase 2 - Continuous Security Monitoring

Comprehensive compliance monitoring with:
- Regulatory compliance checks (GDPR, HIPAA, SOX, etc.)
- Policy enforcement and validation
- Automated compliance reporting
- Real-time compliance alerting
- Risk assessment and scoring
- Audit trail compliance verification
"""

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
import re
import hashlib

# Import audit logging system
from audit_logging_system import AuditLogger, AuditEvent, AuditEventType, AuditSeverity
from security.security_manager import SecurityManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComplianceFramework(Enum):
    """Supported compliance frameworks"""
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    NIST = "nist"
    SOC2 = "soc2"
    COPPA = "coppa"
    CCPA = "ccpa"
    CUSTOM = "custom"


class ComplianceStatus(Enum):
    """Compliance status levels"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NOT_ASSESSED = "not_assessed"
    UNDER_REVIEW = "under_review"


class ComplianceRiskLevel(Enum):
    """Compliance risk levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ComplianceRule:
    """Compliance rule definition"""
    rule_id: str
    framework: ComplianceFramework
    category: str
    title: str
    description: str
    requirement: str
    validation_query: str
    threshold: Optional[float] = None
    severity: ComplianceRiskLevel = ComplianceRiskLevel.MEDIUM
    enabled: bool = True
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class ComplianceResult:
    """Compliance check result"""
    rule_id: str
    framework: ComplianceFramework
    timestamp: datetime
    status: ComplianceStatus
    score: float  # 0-100
    findings: List[str]
    evidence: Dict[str, Any]
    remediation_steps: List[str]
    risk_level: ComplianceRiskLevel
    next_check: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['framework'] = self.framework.value
        data['timestamp'] = self.timestamp.isoformat()
        data['status'] = self.status.value
        data['risk_level'] = self.risk_level.value
        if self.next_check:
            data['next_check'] = self.next_check.isoformat()
        return data


@dataclass
class ComplianceReport:
    """Comprehensive compliance report"""
    report_id: str
    framework: ComplianceFramework
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    overall_score: float
    total_rules: int
    compliant_rules: int
    non_compliant_rules: int
    results: List[ComplianceResult]
    recommendations: List[str]
    executive_summary: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['framework'] = self.framework.value
        data['generated_at'] = self.generated_at.isoformat()
        data['period_start'] = self.period_start.isoformat()
        data['period_end'] = self.period_end.isoformat()
        data['results'] = [r.to_dict() for r in self.results]
        return data


class ComplianceRuleEngine:
    """Compliance rule engine for executing compliance checks"""
    
    def __init__(self, audit_logger: AuditLogger, security_manager: SecurityManager):
        self.audit_logger = audit_logger
        self.security_manager = security_manager
        
        # Load built-in compliance rules
        self.rules = self._load_builtin_rules()
        
    def _load_builtin_rules(self) -> Dict[str, ComplianceRule]:
        """Load built-in compliance rules for major frameworks"""
        rules = {}
        
        # GDPR Rules
        rules.update(self._load_gdpr_rules())
        
        # ISO 27001 Rules
        rules.update(self._load_iso27001_rules())
        
        # SOC 2 Rules
        rules.update(self._load_soc2_rules())
        
        # NIST Rules
        rules.update(self._load_nist_rules())
        
        return rules
    
    def _load_gdpr_rules(self) -> Dict[str, ComplianceRule]:
        """Load GDPR compliance rules"""
        return {
            "gdpr_data_retention": ComplianceRule(
                rule_id="gdpr_data_retention",
                framework=ComplianceFramework.GDPR,
                category="data_protection",
                title="Data Retention Compliance",
                description="Verify data retention policies are enforced",
                requirement="Data must not be retained longer than necessary",
                validation_query="SELECT COUNT(*) FROM audit_events WHERE event_type = 'data_access' AND timestamp < ?",
                threshold=0.0,
                severity=ComplianceRiskLevel.HIGH,
                tags=["data_protection", "retention", "privacy"]
            ),
            "gdpr_access_logging": ComplianceRule(
                rule_id="gdpr_access_logging",
                framework=ComplianceFramework.GDPR,
                category="access_control",
                title="Personal Data Access Logging",
                description="All access to personal data must be logged",
                requirement="Log all access to personal data systems",
                validation_query="SELECT COUNT(*) FROM audit_events WHERE event_type = 'data_access' AND timestamp >= ?",
                threshold=1.0,
                severity=ComplianceRiskLevel.HIGH,
                tags=["access_control", "logging", "personal_data"]
            ),
            "gdpr_consent_tracking": ComplianceRule(
                rule_id="gdpr_consent_tracking",
                framework=ComplianceFramework.GDPR,
                category="consent",
                title="Consent Tracking",
                description="Track and validate user consent for data processing",
                requirement="Maintain records of user consent",
                validation_query="SELECT COUNT(*) FROM audit_events WHERE action = 'consent_granted' AND timestamp >= ?",
                threshold=1.0,
                severity=ComplianceRiskLevel.CRITICAL,
                tags=["consent", "data_processing", "user_rights"]
            )
        }
    
    def _load_iso27001_rules(self) -> Dict[str, ComplianceRule]:
        """Load ISO 27001 compliance rules"""
        return {
            "iso27001_access_control": ComplianceRule(
                rule_id="iso27001_access_control",
                framework=ComplianceFramework.ISO_27001,
                category="access_control",
                title="Access Control Management",
                description="Verify access control mechanisms are in place",
                requirement="Implement proper access control measures",
                validation_query="SELECT COUNT(*) FROM audit_events WHERE event_type = 'authorization' AND outcome = 'success'",
                threshold=0.95,
                severity=ComplianceRiskLevel.HIGH,
                tags=["access_control", "authentication", "authorization"]
            ),
            "iso27001_incident_response": ComplianceRule(
                rule_id="iso27001_incident_response",
                framework=ComplianceFramework.ISO_27001,
                category="incident_management",
                title="Security Incident Response",
                description="Security incidents must be properly logged and responded to",
                requirement="Maintain incident response procedures",
                validation_query="SELECT COUNT(*) FROM audit_events WHERE event_type = 'security_event' AND severity = 'critical'",
                threshold=0.0,
                severity=ComplianceRiskLevel.CRITICAL,
                tags=["incident_response", "security", "monitoring"]
            ),
            "iso27001_audit_trail": ComplianceRule(
                rule_id="iso27001_audit_trail",
                framework=ComplianceFramework.ISO_27001,
                category="audit_logging",
                title="Audit Trail Integrity",
                description="Audit trails must be complete and tamper-proof",
                requirement="Maintain comprehensive audit logs",
                validation_query="SELECT COUNT(*) FROM audit_events WHERE timestamp >= ?",
                threshold=1.0,
                severity=ComplianceRiskLevel.HIGH,
                tags=["audit_trail", "logging", "integrity"]
            )
        }
    
    def _load_soc2_rules(self) -> Dict[str, ComplianceRule]:
        """Load SOC 2 compliance rules"""
        return {
            "soc2_security_monitoring": ComplianceRule(
                rule_id="soc2_security_monitoring",
                framework=ComplianceFramework.SOC2,
                category="security",
                title="Security Monitoring",
                description="Continuous security monitoring must be in place",
                requirement="Monitor security events continuously",
                validation_query="SELECT COUNT(*) FROM audit_events WHERE event_type = 'security_event' AND timestamp >= ?",
                threshold=1.0,
                severity=ComplianceRiskLevel.HIGH,
                tags=["security", "monitoring", "continuous"]
            ),
            "soc2_availability": ComplianceRule(
                rule_id="soc2_availability",
                framework=ComplianceFramework.SOC2,
                category="availability",
                title="System Availability",
                description="System availability must be monitored and maintained",
                requirement="Ensure system availability",
                validation_query="SELECT COUNT(*) FROM audit_events WHERE event_type = 'system_change' AND outcome = 'failure'",
                threshold=0.0,
                severity=ComplianceRiskLevel.MEDIUM,
                tags=["availability", "system_health", "uptime"]
            ),
            "soc2_processing_integrity": ComplianceRule(
                rule_id="soc2_processing_integrity",
                framework=ComplianceFramework.SOC2,
                category="processing_integrity",
                title="Processing Integrity",
                description="Data processing must be complete, accurate, and authorized",
                requirement="Ensure processing integrity",
                validation_query="SELECT COUNT(*) FROM audit_events WHERE event_type = 'data_modification' AND outcome = 'success'",
                threshold=0.99,
                severity=ComplianceRiskLevel.HIGH,
                tags=["processing_integrity", "data_quality", "authorization"]
            )
        }
    
    def _load_nist_rules(self) -> Dict[str, ComplianceRule]:
        """Load NIST Cybersecurity Framework rules"""
        return {
            "nist_identify": ComplianceRule(
                rule_id="nist_identify",
                framework=ComplianceFramework.NIST,
                category="identify",
                title="Asset Identification",
                description="Identify and manage assets and systems",
                requirement="Maintain asset inventory",
                validation_query="SELECT COUNT(*) FROM audit_events WHERE event_type = 'system_change' AND action = 'asset_discovery'",
                threshold=1.0,
                severity=ComplianceRiskLevel.MEDIUM,
                tags=["identify", "asset_management", "inventory"]
            ),
            "nist_protect": ComplianceRule(
                rule_id="nist_protect",
                framework=ComplianceFramework.NIST,
                category="protect",
                title="Protection Measures",
                description="Implement protective measures for systems and data",
                requirement="Deploy protective safeguards",
                validation_query="SELECT COUNT(*) FROM audit_events WHERE event_type = 'security_event' AND action = 'protection_enabled'",
                threshold=1.0,
                severity=ComplianceRiskLevel.HIGH,
                tags=["protect", "safeguards", "security_controls"]
            ),
            "nist_detect": ComplianceRule(
                rule_id="nist_detect",
                framework=ComplianceFramework.NIST,
                category="detect",
                title="Detection Capabilities",
                description="Implement detection capabilities for security events",
                requirement="Maintain detection systems",
                validation_query="SELECT COUNT(*) FROM audit_events WHERE event_type = 'security_event' AND action = 'threat_detected'",
                threshold=1.0,
                severity=ComplianceRiskLevel.HIGH,
                tags=["detect", "monitoring", "threat_detection"]
            ),
            "nist_respond": ComplianceRule(
                rule_id="nist_respond",
                framework=ComplianceFramework.NIST,
                category="respond",
                title="Incident Response",
                description="Respond to detected security events",
                requirement="Implement incident response procedures",
                validation_query="SELECT COUNT(*) FROM audit_events WHERE event_type = 'security_event' AND action = 'incident_response'",
                threshold=1.0,
                severity=ComplianceRiskLevel.CRITICAL,
                tags=["respond", "incident_response", "security"]
            )
        }
    
    def execute_rule(self, rule: ComplianceRule, period_hours: int = 24) -> ComplianceResult:
        """Execute a compliance rule and return result"""
        try:
            start_time = datetime.now() - timedelta(hours=period_hours)
            
            # Execute validation query
            evidence = self._execute_validation_query(rule, start_time)
            
            # Determine compliance status
            status, score, findings = self._evaluate_compliance(rule, evidence)
            
            # Determine risk level
            risk_level = self._determine_risk_level(rule, status, score)
            
            # Generate remediation steps
            remediation_steps = self._generate_remediation_steps(rule, status, findings)
            
            result = ComplianceResult(
                rule_id=rule.rule_id,
                framework=rule.framework,
                timestamp=datetime.now(),
                status=status,
                score=score,
                findings=findings,
                evidence=evidence,
                remediation_steps=remediation_steps,
                risk_level=risk_level,
                next_check=datetime.now() + timedelta(hours=24)
            )
            
            # Log compliance check
            self._log_compliance_check(rule, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing compliance rule {rule.rule_id}: {e}")
            return ComplianceResult(
                rule_id=rule.rule_id,
                framework=rule.framework,
                timestamp=datetime.now(),
                status=ComplianceStatus.NOT_ASSESSED,
                score=0.0,
                findings=[f"Error executing rule: {str(e)}"],
                evidence={},
                remediation_steps=["Fix rule execution error"],
                risk_level=ComplianceRiskLevel.HIGH
            )
    
    def _execute_validation_query(self, rule: ComplianceRule, start_time: datetime) -> Dict[str, Any]:
        """Execute validation query for a rule"""
        evidence = {}
        
        try:
            # Search audit events based on rule criteria
            events = self.audit_logger.search_events(
                start_time=start_time,
                limit=10000
            )
            
            # Apply rule-specific filters
            relevant_events = []
            for event in events:
                if self._event_matches_rule(event, rule):
                    relevant_events.append(event)
            
            evidence['total_events'] = len(relevant_events)
            evidence['event_types'] = {}
            evidence['outcomes'] = {}
            evidence['actors'] = {}
            
            # Analyze events
            for event in relevant_events:
                # Count by event type
                event_type = event.event_type.value
                evidence['event_types'][event_type] = evidence['event_types'].get(event_type, 0) + 1
                
                # Count by outcome
                outcome = event.outcome
                evidence['outcomes'][outcome] = evidence['outcomes'].get(outcome, 0) + 1
                
                # Count by actor
                actor = event.actor_id
                evidence['actors'][actor] = evidence['actors'].get(actor, 0) + 1
            
            # Rule-specific metrics
            if rule.rule_id == "gdpr_access_logging":
                evidence['data_access_events'] = len([e for e in relevant_events if e.event_type == AuditEventType.DATA_ACCESS])
            elif rule.rule_id == "iso27001_access_control":
                successful_auth = len([e for e in relevant_events if e.event_type == AuditEventType.AUTHORIZATION and e.outcome == "success"])
                total_auth = len([e for e in relevant_events if e.event_type == AuditEventType.AUTHORIZATION])
                evidence['auth_success_rate'] = (successful_auth / total_auth) if total_auth > 0 else 0
            
            return evidence
            
        except Exception as e:
            logger.error(f"Error executing validation query for rule {rule.rule_id}: {e}")
            return {'error': str(e)}
    
    def _event_matches_rule(self, event: AuditEvent, rule: ComplianceRule) -> bool:
        """Check if an event matches a compliance rule"""
        # Basic matching based on rule tags and event properties
        if rule.tags:
            for tag in rule.tags:
                if (tag in event.event_type.value or 
                    tag in event.action or 
                    tag in str(event.details)):
                    return True
        
        # Rule-specific matching
        if rule.rule_id == "gdpr_data_retention":
            return event.event_type == AuditEventType.DATA_ACCESS
        elif rule.rule_id == "gdpr_access_logging":
            return event.event_type == AuditEventType.DATA_ACCESS
        elif rule.rule_id == "iso27001_access_control":
            return event.event_type == AuditEventType.AUTHORIZATION
        elif rule.rule_id == "iso27001_incident_response":
            return event.event_type == AuditEventType.SECURITY_EVENT
        elif rule.rule_id == "soc2_security_monitoring":
            return event.event_type == AuditEventType.SECURITY_EVENT
        
        return False
    
    def _evaluate_compliance(self, rule: ComplianceRule, evidence: Dict[str, Any]) -> Tuple[ComplianceStatus, float, List[str]]:
        """Evaluate compliance based on rule and evidence"""
        findings = []
        
        # Handle errors in evidence collection
        if 'error' in evidence:
            return ComplianceStatus.NOT_ASSESSED, 0.0, [f"Evidence collection error: {evidence['error']}"]
        
        total_events = evidence.get('total_events', 0)
        
        # Rule-specific evaluation
        if rule.rule_id == "gdpr_data_retention":
            # Check if old data access events exist
            if total_events > 0:
                findings.append(f"Found {total_events} data access events - verify retention compliance")
                return ComplianceStatus.PARTIALLY_COMPLIANT, 70.0, findings
            else:
                return ComplianceStatus.COMPLIANT, 100.0, ["No data retention violations found"]
        
        elif rule.rule_id == "gdpr_access_logging":
            data_access_events = evidence.get('data_access_events', 0)
            if data_access_events > 0:
                return ComplianceStatus.COMPLIANT, 100.0, [f"Found {data_access_events} properly logged data access events"]
            else:
                return ComplianceStatus.NON_COMPLIANT, 0.0, ["No data access events logged"]
        
        elif rule.rule_id == "iso27001_access_control":
            auth_success_rate = evidence.get('auth_success_rate', 0)
            if auth_success_rate >= 0.95:
                return ComplianceStatus.COMPLIANT, 100.0, [f"Access control success rate: {auth_success_rate:.2%}"]
            elif auth_success_rate >= 0.85:
                return ComplianceStatus.PARTIALLY_COMPLIANT, 75.0, [f"Access control success rate below threshold: {auth_success_rate:.2%}"]
            else:
                return ComplianceStatus.NON_COMPLIANT, 25.0, [f"Poor access control success rate: {auth_success_rate:.2%}"]
        
        elif rule.rule_id == "iso27001_incident_response":
            security_events = evidence.get('event_types', {}).get('security_event', 0)
            if security_events == 0:
                return ComplianceStatus.COMPLIANT, 100.0, ["No security incidents detected"]
            else:
                findings.append(f"Found {security_events} security events - verify incident response")
                return ComplianceStatus.PARTIALLY_COMPLIANT, 80.0, findings
        
        # Generic evaluation
        if total_events > 0:
            successful_outcomes = evidence.get('outcomes', {}).get('success', 0)
            success_rate = (successful_outcomes / total_events) if total_events > 0 else 0
            
            if success_rate >= 0.95:
                return ComplianceStatus.COMPLIANT, 100.0, [f"High success rate: {success_rate:.2%}"]
            elif success_rate >= 0.85:
                return ComplianceStatus.PARTIALLY_COMPLIANT, 75.0, [f"Moderate success rate: {success_rate:.2%}"]
            else:
                return ComplianceStatus.NON_COMPLIANT, 25.0, [f"Low success rate: {success_rate:.2%}"]
        else:
            return ComplianceStatus.NOT_ASSESSED, 0.0, ["No relevant events found for assessment"]
    
    def _determine_risk_level(self, rule: ComplianceRule, status: ComplianceStatus, score: float) -> ComplianceRiskLevel:
        """Determine risk level based on compliance status"""
        if status == ComplianceStatus.NON_COMPLIANT:
            return ComplianceRiskLevel.CRITICAL if rule.severity == ComplianceRiskLevel.CRITICAL else ComplianceRiskLevel.HIGH
        elif status == ComplianceStatus.PARTIALLY_COMPLIANT:
            return ComplianceRiskLevel.MEDIUM
        elif status == ComplianceStatus.COMPLIANT:
            return ComplianceRiskLevel.LOW
        else:
            return ComplianceRiskLevel.MEDIUM
    
    def _generate_remediation_steps(self, rule: ComplianceRule, status: ComplianceStatus, findings: List[str]) -> List[str]:
        """Generate remediation steps based on compliance status"""
        steps = []
        
        if status == ComplianceStatus.NON_COMPLIANT:
            steps.append(f"Immediate action required for {rule.title}")
            steps.append(f"Review and implement {rule.requirement}")
            steps.append("Conduct root cause analysis")
            steps.append("Implement corrective measures")
            steps.append("Monitor for improvement")
        
        elif status == ComplianceStatus.PARTIALLY_COMPLIANT:
            steps.append(f"Improvement needed for {rule.title}")
            steps.append("Review current implementation")
            steps.append("Identify gaps and weaknesses")
            steps.append("Implement improvements")
        
        elif status == ComplianceStatus.NOT_ASSESSED:
            steps.append("Fix assessment methodology")
            steps.append("Collect proper evidence")
            steps.append("Re-run compliance check")
        
        # Add rule-specific steps
        if rule.rule_id == "gdpr_access_logging":
            steps.append("Ensure all data access is logged")
            steps.append("Implement data access monitoring")
        elif rule.rule_id == "iso27001_access_control":
            steps.append("Review access control policies")
            steps.append("Strengthen authentication mechanisms")
        
        return steps
    
    def _log_compliance_check(self, rule: ComplianceRule, result: ComplianceResult):
        """Log compliance check result"""
        from audit_logging_system import AuditEvent, AuditEventType, AuditSeverity
        
        severity_map = {
            ComplianceStatus.COMPLIANT: AuditSeverity.INFO,
            ComplianceStatus.PARTIALLY_COMPLIANT: AuditSeverity.WARNING,
            ComplianceStatus.NON_COMPLIANT: AuditSeverity.ERROR,
            ComplianceStatus.NOT_ASSESSED: AuditSeverity.WARNING
        }
        
        event = AuditEvent(
            event_id=f"compliance_{rule.rule_id}_{int(time.time() * 1000)}",
            timestamp=datetime.now(),
            event_type=AuditEventType.COMPLIANCE_CHECK,
            severity=severity_map.get(result.status, AuditSeverity.INFO),
            actor_id="compliance_monitor",
            actor_type="system",
            target_resource=rule.rule_id,
            action="compliance_check",
            outcome=result.status.value,
            details={
                "framework": rule.framework.value,
                "score": result.score,
                "findings": result.findings,
                "risk_level": result.risk_level.value
            },
            compliance_tags=[rule.framework.value, "compliance_monitoring"]
        )
        
        self.audit_logger.log_event(event)


class ComplianceMonitor:
    """Main compliance monitoring system"""
    
    def __init__(self, config_path: str = "config/compliance_config.json"):
        self.config = self._load_config(config_path)
        self.audit_logger = AuditLogger()
        self.security_manager = SecurityManager()
        self.rule_engine = ComplianceRuleEngine(self.audit_logger, self.security_manager)
        self.db_path = "compliance_monitoring.db"
        self.lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        # Start monitoring
        self._start_monitoring()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load compliance configuration"""
        default_config = {
            "enabled_frameworks": ["gdpr", "iso_27001", "soc2"],
            "check_interval_hours": 24,
            "alert_thresholds": {
                "critical": 0,
                "high": 3,
                "medium": 10
            },
            "reporting": {
                "enabled": True,
                "frequency": "daily"
            }
        }
        
        try:
            if Path(config_path).exists():
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
        except Exception as e:
            logger.warning(f"Failed to load compliance config: {e}")
        
        return default_config
    
    def _init_database(self):
        """Initialize compliance monitoring database"""
        with sqlite3.connect(self.db_path) as conn:
            # Compliance results table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS compliance_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id TEXT NOT NULL,
                    framework TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    score REAL NOT NULL,
                    findings TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    remediation_steps TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    next_check TEXT
                )
            ''')
            
            # Compliance reports table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS compliance_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT UNIQUE NOT NULL,
                    framework TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    overall_score REAL NOT NULL,
                    total_rules INTEGER NOT NULL,
                    compliant_rules INTEGER NOT NULL,
                    non_compliant_rules INTEGER NOT NULL,
                    report_data TEXT NOT NULL
                )
            ''')
            
            # Create indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_compliance_timestamp ON compliance_results(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_compliance_framework ON compliance_results(framework)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_compliance_status ON compliance_results(status)')
    
    def _start_monitoring(self):
        """Start compliance monitoring thread"""
        def monitor_worker():
            while True:
                try:
                    self._run_compliance_checks()
                    time.sleep(self.config.get('check_interval_hours', 24) * 3600)
                except Exception as e:
                    logger.error(f"Compliance monitoring error: {e}")
                    time.sleep(3600)  # Wait 1 hour on error
        
        thread = threading.Thread(target=monitor_worker, daemon=True)
        thread.start()
        logger.info("Compliance monitoring started")
    
    def _run_compliance_checks(self):
        """Run all compliance checks"""
        logger.info("Starting compliance checks...")
        
        enabled_frameworks = self.config.get('enabled_frameworks', [])
        results = []
        
        for rule_id, rule in self.rule_engine.rules.items():
            if rule.framework.value in enabled_frameworks and rule.enabled:
                try:
                    result = self.rule_engine.execute_rule(rule)
                    results.append(result)
                    
                    # Store result
                    self._store_compliance_result(result)
                    
                    logger.info(f"Compliance check {rule_id}: {result.status.value} (score: {result.score:.1f})")
                    
                except Exception as e:
                    logger.error(f"Error in compliance check {rule_id}: {e}")
        
        # Generate alerts for non-compliant rules
        self._generate_compliance_alerts(results)
        
        logger.info(f"Completed {len(results)} compliance checks")
    
    def _store_compliance_result(self, result: ComplianceResult):
        """Store compliance result in database"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO compliance_results (
                        rule_id, framework, timestamp, status, score, findings,
                        evidence, remediation_steps, risk_level, next_check
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result.rule_id,
                    result.framework.value,
                    result.timestamp.isoformat(),
                    result.status.value,
                    result.score,
                    json.dumps(result.findings),
                    json.dumps(result.evidence),
                    json.dumps(result.remediation_steps),
                    result.risk_level.value,
                    result.next_check.isoformat() if result.next_check else None
                ))
    
    def _generate_compliance_alerts(self, results: List[ComplianceResult]):
        """Generate alerts for compliance violations"""
        critical_violations = [r for r in results if r.risk_level == ComplianceRiskLevel.CRITICAL]
        high_violations = [r for r in results if r.risk_level == ComplianceRiskLevel.HIGH]
        
        if critical_violations:
            logger.critical(f"CRITICAL COMPLIANCE VIOLATIONS: {len(critical_violations)} rules")
            for result in critical_violations:
                logger.critical(f"  - {result.rule_id}: {result.status.value}")
        
        if high_violations:
            logger.warning(f"HIGH RISK COMPLIANCE ISSUES: {len(high_violations)} rules")
            for result in high_violations:
                logger.warning(f"  - {result.rule_id}: {result.status.value}")
    
    def generate_compliance_report(self, framework: ComplianceFramework, days: int = 30) -> ComplianceReport:
        """Generate comprehensive compliance report"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # Get recent results for framework
        results = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT * FROM compliance_results 
                WHERE framework = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            ''', (framework.value, start_time.isoformat()))
            
            for row in cursor.fetchall():
                result = ComplianceResult(
                    rule_id=row[1],
                    framework=ComplianceFramework(row[2]),
                    timestamp=datetime.fromisoformat(row[3]),
                    status=ComplianceStatus(row[4]),
                    score=row[5],
                    findings=json.loads(row[6]),
                    evidence=json.loads(row[7]),
                    remediation_steps=json.loads(row[8]),
                    risk_level=ComplianceRiskLevel(row[9]),
                    next_check=datetime.fromisoformat(row[10]) if row[10] else None
                )
                results.append(result)
        
        # Calculate overall metrics
        if results:
            overall_score = sum(r.score for r in results) / len(results)
            compliant_count = len([r for r in results if r.status == ComplianceStatus.COMPLIANT])
            non_compliant_count = len([r for r in results if r.status == ComplianceStatus.NON_COMPLIANT])
        else:
            overall_score = 0.0
            compliant_count = 0
            non_compliant_count = 0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(results)
        
        # Generate executive summary
        executive_summary = self._generate_executive_summary(framework, overall_score, results)
        
        report = ComplianceReport(
            report_id=f"compliance_{framework.value}_{int(time.time())}",
            framework=framework,
            generated_at=datetime.now(),
            period_start=start_time,
            period_end=end_time,
            overall_score=overall_score,
            total_rules=len(results),
            compliant_rules=compliant_count,
            non_compliant_rules=non_compliant_count,
            results=results,
            recommendations=recommendations,
            executive_summary=executive_summary
        )
        
        # Store report
        self._store_compliance_report(report)
        
        return report
    
    def _generate_recommendations(self, results: List[ComplianceResult]) -> List[str]:
        """Generate recommendations based on compliance results"""
        recommendations = []
        
        non_compliant = [r for r in results if r.status == ComplianceStatus.NON_COMPLIANT]
        partially_compliant = [r for r in results if r.status == ComplianceStatus.PARTIALLY_COMPLIANT]
        
        if non_compliant:
            recommendations.append(f"Address {len(non_compliant)} non-compliant rules immediately")
            for result in non_compliant[:3]:  # Top 3
                recommendations.extend(result.remediation_steps[:2])  # Top 2 steps
        
        if partially_compliant:
            recommendations.append(f"Improve {len(partially_compliant)} partially compliant rules")
        
        if not non_compliant and not partially_compliant:
            recommendations.append("Maintain current compliance posture")
            recommendations.append("Continue regular monitoring and assessments")
        
        return recommendations
    
    def _generate_executive_summary(self, framework: ComplianceFramework, score: float, results: List[ComplianceResult]) -> str:
        """Generate executive summary for compliance report"""
        summary = f"Compliance Assessment Summary for {framework.value.upper()}\n\n"
        summary += f"Overall Compliance Score: {score:.1f}/100\n\n"
        
        if score >= 90:
            summary += "EXCELLENT: Organization demonstrates strong compliance posture with minimal risks."
        elif score >= 80:
            summary += "GOOD: Organization shows good compliance but some improvements needed."
        elif score >= 70:
            summary += "FAIR: Organization has basic compliance but significant improvements required."
        else:
            summary += "POOR: Organization has significant compliance gaps requiring immediate attention."
        
        critical_count = len([r for r in results if r.risk_level == ComplianceRiskLevel.CRITICAL])
        high_count = len([r for r in results if r.risk_level == ComplianceRiskLevel.HIGH])
        
        if critical_count > 0:
            summary += f"\n\nCRITICAL ATTENTION REQUIRED: {critical_count} critical compliance issues identified."
        
        if high_count > 0:
            summary += f"\n\nHIGH PRIORITY: {high_count} high-risk compliance issues require prompt attention."
        
        return summary
    
    def _store_compliance_report(self, report: ComplianceReport):
        """Store compliance report in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO compliance_reports (
                    report_id, framework, generated_at, period_start, period_end,
                    overall_score, total_rules, compliant_rules, non_compliant_rules,
                    report_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report.report_id,
                report.framework.value,
                report.generated_at.isoformat(),
                report.period_start.isoformat(),
                report.period_end.isoformat(),
                report.overall_score,
                report.total_rules,
                report.compliant_rules,
                report.non_compliant_rules,
                json.dumps(report.to_dict())
            ))
    
    def get_compliance_status(self, framework: ComplianceFramework = None) -> Dict[str, Any]:
        """Get current compliance status"""
        with sqlite3.connect(self.db_path) as conn:
            if framework:
                cursor = conn.execute('''
                    SELECT framework, AVG(score), COUNT(*), 
                           SUM(CASE WHEN status = 'compliant' THEN 1 ELSE 0 END),
                           SUM(CASE WHEN status = 'non_compliant' THEN 1 ELSE 0 END)
                    FROM compliance_results 
                    WHERE framework = ? AND timestamp >= ?
                    GROUP BY framework
                ''', (framework.value, (datetime.now() - timedelta(days=1)).isoformat()))
            else:
                cursor = conn.execute('''
                    SELECT framework, AVG(score), COUNT(*), 
                           SUM(CASE WHEN status = 'compliant' THEN 1 ELSE 0 END),
                           SUM(CASE WHEN status = 'non_compliant' THEN 1 ELSE 0 END)
                    FROM compliance_results 
                    WHERE timestamp >= ?
                    GROUP BY framework
                ''', ((datetime.now() - timedelta(days=1)).isoformat(),))
            
            status = {}
            for row in cursor.fetchall():
                status[row[0]] = {
                    'average_score': row[1],
                    'total_rules': row[2],
                    'compliant_rules': row[3],
                    'non_compliant_rules': row[4],
                    'compliance_rate': (row[3] / row[2] * 100) if row[2] > 0 else 0
                }
            
            return status


# Global compliance monitor instance
compliance_monitor = ComplianceMonitor()


if __name__ == "__main__":
    # Test compliance monitoring
    print("Compliance Monitoring System Test")
    print("=" * 50)
    
    # Run compliance checks
    compliance_monitor._run_compliance_checks()
    
    # Generate GDPR report
    gdpr_report = compliance_monitor.generate_compliance_report(ComplianceFramework.GDPR)
    print(f"\nGDPR Compliance Report:")
    print(f"Overall Score: {gdpr_report.overall_score:.1f}/100")
    print(f"Compliant Rules: {gdpr_report.compliant_rules}/{gdpr_report.total_rules}")
    print(f"Executive Summary: {gdpr_report.executive_summary}")
    
    # Get compliance status
    status = compliance_monitor.get_compliance_status()
    print(f"\nCompliance Status: {json.dumps(status, indent=2)}")
    
    print("\nCompliance monitoring system test complete!")