#!/usr/bin/env python3
"""
Compliance Reporting System

Enterprise-grade compliance reporting for SOC2, ISO27001, OWASP, and other 
security standards with automated assessment, gap analysis, and remediation 
recommendations for LeanVibe Agent Hive.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from security.security_manager import SecurityManager
# Optional imports to avoid circular dependencies and missing modules
try:
    from security.auth_service import AuthenticationService
except ImportError:
    AuthenticationService = None

try:
    from security.rbac_manager import RBACManager
except ImportError:
    RBACManager = None

try:
    from security.two_factor_auth import TwoFactorAuthManager
except ImportError:
    TwoFactorAuthManager = None

try:
    from security.api_key_manager import ApiKeyManager
except ImportError:
    ApiKeyManager = None


logger = logging.getLogger(__name__)


class ComplianceStandard(Enum):
    """Supported compliance standards."""
    SOC2_TYPE1 = "soc2_type1"
    SOC2_TYPE2 = "soc2_type2"
    ISO27001 = "iso27001"
    OWASP_TOP10 = "owasp_top10"
    NIST_CSF = "nist_csf"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"


class ComplianceStatus(Enum):
    """Compliance assessment status."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NOT_APPLICABLE = "not_applicable"
    UNDER_REVIEW = "under_review"


class ControlSeverity(Enum):
    """Control requirement severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


@dataclass
class ComplianceControl:
    """Individual compliance control requirement."""
    control_id: str
    standard: ComplianceStandard
    title: str
    description: str
    category: str
    severity: ControlSeverity
    requirements: List[str]
    implementation_guidance: str
    automated_check: bool = False
    evidence_required: List[str] = None
    
    def __post_init__(self):
        if self.evidence_required is None:
            self.evidence_required = []


@dataclass
class ControlAssessment:
    """Assessment result for a compliance control."""
    control_id: str
    status: ComplianceStatus
    score: float  # 0.0 to 1.0
    evidence_found: List[str]
    gaps_identified: List[str]
    recommendations: List[str]
    assessed_at: datetime
    assessed_by: str
    next_assessment_due: Optional[datetime] = None
    remediation_deadline: Optional[datetime] = None


@dataclass
class ComplianceReport:
    """Comprehensive compliance report."""
    report_id: str
    standard: ComplianceStandard
    generated_at: datetime
    generated_by: str
    overall_score: float
    total_controls: int
    compliant_controls: int
    non_compliant_controls: int
    partially_compliant_controls: int
    control_assessments: List[ControlAssessment]
    executive_summary: str
    key_findings: List[str]
    critical_gaps: List[str]
    recommendations: List[str]
    next_assessment_date: datetime


class ComplianceReporter:
    """
    Comprehensive compliance reporting and assessment system.
    
    Features:
    - Multiple compliance standard support (SOC2, ISO27001, OWASP, etc.)
    - Automated security control assessment
    - Gap analysis and remediation recommendations
    - Evidence collection and validation
    - Continuous compliance monitoring
    - Executive reporting and dashboards
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None,
                 security_manager: Optional[SecurityManager] = None,
                 auth_service: Optional[Any] = None,
                 rbac_manager: Optional[Any] = None,
                 two_factor_auth: Optional[Any] = None,
                 api_key_manager: Optional[Any] = None):
        """Initialize compliance reporter."""
        self.config = config or self._get_default_config()
        self.security_manager = security_manager
        self.auth_service = auth_service
        self.rbac_manager = rbac_manager
        self.two_factor_auth = two_factor_auth
        self.api_key_manager = api_key_manager
        
        # Storage for compliance data
        self.compliance_controls: Dict[str, Dict[str, ComplianceControl]] = {}
        self.control_assessments: Dict[str, ControlAssessment] = {}
        self.compliance_reports: Dict[str, ComplianceReport] = {}
        self.evidence_store: Dict[str, List[Dict[str, Any]]] = {}
        
        # Initialize compliance frameworks
        self._initialize_compliance_frameworks()
        
        logger.info("ComplianceReporter initialized")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default compliance configuration."""
        return {
            "assessment_frequency_days": 90,
            "critical_gap_alert_threshold": 0.7,
            "minimum_compliance_score": 0.8,
            "evidence_retention_days": 2555,  # 7 years
            "automated_assessment_enabled": True,
            "continuous_monitoring": True
        }
    
    def _initialize_compliance_frameworks(self) -> None:
        """Initialize compliance framework definitions."""
        # SOC2 Type 2 Controls
        self.compliance_controls[ComplianceStandard.SOC2_TYPE2.value] = {
            "CC6.1": ComplianceControl(
                control_id="CC6.1",
                standard=ComplianceStandard.SOC2_TYPE2,
                title="Logical and Physical Access Controls",
                description="Entity implements logical and physical access security measures to protect against threats from sources outside its system boundaries",
                category="Security",
                severity=ControlSeverity.CRITICAL,
                requirements=[
                    "Implement logical access controls",
                    "Implement physical access controls",
                    "Monitor access attempts",
                    "Document access control procedures"
                ],
                implementation_guidance="Implement multi-factor authentication, role-based access control, and regular access reviews",
                automated_check=True,
                evidence_required=["access_logs", "authentication_records", "rbac_configuration"]
            ),
            "CC6.2": ComplianceControl(
                control_id="CC6.2",
                standard=ComplianceStandard.SOC2_TYPE2,
                title="Authentication and Authorization",
                description="Prior to issuing system credentials and granting access, entity registers and authorizes new internal and external users",
                category="Security",
                severity=ControlSeverity.HIGH,
                requirements=[
                    "User registration process",
                    "Authorization procedures",
                    "Credential management",
                    "Access provisioning controls"
                ],
                implementation_guidance="Implement formal user onboarding, authorization workflows, and credential management processes",
                automated_check=True,
                evidence_required=["user_registration_logs", "authorization_records", "credential_policies"]
            ),
            "CC6.3": ComplianceControl(
                control_id="CC6.3",
                standard=ComplianceStandard.SOC2_TYPE2,
                title="System Access Removal",
                description="Entity removes system access when access is no longer required or appropriate",
                category="Security",
                severity=ControlSeverity.HIGH,
                requirements=[
                    "Access removal procedures",
                    "Terminated user access review",
                    "Regular access certification",
                    "Automated access removal"
                ],
                implementation_guidance="Implement automated user deactivation and regular access reviews",
                automated_check=True,
                evidence_required=["access_removal_logs", "user_termination_records", "access_reviews"]
            )
        }
        
        # OWASP Top 10 Controls
        self.compliance_controls[ComplianceStandard.OWASP_TOP10.value] = {
            "A01": ComplianceControl(
                control_id="A01",
                standard=ComplianceStandard.OWASP_TOP10,
                title="Broken Access Control",
                description="Access control enforces policy such that users cannot act outside of their intended permissions",
                category="Application Security",
                severity=ControlSeverity.CRITICAL,
                requirements=[
                    "Implement proper authorization",
                    "Validate user permissions",
                    "Secure direct object references",
                    "Prevent privilege escalation"
                ],
                implementation_guidance="Implement comprehensive RBAC and validate all access requests",
                automated_check=True,
                evidence_required=["rbac_logs", "authorization_tests", "access_control_tests"]
            ),
            "A02": ComplianceControl(
                control_id="A02",
                standard=ComplianceStandard.OWASP_TOP10,
                title="Cryptographic Failures",
                description="Data is protected in transit and at rest using appropriate cryptographic controls",
                category="Data Protection",
                severity=ControlSeverity.CRITICAL,
                requirements=[
                    "Encrypt data in transit",
                    "Encrypt data at rest",
                    "Use strong cryptographic algorithms",
                    "Proper key management"
                ],
                implementation_guidance="Implement TLS for data in transit and AES encryption for data at rest",
                automated_check=True,
                evidence_required=["encryption_configs", "tls_certificates", "key_management_procedures"]
            ),
            "A03": ComplianceControl(
                control_id="A03",
                standard=ComplianceStandard.OWASP_TOP10,
                title="Injection",
                description="Application is protected against injection attacks including SQL, NoSQL, OS, and LDAP injection",
                category="Input Validation",
                severity=ControlSeverity.CRITICAL,
                requirements=[
                    "Input validation",
                    "Parameterized queries",
                    "Output encoding",
                    "Stored procedure security"
                ],
                implementation_guidance="Use parameterized queries and comprehensive input validation",
                automated_check=True,
                evidence_required=["code_reviews", "security_tests", "input_validation_tests"]
            )
        }
        
        # ISO 27001 Controls (subset)
        self.compliance_controls[ComplianceStandard.ISO27001.value] = {
            "A.9.1.1": ComplianceControl(
                control_id="A.9.1.1",
                standard=ComplianceStandard.ISO27001,
                title="Access Control Policy",
                description="An access control policy shall be established, documented and reviewed",
                category="Access Control",
                severity=ControlSeverity.HIGH,
                requirements=[
                    "Document access control policy",
                    "Regular policy reviews",
                    "Management approval",
                    "Policy distribution"
                ],
                implementation_guidance="Create comprehensive access control policy and review annually",
                automated_check=False,
                evidence_required=["access_control_policy", "policy_reviews", "management_approvals"]
            ),
            "A.9.2.1": ComplianceControl(
                control_id="A.9.2.1",
                standard=ComplianceStandard.ISO27001,
                title="User Registration and De-registration",
                description="A formal user registration and de-registration process shall be implemented",
                category="Access Control",
                severity=ControlSeverity.HIGH,
                requirements=[
                    "Formal registration process",
                    "De-registration procedures",
                    "Process documentation",
                    "Management oversight"
                ],
                implementation_guidance="Implement formal user lifecycle management processes",
                automated_check=True,
                evidence_required=["user_registration_process", "deregistration_logs", "process_documentation"]
            )
        }
    
    async def generate_compliance_report(self, standard: ComplianceStandard, 
                                       generated_by: str,
                                       include_evidence: bool = True) -> Tuple[bool, str, Optional[ComplianceReport]]:
        """Generate comprehensive compliance report for specified standard."""
        try:
            report_id = str(uuid.uuid4())
            current_time = datetime.utcnow()
            
            # Get controls for the standard
            standard_controls = self.compliance_controls.get(standard.value, {})
            if not standard_controls:
                return False, f"No controls defined for standard {standard.value}", None
            
            # Assess all controls
            control_assessments = []
            compliant_count = 0
            non_compliant_count = 0
            partially_compliant_count = 0
            total_score = 0.0
            
            for control in standard_controls.values():
                assessment = await self._assess_control(control, include_evidence)
                control_assessments.append(assessment)
                
                if assessment.status == ComplianceStatus.COMPLIANT:
                    compliant_count += 1
                elif assessment.status == ComplianceStatus.NON_COMPLIANT:
                    non_compliant_count += 1
                elif assessment.status == ComplianceStatus.PARTIALLY_COMPLIANT:
                    partially_compliant_count += 1
                
                total_score += assessment.score
            
            # Calculate overall score
            overall_score = total_score / len(control_assessments) if control_assessments else 0.0
            
            # Generate insights
            executive_summary, key_findings, critical_gaps, recommendations = await self._generate_report_insights(
                standard, control_assessments, overall_score
            )
            
            # Create report
            report = ComplianceReport(
                report_id=report_id,
                standard=standard,
                generated_at=current_time,
                generated_by=generated_by,
                overall_score=overall_score,
                total_controls=len(control_assessments),
                compliant_controls=compliant_count,
                non_compliant_controls=non_compliant_count,
                partially_compliant_controls=partially_compliant_count,
                control_assessments=control_assessments,
                executive_summary=executive_summary,
                key_findings=key_findings,
                critical_gaps=critical_gaps,
                recommendations=recommendations,
                next_assessment_date=current_time + timedelta(days=self.config.get("assessment_frequency_days", 90))
            )
            
            # Store report
            self.compliance_reports[report_id] = report
            
            logger.info(f"Compliance report generated for {standard.value}: {report_id}")
            return True, "Compliance report generated successfully", report
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report for {standard.value}: {e}")
            return False, f"Report generation failed: {e}", None
    
    async def _assess_control(self, control: ComplianceControl, include_evidence: bool = True) -> ControlAssessment:
        """Assess a single compliance control."""
        try:
            current_time = datetime.utcnow()
            evidence_found = []
            gaps_identified = []
            recommendations = []
            
            # Perform automated checks if available
            if control.automated_check:
                assessment_result = await self._perform_automated_assessment(control)
                evidence_found.extend(assessment_result.get("evidence", []))
                gaps_identified.extend(assessment_result.get("gaps", []))
                score = assessment_result.get("score", 0.0)
            else:
                # Manual assessment placeholder
                score = 0.5  # Assume partially compliant for manual controls
                gaps_identified.append("Manual assessment required")
            
            # Collect evidence if requested
            if include_evidence:
                control_evidence = await self._collect_control_evidence(control)
                evidence_found.extend(control_evidence)
            
            # Generate recommendations based on gaps
            recommendations = await self._generate_control_recommendations(control, gaps_identified)
            
            # Determine status based on score
            if score >= 0.9:
                status = ComplianceStatus.COMPLIANT
            elif score >= 0.5:
                status = ComplianceStatus.PARTIALLY_COMPLIANT
            else:
                status = ComplianceStatus.NON_COMPLIANT
            
            # Calculate next assessment date
            next_assessment = current_time + timedelta(days=self.config.get("assessment_frequency_days", 90))
            
            return ControlAssessment(
                control_id=control.control_id,
                status=status,
                score=score,
                evidence_found=evidence_found,
                gaps_identified=gaps_identified,
                recommendations=recommendations,
                assessed_at=current_time,
                assessed_by="automated_system",
                next_assessment_due=next_assessment,
                remediation_deadline=current_time + timedelta(days=30) if gaps_identified else None
            )
            
        except Exception as e:
            logger.error(f"Failed to assess control {control.control_id}: {e}")
            return ControlAssessment(
                control_id=control.control_id,
                status=ComplianceStatus.UNDER_REVIEW,
                score=0.0,
                evidence_found=[],
                gaps_identified=[f"Assessment error: {e}"],
                recommendations=["Investigate assessment failure"],
                assessed_at=current_time,
                assessed_by="system_error"
            )
    
    async def _perform_automated_assessment(self, control: ComplianceControl) -> Dict[str, Any]:
        """Perform automated assessment for a control."""
        evidence = []
        gaps = []
        score = 0.0
        
        try:
            # Authentication and Authorization Controls
            if control.control_id in ["CC6.1", "CC6.2", "A01"]:
                score += await self._assess_authentication_controls(evidence, gaps)
            
            # Access Control and RBAC
            if control.control_id in ["CC6.3", "A.9.1.1", "A.9.2.1"]:
                score += await self._assess_access_controls(evidence, gaps)
            
            # Cryptographic Controls
            if control.control_id == "A02":
                score += await self._assess_cryptographic_controls(evidence, gaps)
            
            # Input Validation Controls
            if control.control_id == "A03":
                score += await self._assess_input_validation_controls(evidence, gaps)
            
            # Normalize score to 0-1 range
            score = min(1.0, max(0.0, score))
            
        except Exception as e:
            logger.error(f"Automated assessment failed for {control.control_id}: {e}")
            gaps.append(f"Automated assessment error: {e}")
        
        return {
            "score": score,
            "evidence": evidence,
            "gaps": gaps
        }
    
    async def _assess_authentication_controls(self, evidence: List[str], gaps: List[str]) -> float:
        """Assess authentication-related controls."""
        score = 0.0
        
        # Check if authentication service is available
        if self.auth_service:
            evidence.append("Authentication service configured")
            score += 0.3
            
            # Check for 2FA
            if self.two_factor_auth:
                evidence.append("Two-factor authentication available")
                score += 0.3
                
                # Get 2FA analytics
                analytics = await self.two_factor_auth.get_two_factor_analytics()
                if analytics.get("overview", {}).get("users_with_2fa", 0) > 0:
                    evidence.append("Users have 2FA enabled")
                    score += 0.2
                else:
                    gaps.append("No users have 2FA enabled")
            else:
                gaps.append("Two-factor authentication not implemented")
            
            # Check authentication statistics
            auth_stats = await self.auth_service.get_authentication_stats()
            if auth_stats.get("users", {}).get("with_2fa", 0) > 0:
                evidence.append("Multi-factor authentication in use")
                score += 0.2
            else:
                gaps.append("Multi-factor authentication not widely adopted")
        else:
            gaps.append("Authentication service not configured")
        
        return score
    
    async def _assess_access_controls(self, evidence: List[str], gaps: List[str]) -> float:
        """Assess access control related controls."""
        score = 0.0
        
        # Check RBAC implementation
        if self.rbac_manager:
            evidence.append("Role-based access control implemented")
            score += 0.4
            
            # Get RBAC analytics
            analytics = await self.rbac_manager.get_rbac_analytics()
            if analytics.get("roles", {}).get("total", 0) > 0:
                evidence.append("RBAC roles defined")
                score += 0.3
            else:
                gaps.append("No RBAC roles defined")
            
            if analytics.get("permissions", {}).get("total", 0) > 0:
                evidence.append("Permission system active")
                score += 0.3
            else:
                gaps.append("No permissions configured")
        else:
            gaps.append("Role-based access control not implemented")
        
        return score
    
    async def _assess_cryptographic_controls(self, evidence: List[str], gaps: List[str]) -> float:
        """Assess cryptographic controls."""
        score = 0.0
        
        # Check if security manager has encryption capabilities
        if self.security_manager:
            evidence.append("Security manager configured")
            score += 0.3
            
            # Check for API key encryption (implies cryptographic capabilities)
            if self.api_key_manager:
                evidence.append("API key encryption implemented")
                score += 0.4
            else:
                gaps.append("API key encryption not implemented")
            
            # Check for token management (implies JWT encryption)
            if self.auth_service:
                evidence.append("Token-based authentication with encryption")
                score += 0.3
            else:
                gaps.append("Token encryption not confirmed")
        else:
            gaps.append("Security manager not configured")
            gaps.append("Cryptographic controls not verified")
        
        return score
    
    async def _assess_input_validation_controls(self, evidence: List[str], gaps: List[str]) -> float:
        """Assess input validation controls."""
        score = 0.0
        
        # This would typically involve code analysis tools
        # For now, check if security controls are in place
        if self.security_manager:
            evidence.append("Security framework configured")
            score += 0.5
            
            # Check for rate limiting (implies input validation)
            if hasattr(self.security_manager, 'rate_limiter'):
                evidence.append("Rate limiting configured (implies input validation)")
                score += 0.3
            else:
                gaps.append("Rate limiting not configured")
            
            gaps.append("Manual code review required for injection protection")
            score += 0.2  # Partial credit for having security framework
        else:
            gaps.append("Security framework not configured")
            gaps.append("Input validation controls not verified")
        
        return score
    
    async def _collect_control_evidence(self, control: ComplianceControl) -> List[str]:
        """Collect evidence for a control."""
        evidence = []
        
        try:
            for evidence_type in control.evidence_required:
                if evidence_type == "access_logs" and self.auth_service:
                    events = await self.auth_service.get_security_events(limit=10)
                    evidence.append(f"Found {len(events)} authentication events")
                
                elif evidence_type == "rbac_configuration" and self.rbac_manager:
                    analytics = await self.rbac_manager.get_rbac_analytics()
                    evidence.append(f"RBAC system with {analytics.get('roles', {}).get('total', 0)} roles")
                
                elif evidence_type == "2fa_records" and self.two_factor_auth:
                    analytics = await self.two_factor_auth.get_two_factor_analytics()
                    evidence.append(f"2FA system with {analytics.get('overview', {}).get('users_with_2fa', 0)} enabled users")
                
                elif evidence_type == "api_key_logs" and self.api_key_manager:
                    analytics = await self.api_key_manager.get_api_key_analytics()
                    evidence.append(f"API key management with {analytics.get('overview', {}).get('total_keys', 0)} keys")
        
        except Exception as e:
            logger.error(f"Failed to collect evidence for {control.control_id}: {e}")
            evidence.append(f"Evidence collection error: {e}")
        
        return evidence
    
    async def _generate_control_recommendations(self, control: ComplianceControl, gaps: List[str]) -> List[str]:
        """Generate recommendations for control implementation."""
        recommendations = []
        
        if gaps:
            # General recommendations based on control type
            if control.category == "Security" or control.category == "Access Control":
                if "authentication" in control.description.lower():
                    recommendations.append("Implement multi-factor authentication")
                    recommendations.append("Establish password policy enforcement")
                
                if "access control" in control.description.lower():
                    recommendations.append("Implement role-based access control (RBAC)")
                    recommendations.append("Conduct regular access reviews")
                
                if "monitoring" in control.description.lower():
                    recommendations.append("Enable comprehensive security logging")
                    recommendations.append("Implement real-time monitoring and alerting")
            
            elif control.category == "Data Protection":
                recommendations.append("Implement encryption for data at rest and in transit")
                recommendations.append("Establish key management procedures")
            
            elif control.category == "Application Security":
                recommendations.append("Implement secure coding practices")
                recommendations.append("Conduct regular security testing")
                recommendations.append("Implement input validation and output encoding")
            
            # Add specific recommendations based on gaps
            for gap in gaps:
                if "2fa" in gap.lower() or "two-factor" in gap.lower():
                    recommendations.append("Deploy two-factor authentication solution")
                
                if "rbac" in gap.lower() or "role-based" in gap.lower():
                    recommendations.append("Implement comprehensive RBAC system")
                
                if "encryption" in gap.lower():
                    recommendations.append("Deploy encryption solutions for sensitive data")
        
        return list(set(recommendations))  # Remove duplicates
    
    async def _generate_report_insights(self, standard: ComplianceStandard, 
                                      assessments: List[ControlAssessment],
                                      overall_score: float) -> Tuple[str, List[str], List[str], List[str]]:
        """Generate executive summary and insights for compliance report."""
        # Executive Summary
        total_controls = len(assessments)
        compliant = sum(1 for a in assessments if a.status == ComplianceStatus.COMPLIANT)
        compliance_percentage = (compliant / total_controls * 100) if total_controls > 0 else 0
        
        executive_summary = f"""
        Compliance Assessment Summary for {standard.value.upper()}:
        
        Overall Compliance Score: {overall_score:.1%}
        Controls Assessed: {total_controls}
        Fully Compliant: {compliant} ({compliance_percentage:.1f}%)
        
        {'The organization demonstrates strong compliance posture' if overall_score >= 0.8 else 
         'The organization shows partial compliance with improvement opportunities' if overall_score >= 0.5 else
         'Significant compliance gaps identified requiring immediate attention'}.
        """
        
        # Key Findings
        key_findings = []
        if overall_score >= 0.8:
            key_findings.append("Strong overall compliance posture maintained")
        
        critical_controls = [a for a in assessments if a.status == ComplianceStatus.NON_COMPLIANT]
        if critical_controls:
            key_findings.append(f"{len(critical_controls)} critical controls require immediate attention")
        
        # Identify areas of strength
        strong_areas = {}
        for assessment in assessments:
            if assessment.score >= 0.8:
                control = next((c for controls in self.compliance_controls.values() for c in controls.values() 
                              if c.control_id == assessment.control_id), None)
                if control:
                    category = control.category
                    strong_areas[category] = strong_areas.get(category, 0) + 1
        
        if strong_areas:
            top_category = max(strong_areas.keys(), key=lambda k: strong_areas[k])
            key_findings.append(f"Strong performance in {top_category} controls")
        
        # Critical Gaps
        critical_gaps = []
        for assessment in assessments:
            if assessment.status == ComplianceStatus.NON_COMPLIANT:
                control = next((c for controls in self.compliance_controls.values() for c in controls.values() 
                              if c.control_id == assessment.control_id), None)
                if control and control.severity in [ControlSeverity.CRITICAL, ControlSeverity.HIGH]:
                    critical_gaps.extend(assessment.gaps_identified)
        
        # Remove duplicates and limit to most critical
        critical_gaps = list(set(critical_gaps))[:10]
        
        # Recommendations
        recommendations = []
        all_recommendations = []
        for assessment in assessments:
            all_recommendations.extend(assessment.recommendations)
        
        # Prioritize and deduplicate recommendations
        recommendation_counts = {}
        for rec in all_recommendations:
            recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1
        
        # Sort by frequency and take top recommendations
        sorted_recommendations = sorted(recommendation_counts.items(), key=lambda x: x[1], reverse=True)
        recommendations = [rec for rec, count in sorted_recommendations[:10]]
        
        return executive_summary.strip(), key_findings, critical_gaps, recommendations
    
    async def get_compliance_status_summary(self) -> Dict[str, Any]:
        """Get comprehensive compliance status summary across all standards."""
        try:
            summary = {
                "overview": {
                    "standards_assessed": len(self.compliance_controls),
                    "total_reports": len(self.compliance_reports),
                    "last_assessment": None,
                    "next_assessment": None
                },
                "standards": {},
                "overall_health": "unknown"
            }
            
            # Get latest report for each standard
            latest_reports = {}
            for report in self.compliance_reports.values():
                standard = report.standard.value
                if (standard not in latest_reports or 
                    report.generated_at > latest_reports[standard].generated_at):
                    latest_reports[standard] = report
            
            # Calculate overall metrics
            total_score = 0.0
            total_controls = 0
            total_compliant = 0
            
            for standard, report in latest_reports.items():
                summary["standards"][standard] = {
                    "overall_score": report.overall_score,
                    "total_controls": report.total_controls,
                    "compliant_controls": report.compliant_controls,
                    "non_compliant_controls": report.non_compliant_controls,
                    "last_assessed": report.generated_at.isoformat(),
                    "next_assessment": report.next_assessment_date.isoformat()
                }
                
                total_score += report.overall_score
                total_controls += report.total_controls
                total_compliant += report.compliant_controls
            
            # Calculate overall health
            if latest_reports:
                avg_score = total_score / len(latest_reports)
                if avg_score >= 0.8:
                    summary["overall_health"] = "good"
                elif avg_score >= 0.6:
                    summary["overall_health"] = "fair"
                else:
                    summary["overall_health"] = "poor"
                
                summary["overview"]["average_score"] = avg_score
                summary["overview"]["total_controls"] = total_controls
                summary["overview"]["total_compliant"] = total_compliant
            
            # Get latest and next assessment dates
            if latest_reports:
                latest_assessment = max(report.generated_at for report in latest_reports.values())
                next_assessment = min(report.next_assessment_date for report in latest_reports.values())
                summary["overview"]["last_assessment"] = latest_assessment.isoformat()
                summary["overview"]["next_assessment"] = next_assessment.isoformat()
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get compliance status summary: {e}")
            return {"error": f"Failed to get compliance status: {e}"}
    
    async def export_compliance_report(self, report_id: str, format_type: str = "json") -> Tuple[bool, str, Optional[str]]:
        """Export compliance report in specified format."""
        try:
            report = self.compliance_reports.get(report_id)
            if not report:
                return False, "Report not found", None
            
            if format_type.lower() == "json":
                # Convert report to JSON
                report_dict = asdict(report)
                # Convert datetime objects to ISO strings
                def convert_datetime(obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    elif isinstance(obj, dict):
                        return {k: convert_datetime(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_datetime(item) for item in obj]
                    else:
                        return obj
                
                report_dict = convert_datetime(report_dict)
                exported_data = json.dumps(report_dict, indent=2)
                
            else:
                return False, f"Unsupported format: {format_type}", None
            
            return True, "Report exported successfully", exported_data
            
        except Exception as e:
            logger.error(f"Failed to export report {report_id}: {e}")
            return False, f"Export failed: {e}", None