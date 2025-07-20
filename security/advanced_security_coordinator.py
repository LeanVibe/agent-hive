#!/usr/bin/env python3
"""
Advanced Security Coordinator

Unified coordinator for all advanced security features including 2FA, API key management,
compliance reporting, and threat detection. Provides integrated security operations
and centralized management for LeanVibe Agent Hive.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from security.auth_service import AuthenticationService, UserRole
from security.rbac_manager import RBACManager
from security.two_factor_auth import TwoFactorAuthManager, TwoFactorMethod
from security.api_key_manager import ApiKeyManager, ApiKeyType, ApiKeyScope
from security.compliance_reporter import ComplianceReporter, ComplianceStandard
from security.threat_detector import MLThreatDetector, ThreatCategory
from security.rate_limiter import RateLimiter
from security.security_manager import SecurityManager


logger = logging.getLogger(__name__)


@dataclass
class SecurityMetrics:
    """Comprehensive security metrics."""
    timestamp: datetime
    authentication_stats: Dict[str, Any]
    rbac_stats: Dict[str, Any]
    two_factor_stats: Dict[str, Any]
    api_key_stats: Dict[str, Any]
    compliance_status: Dict[str, Any]
    threat_stats: Dict[str, Any]
    overall_security_score: float


class AdvancedSecurityCoordinator:
    """
    Unified coordinator for all advanced security features.
    
    Features:
    - Centralized security management
    - Cross-component integration
    - Comprehensive security monitoring
    - Automated threat response
    - Compliance automation
    - Security metrics aggregation
    - Event correlation across systems
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize advanced security coordinator."""
        self.config = config or self._get_default_config()
        
        # Initialize core security components
        self.security_manager = SecurityManager()
        self.auth_service = AuthenticationService(self.config.get("auth", {}))
        self.rbac_manager = RBACManager(self.config.get("rbac", {}))
        self.rate_limiter = RateLimiter(self.config.get("rate_limiting", {}))
        
        # Initialize advanced security features
        self.two_factor_auth = TwoFactorAuthManager(
            config=self.config.get("two_factor", {}),
            security_manager=self.security_manager
        )
        
        self.api_key_manager = ApiKeyManager(
            config=self.config.get("api_keys", {}),
            security_manager=self.security_manager,
            rate_limiter=self.rate_limiter
        )
        
        self.compliance_reporter = ComplianceReporter(
            config=self.config.get("compliance", {}),
            security_manager=self.security_manager,
            auth_service=self.auth_service,
            rbac_manager=self.rbac_manager,
            two_factor_auth=self.two_factor_auth,
            api_key_manager=self.api_key_manager
        )
        
        self.threat_detector = MLThreatDetector(
            config=self.config.get("threat_detection", {}),
            security_manager=self.security_manager
        )
        
        # Security event tracking
        self.security_events: List[Dict[str, Any]] = []
        self.security_metrics_history: List[SecurityMetrics] = []
        
        # Start integrated monitoring
        self._start_integrated_monitoring()
        
        logger.info("AdvancedSecurityCoordinator initialized with all components")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default security coordinator configuration."""
        return {
            "monitoring_interval_seconds": 300,
            "metrics_retention_days": 30,
            "auto_threat_response": True,
            "compliance_check_interval_hours": 24,
            "security_score_threshold": 0.8,
            "event_correlation_enabled": True,
            "real_time_monitoring": True
        }
    
    async def authenticate_user_comprehensive(self, username: str, password: str,
                                            client_ip: str, user_agent: str,
                                            two_factor_code: Optional[str] = None,
                                            device_fingerprint: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Comprehensive user authentication with all security features integrated.
        
        Returns:
            Tuple of (success, message, session_data)
        """
        try:
            # Log authentication attempt for threat detection
            auth_event = {
                "event_type": "authentication_attempt",
                "username": username,
                "ip_address": client_ip,
                "user_agent": user_agent,
                "timestamp": datetime.utcnow().isoformat(),
                "success": False  # Will be updated later
            }
            
            # Analyze for threats before proceeding
            threats = await self.threat_detector.analyze_authentication_event(auth_event)
            
            # Check for active threats that should block authentication
            for threat in threats:
                if threat.category in [ThreatCategory.BRUTE_FORCE, ThreatCategory.CREDENTIAL_STUFFING] and threat.score > 0.8:
                    await self._log_security_event({
                        "event_type": "authentication_blocked",
                        "reason": "active_threat_detected",
                        "threat_category": threat.category.value,
                        "threat_score": threat.score,
                        "username": username,
                        "ip_address": client_ip,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    return False, "Authentication blocked due to security threat", None
            
            # Proceed with standard authentication
            success, message, session = await self.auth_service.authenticate_with_rbac(
                username=username,
                password=password,
                client_ip=client_ip,
                user_agent=user_agent,
                rbac_manager=self.rbac_manager,
                two_factor_code=two_factor_code
            )
            
            # Update authentication event
            auth_event["success"] = success
            auth_event["user_id"] = session.user_id if session else None
            
            if success and session:
                # Check if 2FA challenge is needed
                if not two_factor_code:
                    # Check if user should be challenged for 2FA
                    challenge_success, challenge_message, challenge_session_id = await self.two_factor_auth.create_two_factor_challenge(
                        user_id=session.user_id,
                        challenge_type=TwoFactorMethod.TOTP,
                        device_id=device_fingerprint,
                        ip_address=client_ip
                    )
                    
                    if challenge_success and challenge_session_id:
                        return False, "2FA challenge required", {
                            "requires_2fa": True,
                            "challenge_session_id": challenge_session_id,
                            "challenge_methods": ["totp", "backup_codes"]
                        }
                
                # Authentication successful - prepare comprehensive session data
                session_data = {
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "access_token": session.access_token,
                    "refresh_token": session.refresh_token,
                    "expires_at": session.expires_at.isoformat(),
                    "user_roles": session.metadata.get("rbac_roles", []) if hasattr(session, 'metadata') and session.metadata else [],
                    "permissions": [perm.value for perm in session.permissions] if hasattr(session, 'permissions') else [],
                    "security_level": await self._calculate_user_security_level(session.user_id),
                    "device_trusted": device_fingerprint is not None
                }
                
                # Log successful authentication
                await self._log_security_event({
                    "event_type": "authentication_successful",
                    "user_id": session.user_id,
                    "username": username,
                    "ip_address": client_ip,
                    "security_level": session_data["security_level"],
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                return True, "Authentication successful", session_data
            else:
                # Log failed authentication
                await self._log_security_event({
                    "event_type": "authentication_failed",
                    "username": username,
                    "ip_address": client_ip,
                    "reason": message,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                return False, message, None
            
        except Exception as e:
            logger.error(f"Comprehensive authentication failed for {username}: {e}")
            return False, f"Authentication failed: {e}", None
    
    async def verify_two_factor_comprehensive(self, challenge_session_id: str, 
                                            verification_code: str,
                                            device_fingerprint: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Complete 2FA verification with session creation."""
        try:
            # Verify 2FA challenge
            success, message, trusted_device_id = await self.two_factor_auth.verify_two_factor_challenge(
                session_id=challenge_session_id,
                verification_code=verification_code,
                device_fingerprint=device_fingerprint
            )
            
            if success:
                # Create final authentication session
                # Note: In a real implementation, you'd need to store the pending authentication
                # state from the initial authentication attempt
                return True, "2FA verification successful", {
                    "2fa_verified": True,
                    "trusted_device_id": trusted_device_id,
                    "device_trust_enabled": trusted_device_id is not None
                }
            else:
                return False, message, None
            
        except Exception as e:
            logger.error(f"2FA verification failed for session {challenge_session_id}: {e}")
            return False, f"2FA verification failed: {e}", None
    
    async def create_api_key_comprehensive(self, user_id: str, name: str, description: str,
                                         scope: ApiKeyScope, permissions: List[str],
                                         expires_in_days: Optional[int] = None,
                                         allowed_ips: Optional[List[str]] = None,
                                         created_by: str = "system") -> Tuple[bool, str, Optional[str]]:
        """Create API key with comprehensive security validation."""
        try:
            # Convert permission strings to Permission objects
            from config.auth_models import Permission
            permission_objects = []
            for perm_str in permissions:
                try:
                    permission_objects.append(Permission(perm_str))
                except ValueError:
                    logger.warning(f"Invalid permission: {perm_str}")
            
            # Check user's authorization to create API keys
            user_perms = await self.rbac_manager.get_user_permissions(user_id)
            if Permission.ADMIN not in user_perms and Permission.WRITE not in user_perms:
                return False, "Insufficient permissions to create API keys", None
            
            # Create API key
            success, message, api_key = await self.api_key_manager.create_api_key(
                user_id=user_id,
                name=name,
                description=description,
                key_type=ApiKeyType.PERSONAL,
                scope=scope,
                permissions=permission_objects,
                expires_in_days=expires_in_days,
                allowed_ips=allowed_ips,
                created_by=created_by
            )
            
            if success:
                # Log API key creation
                await self._log_security_event({
                    "event_type": "api_key_created",
                    "user_id": user_id,
                    "key_name": name,
                    "scope": scope.value,
                    "permissions": permissions,
                    "created_by": created_by,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            return success, message, api_key
            
        except Exception as e:
            logger.error(f"Failed to create API key for user {user_id}: {e}")
            return False, f"API key creation failed: {e}", None
    
    async def generate_compliance_report_comprehensive(self, standard: ComplianceStandard,
                                                     generated_by: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Generate comprehensive compliance report with all security data."""
        try:
            # Generate the compliance report
            success, message, report = await self.compliance_reporter.generate_compliance_report(
                standard=standard,
                generated_by=generated_by,
                include_evidence=True
            )
            
            if success and report:
                # Enhance report with additional security metrics
                enhanced_report = {
                    "report_id": report.report_id,
                    "standard": report.standard.value,
                    "generated_at": report.generated_at.isoformat(),
                    "generated_by": report.generated_by,
                    "overall_score": report.overall_score,
                    "compliance_summary": {
                        "total_controls": report.total_controls,
                        "compliant": report.compliant_controls,
                        "non_compliant": report.non_compliant_controls,
                        "partially_compliant": report.partially_compliant_controls
                    },
                    "executive_summary": report.executive_summary,
                    "key_findings": report.key_findings,
                    "critical_gaps": report.critical_gaps,
                    "recommendations": report.recommendations,
                    "next_assessment_date": report.next_assessment_date.isoformat(),
                    "security_metrics": await self._get_current_security_metrics(),
                    "control_assessments": [
                        {
                            "control_id": assessment.control_id,
                            "status": assessment.status.value,
                            "score": assessment.score,
                            "gaps": assessment.gaps_identified,
                            "recommendations": assessment.recommendations
                        }
                        for assessment in report.control_assessments
                    ]
                }
                
                # Log report generation
                await self._log_security_event({
                    "event_type": "compliance_report_generated",
                    "standard": standard.value,
                    "report_id": report.report_id,
                    "overall_score": report.overall_score,
                    "generated_by": generated_by,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                return True, "Compliance report generated successfully", enhanced_report
            else:
                return False, message, None
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report for {standard.value}: {e}")
            return False, f"Compliance report generation failed: {e}", None
    
    async def get_security_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive security dashboard with all metrics."""
        try:
            current_metrics = await self._get_current_security_metrics()
            
            # Get recent security events
            recent_events = self.security_events[-50:] if self.security_events else []
            
            # Get active threats
            threat_analytics = await self.threat_detector.get_threat_analytics()
            
            # Calculate security trends
            trends = await self._calculate_security_trends()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_security_score": current_metrics.overall_security_score,
                "security_level": self._get_security_level_description(current_metrics.overall_security_score),
                "metrics": {
                    "authentication": current_metrics.authentication_stats,
                    "rbac": current_metrics.rbac_stats,
                    "two_factor": current_metrics.two_factor_stats,
                    "api_keys": current_metrics.api_key_stats,
                    "compliance": current_metrics.compliance_status,
                    "threats": current_metrics.threat_stats
                },
                "recent_events": recent_events,
                "active_threats": threat_analytics.get("overview", {}).get("active_alerts", 0),
                "trends": trends,
                "recommendations": await self._generate_security_recommendations(current_metrics)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate security dashboard: {e}")
            return {"error": f"Failed to generate security dashboard: {e}"}
    
    async def _calculate_user_security_level(self, user_id: str) -> str:
        """Calculate security level for a user."""
        try:
            score = 0.0
            max_score = 5.0
            
            # Check 2FA status
            two_factor_status = await self.two_factor_auth.get_two_factor_status(user_id)
            if two_factor_status.get("2fa_enabled", False):
                score += 2.0
            
            # Check RBAC configuration
            user_roles = await self.rbac_manager.get_user_roles(user_id)
            if user_roles:
                score += 1.0
            
            # Check API key security
            api_keys = await self.api_key_manager.get_user_api_keys(user_id)
            active_keys = [key for key in api_keys if key["status"] == "active"]
            if len(active_keys) <= 5:  # Reasonable number of keys
                score += 1.0
            
            # Check recent security events
            recent_threats = [
                event for event in self.security_events[-100:]
                if event.get("user_id") == user_id and event.get("event_type", "").startswith("threat_")
            ]
            if len(recent_threats) == 0:
                score += 1.0
            
            security_ratio = score / max_score
            
            if security_ratio >= 0.8:
                return "high"
            elif security_ratio >= 0.6:
                return "medium"
            else:
                return "low"
                
        except Exception as e:
            logger.error(f"Failed to calculate security level for user {user_id}: {e}")
            return "unknown"
    
    async def _get_current_security_metrics(self) -> SecurityMetrics:
        """Get current security metrics from all components."""
        try:
            current_time = datetime.utcnow()
            
            # Get metrics from each component
            auth_stats = await self.auth_service.get_authentication_stats()
            rbac_stats = await self.rbac_manager.get_rbac_analytics()
            two_factor_stats = await self.two_factor_auth.get_two_factor_analytics()
            api_key_stats = await self.api_key_manager.get_api_key_analytics()
            compliance_status = await self.compliance_reporter.get_compliance_status_summary()
            threat_stats = await self.threat_detector.get_threat_analytics()
            
            # Calculate overall security score
            overall_score = await self._calculate_overall_security_score(
                auth_stats, rbac_stats, two_factor_stats, api_key_stats, 
                compliance_status, threat_stats
            )
            
            return SecurityMetrics(
                timestamp=current_time,
                authentication_stats=auth_stats,
                rbac_stats=rbac_stats,
                two_factor_stats=two_factor_stats,
                api_key_stats=api_key_stats,
                compliance_status=compliance_status,
                threat_stats=threat_stats,
                overall_security_score=overall_score
            )
            
        except Exception as e:
            logger.error(f"Failed to get current security metrics: {e}")
            return SecurityMetrics(
                timestamp=datetime.utcnow(),
                authentication_stats={},
                rbac_stats={},
                two_factor_stats={},
                api_key_stats={},
                compliance_status={},
                threat_stats={},
                overall_security_score=0.0
            )
    
    async def _calculate_overall_security_score(self, auth_stats: Dict, rbac_stats: Dict,
                                              two_factor_stats: Dict, api_key_stats: Dict,
                                              compliance_status: Dict, threat_stats: Dict) -> float:
        """Calculate overall security score based on all metrics."""
        try:
            scores = []
            
            # Authentication score
            total_users = auth_stats.get("users", {}).get("total", 1)
            active_users = auth_stats.get("users", {}).get("active", 0)
            if total_users > 0:
                auth_score = active_users / total_users
                scores.append(auth_score)
            
            # 2FA adoption score
            users_with_2fa = two_factor_stats.get("overview", {}).get("users_with_2fa", 0)
            if total_users > 0:
                two_factor_score = min(1.0, users_with_2fa / total_users * 2)  # Boost 2FA importance
                scores.append(two_factor_score)
            
            # RBAC configuration score
            total_roles = rbac_stats.get("roles", {}).get("total", 0)
            rbac_score = min(1.0, total_roles / 5)  # Expect at least 5 roles
            scores.append(rbac_score)
            
            # API key security score
            total_keys = api_key_stats.get("overview", {}).get("total_keys", 0)
            active_keys = api_key_stats.get("overview", {}).get("active_keys", 0)
            if total_keys > 0:
                api_score = active_keys / total_keys
                scores.append(api_score)
            
            # Compliance score
            overall_health = compliance_status.get("overall_health", "unknown")
            if overall_health == "good":
                compliance_score = 1.0
            elif overall_health == "fair":
                compliance_score = 0.7
            elif overall_health == "poor":
                compliance_score = 0.3
            else:
                compliance_score = 0.5
            scores.append(compliance_score)
            
            # Threat detection score (inverse of active threats)
            active_alerts = threat_stats.get("overview", {}).get("active_alerts", 0)
            threat_score = max(0.0, 1.0 - (active_alerts * 0.1))  # Reduce score for each active threat
            scores.append(threat_score)
            
            # Calculate weighted average
            if scores:
                return sum(scores) / len(scores)
            else:
                return 0.5  # Default neutral score
            
        except Exception as e:
            logger.error(f"Failed to calculate overall security score: {e}")
            return 0.0
    
    def _get_security_level_description(self, score: float) -> str:
        """Get security level description based on score."""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.8:
            return "good"
        elif score >= 0.6:
            return "fair"
        elif score >= 0.4:
            return "poor"
        else:
            return "critical"
    
    async def _calculate_security_trends(self) -> Dict[str, Any]:
        """Calculate security trends from historical metrics."""
        try:
            if len(self.security_metrics_history) < 2:
                return {"trend": "insufficient_data"}
            
            recent_scores = [m.overall_security_score for m in self.security_metrics_history[-10:]]
            
            if len(recent_scores) >= 2:
                trend = recent_scores[-1] - recent_scores[-2]
                
                return {
                    "trend": "improving" if trend > 0.05 else "declining" if trend < -0.05 else "stable",
                    "trend_value": trend,
                    "recent_scores": recent_scores,
                    "score_change_30d": recent_scores[-1] - recent_scores[0] if len(recent_scores) >= 30 else None
                }
            
            return {"trend": "stable"}
            
        except Exception as e:
            logger.error(f"Failed to calculate security trends: {e}")
            return {"trend": "unknown"}
    
    async def _generate_security_recommendations(self, metrics: SecurityMetrics) -> List[str]:
        """Generate security recommendations based on current metrics."""
        recommendations = []
        
        try:
            # 2FA recommendations
            total_users = metrics.authentication_stats.get("users", {}).get("total", 0)
            users_with_2fa = metrics.two_factor_stats.get("overview", {}).get("users_with_2fa", 0)
            
            if total_users > 0 and users_with_2fa / total_users < 0.5:
                recommendations.append("Increase two-factor authentication adoption across user base")
            
            # API key recommendations
            total_keys = metrics.api_key_stats.get("overview", {}).get("total_keys", 0)
            expired_keys = metrics.api_key_stats.get("overview", {}).get("expired_keys", 0)
            
            if total_keys > 0 and expired_keys / total_keys > 0.1:
                recommendations.append("Review and rotate expired API keys")
            
            # Compliance recommendations
            if metrics.compliance_status.get("overall_health") in ["poor", "fair"]:
                recommendations.append("Address compliance gaps identified in latest assessment")
            
            # Threat recommendations
            active_alerts = metrics.threat_stats.get("overview", {}).get("active_alerts", 0)
            if active_alerts > 0:
                recommendations.append(f"Investigate and resolve {active_alerts} active security alerts")
            
            # Overall score recommendations
            if metrics.overall_security_score < 0.6:
                recommendations.append("Implement comprehensive security improvements across all areas")
            
        except Exception as e:
            logger.error(f"Failed to generate security recommendations: {e}")
            recommendations.append("Review security configuration - analysis incomplete")
        
        return recommendations
    
    async def _log_security_event(self, event: Dict[str, Any]) -> None:
        """Log security event to centralized tracking."""
        event["event_id"] = str(uuid.uuid4())
        self.security_events.append(event)
        
        # Keep only last 10000 events
        if len(self.security_events) > 10000:
            self.security_events = self.security_events[-5000:]
        
        # Forward to security manager if available
        if self.security_manager:
            await self.security_manager.log_security_event(event)
    
    def _start_integrated_monitoring(self) -> None:
        """Start integrated security monitoring tasks."""
        async def collect_security_metrics():
            """Collect security metrics periodically."""
            while True:
                try:
                    metrics = await self._get_current_security_metrics()
                    self.security_metrics_history.append(metrics)
                    
                    # Keep only recent metrics
                    retention_days = self.config.get("metrics_retention_days", 30)
                    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
                    
                    self.security_metrics_history = [
                        m for m in self.security_metrics_history
                        if m.timestamp > cutoff_date
                    ]
                    
                    # Log if security score is below threshold
                    threshold = self.config.get("security_score_threshold", 0.8)
                    if metrics.overall_security_score < threshold:
                        await self._log_security_event({
                            "event_type": "security_score_low",
                            "score": metrics.overall_security_score,
                            "threshold": threshold,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    
                    interval = self.config.get("monitoring_interval_seconds", 300)
                    await asyncio.sleep(interval)
                    
                except Exception as e:
                    logger.error(f"Security metrics collection error: {e}")
                    await asyncio.sleep(60)
        
        # Start monitoring if event loop is available
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(collect_security_metrics())
        except RuntimeError:
            logger.info("No event loop running, integrated monitoring will be handled manually")
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive security system health check."""
        try:
            current_time = datetime.utcnow()
            health_status = {
                "timestamp": current_time.isoformat(),
                "overall_status": "healthy",
                "components": {}
            }
            
            # Check each component
            components = {
                "auth_service": self.auth_service,
                "rbac_manager": self.rbac_manager,
                "two_factor_auth": self.two_factor_auth,
                "api_key_manager": self.api_key_manager,
                "compliance_reporter": self.compliance_reporter,
                "threat_detector": self.threat_detector
            }
            
            for name, component in components.items():
                try:
                    # Basic component check
                    health_status["components"][name] = {
                        "status": "healthy",
                        "initialized": component is not None,
                        "last_check": current_time.isoformat()
                    }
                except Exception as e:
                    health_status["components"][name] = {
                        "status": "unhealthy",
                        "error": str(e),
                        "last_check": current_time.isoformat()
                    }
                    health_status["overall_status"] = "degraded"
            
            # Get current metrics
            try:
                metrics = await self._get_current_security_metrics()
                health_status["security_score"] = metrics.overall_security_score
                
                if metrics.overall_security_score < 0.5:
                    health_status["overall_status"] = "critical"
                elif metrics.overall_security_score < 0.7:
                    health_status["overall_status"] = "warning"
            except Exception as e:
                health_status["metrics_error"] = str(e)
                health_status["overall_status"] = "degraded"
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": "critical",
                "error": str(e)
            }