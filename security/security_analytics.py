#!/usr/bin/env python3
"""
Security Analytics and Compliance Reporting

Advanced analytics and compliance reporting system for LeanVibe Agent Hive with:
- Comprehensive security metrics and KPIs
- Compliance reporting (SOC2, ISO27001, GDPR, etc.)
- Trend analysis and predictive insights
- Risk assessment and scoring
- Automated compliance checks and validation
"""

import asyncio
import logging
import json
import csv
import io
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict, Counter
from enum import Enum
import statistics
import uuid

from security.audit_logger import (
    SecurityAuditLogger, SecurityEvent, SecurityEventType, SecuritySeverity,
    AuditLogStatistics, audit_logger
)
from security.security_monitor import SecurityMonitor, SecurityIncident, security_monitor
from security.monitoring_integration import security_integration


logger = logging.getLogger(__name__)


class ComplianceFramework(Enum):
    """Supported compliance frameworks."""
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    NIST = "nist"
    CIS = "cis"
    OWASP = "owasp"


class RiskCategory(Enum):
    """Risk categories for assessment."""
    CONFIDENTIALITY = "confidentiality"
    INTEGRITY = "integrity"
    AVAILABILITY = "availability"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_PROTECTION = "data_protection"
    INCIDENT_RESPONSE = "incident_response"
    MONITORING = "monitoring"


@dataclass
class SecurityMetric:
    """Security metric definition and tracking."""
    metric_id: str
    name: str
    description: str
    category: str
    current_value: float
    target_value: float
    threshold_critical: float
    threshold_warning: float
    unit: str
    trend_direction: str  # "up", "down", "stable"
    last_updated: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceControl:
    """Compliance control definition and status."""
    control_id: str
    framework: ComplianceFramework
    name: str
    description: str
    requirement: str
    implementation_status: str  # "implemented", "partial", "not_implemented", "not_applicable"
    effectiveness_rating: str  # "effective", "partially_effective", "ineffective"
    last_assessed: datetime
    next_assessment: datetime
    evidence: List[str] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)
    remediation_actions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskAssessment:
    """Risk assessment result."""
    assessment_id: str
    risk_category: RiskCategory
    risk_score: float  # 0-100
    impact_score: float  # 0-10
    likelihood_score: float  # 0-10
    risk_level: str  # "low", "medium", "high", "critical"
    description: str
    mitigation_measures: List[str]
    residual_risk_score: float
    assessed_at: datetime
    assessed_by: str
    next_assessment: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceReport:
    """Comprehensive compliance report."""
    report_id: str
    framework: ComplianceFramework
    report_type: str  # "assessment", "audit", "certification"
    period_start: datetime
    period_end: datetime
    overall_compliance_score: float
    controls_assessed: int
    controls_compliant: int
    controls_non_compliant: int
    critical_findings: List[str]
    recommendations: List[str]
    generated_at: datetime
    generated_by: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecurityAnalytics:
    """
    Comprehensive security analytics and compliance reporting system.
    
    Features:
    - Real-time security metrics calculation and tracking
    - Compliance framework mapping and assessment
    - Risk assessment and scoring algorithms
    - Trend analysis and predictive insights
    - Automated report generation
    - Performance benchmarking
    """
    
    def __init__(self, 
                 audit_logger: SecurityAuditLogger,
                 security_monitor: SecurityMonitor,
                 config: Optional[Dict[str, Any]] = None):
        """Initialize security analytics system."""
        self.audit_logger = audit_logger
        self.security_monitor = security_monitor
        self.config = config or self._get_default_config()
        
        # Metrics and tracking
        self.security_metrics: Dict[str, SecurityMetric] = {}
        self.compliance_controls: Dict[str, ComplianceControl] = {}
        self.risk_assessments: Dict[str, RiskAssessment] = {}
        self.historical_data = defaultdict(list)
        
        # Compliance frameworks
        self.supported_frameworks = {
            ComplianceFramework.SOC2: self._load_soc2_controls(),
            ComplianceFramework.ISO27001: self._load_iso27001_controls(),
            ComplianceFramework.NIST: self._load_nist_controls(),
            ComplianceFramework.OWASP: self._load_owasp_controls()
        }
        
        # Analytics cache
        self.analytics_cache = {}
        self.cache_timestamps = {}
        
        # Background tasks
        self._analytics_task = None
        
        # Initialize system
        self._initialize_security_metrics()
        self._initialize_compliance_controls()
        self._start_analytics_processing()
        
        logger.info("SecurityAnalytics initialized with comprehensive reporting")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default analytics configuration."""
        return {
            "enabled": True,
            "real_time_analytics": True,
            "cache_ttl_minutes": 30,
            "metrics_update_interval_minutes": 15,
            "compliance_assessment_interval_days": 30,
            "risk_assessment_interval_days": 7,
            "trend_analysis_period_days": 30,
            "performance_benchmarking": True,
            "automated_reporting": True,
            "report_retention_days": 365
        }
    
    def _initialize_security_metrics(self):
        """Initialize core security metrics."""
        metrics = [
            SecurityMetric(
                metric_id="security_score",
                name="Overall Security Score",
                description="Composite security score based on all security events",
                category="security",
                current_value=0.0,
                target_value=95.0,
                threshold_critical=70.0,
                threshold_warning=85.0,
                unit="percentage",
                trend_direction="stable",
                last_updated=datetime.utcnow()
            ),
            SecurityMetric(
                metric_id="incident_count",
                name="Active Security Incidents",
                description="Number of active security incidents",
                category="incidents",
                current_value=0.0,
                target_value=0.0,
                threshold_critical=5.0,
                threshold_warning=2.0,
                unit="count",
                trend_direction="stable",
                last_updated=datetime.utcnow()
            ),
            SecurityMetric(
                metric_id="anomaly_detection_rate",
                name="Anomaly Detection Rate",
                description="Rate of anomaly detection per 1000 events",
                category="detection",
                current_value=0.0,
                target_value=5.0,
                threshold_critical=20.0,
                threshold_warning=10.0,
                unit="rate",
                trend_direction="stable",
                last_updated=datetime.utcnow()
            ),
            SecurityMetric(
                metric_id="authentication_failure_rate",
                name="Authentication Failure Rate",
                description="Percentage of failed authentication attempts",
                category="authentication",
                current_value=0.0,
                target_value=2.0,
                threshold_critical=10.0,
                threshold_warning=5.0,
                unit="percentage",
                trend_direction="stable",
                last_updated=datetime.utcnow()
            ),
            SecurityMetric(
                metric_id="mean_time_to_detection",
                name="Mean Time to Detection (MTTD)",
                description="Average time to detect security incidents",
                category="performance",
                current_value=0.0,
                target_value=300.0,  # 5 minutes
                threshold_critical=1800.0,  # 30 minutes
                threshold_warning=900.0,  # 15 minutes
                unit="seconds",
                trend_direction="stable",
                last_updated=datetime.utcnow()
            ),
            SecurityMetric(
                metric_id="mean_time_to_response",
                name="Mean Time to Response (MTTR)",
                description="Average time to respond to security incidents",
                category="performance",
                current_value=0.0,
                target_value=1800.0,  # 30 minutes
                threshold_critical=7200.0,  # 2 hours
                threshold_warning=3600.0,  # 1 hour
                unit="seconds",
                trend_direction="stable",
                last_updated=datetime.utcnow()
            )
        ]
        
        for metric in metrics:
            self.security_metrics[metric.metric_id] = metric
        
        logger.info(f"Initialized {len(metrics)} security metrics")
    
    def _initialize_compliance_controls(self):
        """Initialize compliance controls for all frameworks."""
        for framework, controls in self.supported_frameworks.items():
            for control in controls:
                control_key = f"{framework.value}_{control.control_id}"
                self.compliance_controls[control_key] = control
        
        logger.info(f"Initialized {len(self.compliance_controls)} compliance controls")
    
    def _load_soc2_controls(self) -> List[ComplianceControl]:
        """Load SOC 2 compliance controls."""
        return [
            ComplianceControl(
                control_id="CC6.1",
                framework=ComplianceFramework.SOC2,
                name="Logical and Physical Access Controls",
                description="Entity implements logical and physical access controls",
                requirement="Access controls are implemented to restrict access to assets",
                implementation_status="implemented",
                effectiveness_rating="effective",
                last_assessed=datetime.utcnow(),
                next_assessment=datetime.utcnow() + timedelta(days=90)
            ),
            ComplianceControl(
                control_id="CC6.2",
                framework=ComplianceFramework.SOC2,
                name="Authentication and Authorization",
                description="Prior to issuing credentials, registration and authorization are completed",
                requirement="User authentication and authorization processes are implemented",
                implementation_status="implemented",
                effectiveness_rating="effective",
                last_assessed=datetime.utcnow(),
                next_assessment=datetime.utcnow() + timedelta(days=90)
            ),
            ComplianceControl(
                control_id="CC6.7",
                framework=ComplianceFramework.SOC2,
                name="System Monitoring",
                description="Entity monitors system components and the operation of controls",
                requirement="Continuous monitoring of system components is implemented",
                implementation_status="implemented",
                effectiveness_rating="effective",
                last_assessed=datetime.utcnow(),
                next_assessment=datetime.utcnow() + timedelta(days=90)
            ),
            ComplianceControl(
                control_id="CC7.2",
                framework=ComplianceFramework.SOC2,
                name="System Monitoring and Alerting",
                description="Entity monitors system components for anomalies",
                requirement="Monitoring and alerting for security anomalies",
                implementation_status="implemented",
                effectiveness_rating="effective",
                last_assessed=datetime.utcnow(),
                next_assessment=datetime.utcnow() + timedelta(days=90)
            )
        ]
    
    def _load_iso27001_controls(self) -> List[ComplianceControl]:
        """Load ISO 27001 compliance controls."""
        return [
            ComplianceControl(
                control_id="A.9.1.1",
                framework=ComplianceFramework.ISO27001,
                name="Access Control Policy",
                description="Access control policy should be established",
                requirement="Documented access control policy",
                implementation_status="implemented",
                effectiveness_rating="effective",
                last_assessed=datetime.utcnow(),
                next_assessment=datetime.utcnow() + timedelta(days=90)
            ),
            ComplianceControl(
                control_id="A.12.6.1",
                framework=ComplianceFramework.ISO27001,
                name="Management of Technical Vulnerabilities",
                description="Information about technical vulnerabilities should be obtained",
                requirement="Vulnerability management process",
                implementation_status="implemented",
                effectiveness_rating="effective",
                last_assessed=datetime.utcnow(),
                next_assessment=datetime.utcnow() + timedelta(days=90)
            ),
            ComplianceControl(
                control_id="A.16.1.1",
                framework=ComplianceFramework.ISO27001,
                name="Incident Management Responsibilities",
                description="Management responsibilities and procedures should be established",
                requirement="Incident response procedures",
                implementation_status="implemented",
                effectiveness_rating="effective",
                last_assessed=datetime.utcnow(),
                next_assessment=datetime.utcnow() + timedelta(days=90)
            )
        ]
    
    def _load_nist_controls(self) -> List[ComplianceControl]:
        """Load NIST Cybersecurity Framework controls."""
        return [
            ComplianceControl(
                control_id="ID.AM-1",
                framework=ComplianceFramework.NIST,
                name="Asset Management",
                description="Physical devices and systems are inventoried",
                requirement="Asset inventory and management",
                implementation_status="implemented",
                effectiveness_rating="effective",
                last_assessed=datetime.utcnow(),
                next_assessment=datetime.utcnow() + timedelta(days=90)
            ),
            ComplianceControl(
                control_id="DE.AE-1",
                framework=ComplianceFramework.NIST,
                name="Anomaly Detection",
                description="Baseline of network operations is established",
                requirement="Anomaly and event detection",
                implementation_status="implemented",
                effectiveness_rating="effective",
                last_assessed=datetime.utcnow(),
                next_assessment=datetime.utcnow() + timedelta(days=90)
            ),
            ComplianceControl(
                control_id="RS.RP-1",
                framework=ComplianceFramework.NIST,
                name="Response Planning",
                description="Response plan is executed during or after an incident",
                requirement="Incident response planning and execution",
                implementation_status="implemented",
                effectiveness_rating="effective",
                last_assessed=datetime.utcnow(),
                next_assessment=datetime.utcnow() + timedelta(days=90)
            )
        ]
    
    def _load_owasp_controls(self) -> List[ComplianceControl]:
        """Load OWASP Top 10 controls."""
        return [
            ComplianceControl(
                control_id="A01-2021",
                framework=ComplianceFramework.OWASP,
                name="Broken Access Control",
                description="Access control enforces policy restrictions",
                requirement="Proper access control implementation",
                implementation_status="implemented",
                effectiveness_rating="effective",
                last_assessed=datetime.utcnow(),
                next_assessment=datetime.utcnow() + timedelta(days=90)
            ),
            ComplianceControl(
                control_id="A03-2021",
                framework=ComplianceFramework.OWASP,
                name="Injection",
                description="Application is protected against injection attacks",
                requirement="Input validation and sanitization",
                implementation_status="implemented",
                effectiveness_rating="effective",
                last_assessed=datetime.utcnow(),
                next_assessment=datetime.utcnow() + timedelta(days=90)
            ),
            ComplianceControl(
                control_id="A09-2021",
                framework=ComplianceFramework.OWASP,
                name="Security Logging and Monitoring Failures",
                description="Logging, detection, monitoring and active response",
                requirement="Comprehensive security logging and monitoring",
                implementation_status="implemented",
                effectiveness_rating="effective",
                last_assessed=datetime.utcnow(),
                next_assessment=datetime.utcnow() + timedelta(days=90)
            )
        ]
    
    def _start_analytics_processing(self):
        """Start background analytics processing."""
        async def analytics_processor():
            while True:
                try:
                    await self._update_security_metrics()
                    await self._update_compliance_assessments()
                    await self._update_risk_assessments()
                    await asyncio.sleep(self.config.get("metrics_update_interval_minutes", 15) * 60)
                except Exception as e:
                    logger.error(f"Analytics processor error: {e}")
                    await asyncio.sleep(300)  # Wait 5 minutes on error
        
        try:
            loop = asyncio.get_running_loop()
            self._analytics_task = loop.create_task(analytics_processor())
            logger.info("Security analytics processing started")
        except RuntimeError:
            logger.info("No event loop running, analytics will be processed on demand")
    
    async def _update_security_metrics(self):
        """Update all security metrics."""
        try:
            # Get audit statistics
            audit_stats = await self.audit_logger.get_statistics(hours=24)
            
            # Get monitoring status
            monitor_status = self.security_monitor.get_monitoring_status()
            
            # Update security score
            security_score = audit_stats.security_score
            self._update_metric("security_score", security_score)
            
            # Update incident count
            active_incidents = len([
                i for i in self.security_monitor.active_incidents.values()
                if i.status.value not in ["resolved", "false_positive"]
            ])
            self._update_metric("incident_count", active_incidents)
            
            # Update anomaly detection rate
            total_events = max(audit_stats.total_events, 1)
            anomaly_count = len(self.security_monitor.detected_anomalies)
            anomaly_rate = (anomaly_count / total_events) * 1000
            self._update_metric("anomaly_detection_rate", anomaly_rate)
            
            # Update authentication failure rate
            auth_failures = audit_stats.events_by_type.get("auth.login.failure", 0)
            auth_total = auth_failures + audit_stats.events_by_type.get("auth.login.success", 0)
            auth_failure_rate = (auth_failures / max(auth_total, 1)) * 100
            self._update_metric("authentication_failure_rate", auth_failure_rate)
            
            # Calculate MTTD and MTTR from incidents
            await self._calculate_response_times()
            
            logger.debug("Security metrics updated")
            
        except Exception as e:
            logger.error(f"Failed to update security metrics: {e}")
    
    def _update_metric(self, metric_id: str, new_value: float):
        """Update a specific metric with trend analysis."""
        if metric_id not in self.security_metrics:
            return
        
        metric = self.security_metrics[metric_id]
        old_value = metric.current_value
        
        # Update value
        metric.current_value = new_value
        metric.last_updated = datetime.utcnow()
        
        # Update trend
        if new_value > old_value * 1.05:
            metric.trend_direction = "up"
        elif new_value < old_value * 0.95:
            metric.trend_direction = "down"
        else:
            metric.trend_direction = "stable"
        
        # Store historical data
        self.historical_data[metric_id].append({
            "timestamp": metric.last_updated.isoformat(),
            "value": new_value
        })
        
        # Keep only last 1000 data points
        if len(self.historical_data[metric_id]) > 1000:
            self.historical_data[metric_id] = self.historical_data[metric_id][-1000:]
    
    async def _calculate_response_times(self):
        """Calculate mean time to detection and response."""
        try:
            incidents = list(self.security_monitor.active_incidents.values())
            
            if not incidents:
                return
            
            # Calculate MTTD (time from first event to incident creation)
            detection_times = []
            response_times = []
            
            for incident in incidents:
                # MTTD: time from first_seen to created_at
                if incident.first_seen and incident.created_at:
                    detection_time = (incident.created_at - incident.first_seen).total_seconds()
                    detection_times.append(max(detection_time, 0))
                
                # MTTR: time from created_at to resolved_at (for resolved incidents)
                if incident.resolved_at and incident.created_at:
                    response_time = (incident.resolved_at - incident.created_at).total_seconds()
                    response_times.append(response_time)
            
            if detection_times:
                mttd = statistics.mean(detection_times)
                self._update_metric("mean_time_to_detection", mttd)
            
            if response_times:
                mttr = statistics.mean(response_times)
                self._update_metric("mean_time_to_response", mttr)
                
        except Exception as e:
            logger.error(f"Failed to calculate response times: {e}")
    
    async def _update_compliance_assessments(self):
        """Update compliance control assessments."""
        try:
            # Assess controls based on current system state
            for control_key, control in self.compliance_controls.items():
                if control.next_assessment <= datetime.utcnow():
                    await self._assess_compliance_control(control)
                    
        except Exception as e:
            logger.error(f"Failed to update compliance assessments: {e}")
    
    async def _assess_compliance_control(self, control: ComplianceControl):
        """Assess a specific compliance control."""
        try:
            # Automated assessment based on control type
            assessment_result = await self._automated_control_assessment(control)
            
            # Update control status
            control.implementation_status = assessment_result.get("status", "implemented")
            control.effectiveness_rating = assessment_result.get("effectiveness", "effective")
            control.last_assessed = datetime.utcnow()
            control.next_assessment = datetime.utcnow() + timedelta(days=90)
            control.findings = assessment_result.get("findings", [])
            
            logger.debug(f"Assessed compliance control: {control.control_id}")
            
        except Exception as e:
            logger.error(f"Failed to assess compliance control {control.control_id}: {e}")
    
    async def _automated_control_assessment(self, control: ComplianceControl) -> Dict[str, Any]:
        """Perform automated assessment of compliance control."""
        findings = []
        effectiveness = "effective"
        status = "implemented"
        
        # Get recent audit statistics
        audit_stats = await self.audit_logger.get_statistics(hours=24)
        
        # Control-specific assessments
        if "access" in control.name.lower():
            # Assess access control effectiveness
            auth_failures = audit_stats.events_by_type.get("auth.login.failure", 0)
            if auth_failures > 50:
                findings.append("High number of authentication failures detected")
                effectiveness = "partially_effective"
        
        elif "monitoring" in control.name.lower():
            # Assess monitoring effectiveness
            if audit_stats.total_events == 0:
                findings.append("No security events logged in the assessment period")
                effectiveness = "ineffective"
            elif audit_stats.security_score < 80:
                findings.append("Low security score indicates monitoring gaps")
                effectiveness = "partially_effective"
        
        elif "incident" in control.name.lower():
            # Assess incident response
            active_incidents = len([
                i for i in self.security_monitor.active_incidents.values()
                if i.status.value not in ["resolved", "false_positive"]
            ])
            if active_incidents > 5:
                findings.append("High number of unresolved security incidents")
                effectiveness = "partially_effective"
        
        return {
            "status": status,
            "effectiveness": effectiveness,
            "findings": findings
        }
    
    async def _update_risk_assessments(self):
        """Update risk assessments for all categories."""
        try:
            for category in RiskCategory:
                assessment = await self._calculate_risk_assessment(category)
                self.risk_assessments[f"{category.value}_current"] = assessment
                
        except Exception as e:
            logger.error(f"Failed to update risk assessments: {e}")
    
    async def _calculate_risk_assessment(self, category: RiskCategory) -> RiskAssessment:
        """Calculate risk assessment for a specific category."""
        try:
            # Get relevant metrics and data
            audit_stats = await self.audit_logger.get_statistics(hours=24)
            
            # Category-specific risk calculation
            if category == RiskCategory.AUTHENTICATION:
                impact_score = 8.0  # High impact for auth failures
                likelihood_score = min(audit_stats.events_by_type.get("auth.login.failure", 0) / 10.0, 10.0)
                description = "Authentication security risk based on failed login attempts"
                mitigation_measures = ["Implement MFA", "Account lockout policies", "Rate limiting"]
                
            elif category == RiskCategory.MONITORING:
                impact_score = 7.0
                likelihood_score = 10.0 - (audit_stats.security_score / 10.0)
                description = "Monitoring effectiveness risk based on security score"
                mitigation_measures = ["Enhanced monitoring", "Alert tuning", "Response automation"]
                
            elif category == RiskCategory.INCIDENT_RESPONSE:
                active_incidents = len(self.security_monitor.active_incidents)
                impact_score = 6.0
                likelihood_score = min(active_incidents / 2.0, 10.0)
                description = "Incident response risk based on active incidents"
                mitigation_measures = ["Incident response training", "Automation", "Resource allocation"]
                
            else:
                # Default risk calculation
                impact_score = 5.0
                likelihood_score = 5.0
                description = f"General risk assessment for {category.value}"
                mitigation_measures = ["Regular assessment", "Control implementation", "Monitoring"]
            
            # Calculate overall risk score
            risk_score = (impact_score * likelihood_score) / 10.0 * 10.0  # Scale to 0-100
            
            # Determine risk level
            if risk_score >= 70:
                risk_level = "critical"
            elif risk_score >= 50:
                risk_level = "high"
            elif risk_score >= 30:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            # Calculate residual risk (assume 30% reduction with current controls)
            residual_risk_score = risk_score * 0.7
            
            return RiskAssessment(
                assessment_id=str(uuid.uuid4()),
                risk_category=category,
                risk_score=risk_score,
                impact_score=impact_score,
                likelihood_score=likelihood_score,
                risk_level=risk_level,
                description=description,
                mitigation_measures=mitigation_measures,
                residual_risk_score=residual_risk_score,
                assessed_at=datetime.utcnow(),
                assessed_by="automated_system",
                next_assessment=datetime.utcnow() + timedelta(days=7)
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate risk assessment for {category.value}: {e}")
            # Return default assessment
            return RiskAssessment(
                assessment_id=str(uuid.uuid4()),
                risk_category=category,
                risk_score=50.0,
                impact_score=5.0,
                likelihood_score=5.0,
                risk_level="medium",
                description=f"Default risk assessment for {category.value}",
                mitigation_measures=["Regular review required"],
                residual_risk_score=35.0,
                assessed_at=datetime.utcnow(),
                assessed_by="automated_system",
                next_assessment=datetime.utcnow() + timedelta(days=7)
            )
    
    async def generate_compliance_report(self, framework: ComplianceFramework, 
                                       report_type: str = "assessment") -> ComplianceReport:
        """Generate comprehensive compliance report."""
        try:
            # Get framework controls
            framework_controls = [
                control for control in self.compliance_controls.values()
                if control.framework == framework
            ]
            
            # Calculate compliance metrics
            total_controls = len(framework_controls)
            compliant_controls = len([
                c for c in framework_controls
                if c.implementation_status == "implemented" and c.effectiveness_rating == "effective"
            ])
            non_compliant_controls = total_controls - compliant_controls
            
            # Calculate overall compliance score
            compliance_score = (compliant_controls / max(total_controls, 1)) * 100
            
            # Gather critical findings
            critical_findings = []
            recommendations = []
            
            for control in framework_controls:
                if control.effectiveness_rating == "ineffective":
                    critical_findings.extend(control.findings)
                    recommendations.append(f"Review and improve {control.name}")
                elif control.effectiveness_rating == "partially_effective":
                    recommendations.append(f"Enhance {control.name} implementation")
            
            # Create report
            report = ComplianceReport(
                report_id=str(uuid.uuid4()),
                framework=framework,
                report_type=report_type,
                period_start=datetime.utcnow() - timedelta(days=30),
                period_end=datetime.utcnow(),
                overall_compliance_score=compliance_score,
                controls_assessed=total_controls,
                controls_compliant=compliant_controls,
                controls_non_compliant=non_compliant_controls,
                critical_findings=critical_findings[:10],  # Limit to top 10
                recommendations=recommendations[:10],  # Limit to top 10
                generated_at=datetime.utcnow(),
                generated_by="automated_system",
                metadata={
                    "framework_version": "latest",
                    "assessment_method": "automated",
                    "data_sources": ["audit_logs", "security_monitor", "compliance_controls"]
                }
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report for {framework.value}: {e}")
            raise
    
    async def generate_security_analytics_report(self, period_days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive security analytics report."""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=period_days)
            
            # Get audit statistics
            audit_stats = await self.audit_logger.get_statistics(hours=period_days * 24)
            
            # Get current metrics
            current_metrics = {
                metric_id: {
                    "name": metric.name,
                    "current_value": metric.current_value,
                    "target_value": metric.target_value,
                    "unit": metric.unit,
                    "trend": metric.trend_direction,
                    "status": self._get_metric_status(metric)
                }
                for metric_id, metric in self.security_metrics.items()
            }
            
            # Get risk assessments
            current_risks = {
                assessment_id: {
                    "category": assessment.risk_category.value,
                    "risk_score": assessment.risk_score,
                    "risk_level": assessment.risk_level,
                    "description": assessment.description
                }
                for assessment_id, assessment in self.risk_assessments.items()
            }
            
            # Calculate trend analysis
            trends = await self._calculate_security_trends(period_days)
            
            # Generate insights and recommendations
            insights = await self._generate_security_insights(audit_stats, current_metrics, current_risks)
            
            report = {
                "report_id": str(uuid.uuid4()),
                "generated_at": datetime.utcnow().isoformat(),
                "period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "days": period_days
                },
                "executive_summary": {
                    "overall_security_score": audit_stats.security_score,
                    "threat_level": audit_stats.threat_level,
                    "compliance_status": audit_stats.compliance_status,
                    "total_events": audit_stats.total_events,
                    "active_incidents": len(self.security_monitor.active_incidents),
                    "critical_findings": len([r for r in current_risks.values() if r["risk_level"] == "critical"])
                },
                "security_metrics": current_metrics,
                "risk_assessments": current_risks,
                "trends": trends,
                "insights": insights,
                "audit_statistics": {
                    "events_by_type": audit_stats.events_by_type,
                    "events_by_severity": audit_stats.events_by_severity,
                    "top_users": audit_stats.top_users,
                    "top_sources": audit_stats.top_sources
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate security analytics report: {e}")
            raise
    
    def _get_metric_status(self, metric: SecurityMetric) -> str:
        """Get status of a metric based on thresholds."""
        if metric.current_value <= metric.threshold_critical:
            return "critical"
        elif metric.current_value <= metric.threshold_warning:
            return "warning"
        elif metric.current_value >= metric.target_value:
            return "excellent"
        else:
            return "good"
    
    async def _calculate_security_trends(self, period_days: int) -> Dict[str, Any]:
        """Calculate security trends over the specified period."""
        trends = {}
        
        for metric_id, historical_data in self.historical_data.items():
            if len(historical_data) < 2:
                continue
            
            # Calculate trend over period
            values = [point["value"] for point in historical_data[-period_days:]]
            
            if len(values) >= 2:
                # Simple linear trend
                start_value = values[0]
                end_value = values[-1]
                change_percent = ((end_value - start_value) / max(start_value, 0.1)) * 100
                
                trends[metric_id] = {
                    "change_percent": round(change_percent, 2),
                    "direction": "improving" if change_percent > 5 else "declining" if change_percent < -5 else "stable",
                    "start_value": start_value,
                    "end_value": end_value
                }
        
        return trends
    
    async def _generate_security_insights(self, audit_stats, metrics, risks) -> List[str]:
        """Generate security insights and recommendations."""
        insights = []
        
        # Security score insights
        if audit_stats.security_score < 70:
            insights.append("Security score is below acceptable threshold - immediate attention required")
        elif audit_stats.security_score < 85:
            insights.append("Security score needs improvement - review security controls")
        
        # Event analysis insights
        critical_events = audit_stats.events_by_severity.get("critical", 0)
        if critical_events > 0:
            insights.append(f"{critical_events} critical security events detected - investigate immediately")
        
        # Incident insights
        active_incidents = len(self.security_monitor.active_incidents)
        if active_incidents > 2:
            insights.append(f"{active_incidents} active security incidents - review incident response")
        
        # Risk insights
        high_risks = len([r for r in risks.values() if r["risk_level"] in ["critical", "high"]])
        if high_risks > 0:
            insights.append(f"{high_risks} high or critical risks identified - prioritize mitigation")
        
        # Authentication insights
        auth_failures = audit_stats.events_by_type.get("auth.login.failure", 0)
        if auth_failures > 100:
            insights.append("High number of authentication failures - consider implementing additional controls")
        
        return insights[:10]  # Limit to top 10 insights
    
    def export_compliance_report_csv(self, report: ComplianceReport) -> str:
        """Export compliance report to CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["Compliance Report", report.framework.value.upper()])
        writer.writerow(["Report ID", report.report_id])
        writer.writerow(["Generated", report.generated_at.isoformat()])
        writer.writerow(["Period", f"{report.period_start.date()} to {report.period_end.date()}"])
        writer.writerow([])
        
        # Write summary
        writer.writerow(["Summary"])
        writer.writerow(["Overall Compliance Score", f"{report.overall_compliance_score:.1f}%"])
        writer.writerow(["Controls Assessed", report.controls_assessed])
        writer.writerow(["Controls Compliant", report.controls_compliant])
        writer.writerow(["Controls Non-Compliant", report.controls_non_compliant])
        writer.writerow([])
        
        # Write findings
        writer.writerow(["Critical Findings"])
        for finding in report.critical_findings:
            writer.writerow(["", finding])
        writer.writerow([])
        
        # Write recommendations
        writer.writerow(["Recommendations"])
        for recommendation in report.recommendations:
            writer.writerow(["", recommendation])
        
        return output.getvalue()
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get comprehensive analytics summary."""
        return {
            "security_metrics": {
                metric_id: {
                    "name": metric.name,
                    "current_value": metric.current_value,
                    "target_value": metric.target_value,
                    "status": self._get_metric_status(metric),
                    "trend": metric.trend_direction
                }
                for metric_id, metric in self.security_metrics.items()
            },
            "compliance_frameworks": {
                framework.value: {
                    "total_controls": len([c for c in self.compliance_controls.values() if c.framework == framework]),
                    "compliant_controls": len([
                        c for c in self.compliance_controls.values()
                        if c.framework == framework and c.implementation_status == "implemented" and c.effectiveness_rating == "effective"
                    ])
                }
                for framework in ComplianceFramework
            },
            "risk_summary": {
                "total_assessments": len(self.risk_assessments),
                "high_risks": len([r for r in self.risk_assessments.values() if r.risk_level in ["critical", "high"]]),
                "medium_risks": len([r for r in self.risk_assessments.values() if r.risk_level == "medium"]),
                "low_risks": len([r for r in self.risk_assessments.values() if r.risk_level == "low"])
            },
            "system_status": {
                "analytics_enabled": self.config.get("enabled", True),
                "real_time_processing": self.config.get("real_time_analytics", True),
                "last_update": datetime.utcnow().isoformat()
            }
        }


# Global analytics instance
security_analytics = SecurityAnalytics(audit_logger, security_monitor)


# Convenience functions for easy access
async def get_security_analytics_report(period_days: int = 30) -> Dict[str, Any]:
    """Get comprehensive security analytics report."""
    return await security_analytics.generate_security_analytics_report(period_days)


async def get_compliance_report(framework: ComplianceFramework) -> ComplianceReport:
    """Get compliance report for specific framework."""
    return await security_analytics.generate_compliance_report(framework)


def get_analytics_summary() -> Dict[str, Any]:
    """Get analytics summary."""
    return security_analytics.get_analytics_summary()


if __name__ == "__main__":
    # Example usage and testing
    async def main():
        analytics = SecurityAnalytics(audit_logger, security_monitor)
        
        print("Generating security analytics report...")
        report = await analytics.generate_security_analytics_report(7)
        
        print(f"Report ID: {report['report_id']}")
        print(f"Security Score: {report['executive_summary']['overall_security_score']}")
        print(f"Total Events: {report['executive_summary']['total_events']}")
        print(f"Active Incidents: {report['executive_summary']['active_incidents']}")
        
        print("\nGenerating SOC 2 compliance report...")
        soc2_report = await analytics.generate_compliance_report(ComplianceFramework.SOC2)
        
        print(f"SOC 2 Compliance Score: {soc2_report.overall_compliance_score:.1f}%")
        print(f"Controls Assessed: {soc2_report.controls_assessed}")
        print(f"Compliant Controls: {soc2_report.controls_compliant}")
        
        print("\nAnalytics Summary:")
        summary = analytics.get_analytics_summary()
        print(f"Security Metrics: {len(summary['security_metrics'])}")
        print(f"Compliance Frameworks: {len(summary['compliance_frameworks'])}")
        print(f"Risk Assessments: {summary['risk_summary']['total_assessments']}")
    
    # Run test
    asyncio.run(main())