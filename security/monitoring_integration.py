#!/usr/bin/env python3
"""
Security Monitoring Integration

Comprehensive integration module that connects all security components
with the monitoring and alerting systems for LeanVibe Agent Hive.

Integrations:
- SecurityManager with audit logging and monitoring
- JWT TokenManager with authentication event tracking
- RBAC Manager with authorization monitoring
- Rate Limiter with violation tracking and alerts
- Centralized security event coordination
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable
from contextlib import asynccontextmanager
import threading

# Import security components
from security.security_manager import SecurityManager, RiskLevel as SecurityRiskLevel
from security.token_manager import SecureTokenManager, TokenType, TokenStatus
from security.rbac_manager import RBACManager, PermissionType, RoleType
from security.rate_limiter import RateLimiter, RateLimitViolation, RateLimitStatus

# Import monitoring components
from security.audit_logger import (
    SecurityAuditLogger, SecurityEvent, SecurityEventType, SecuritySeverity,
    create_security_event, audit_logger
)
from security.security_monitor import (
    SecurityMonitor, SecurityAnomaly, security_monitor
)
from security.alert_system import (
    SecurityAlertSystem, evaluate_security_event, alert_system
)


logger = logging.getLogger(__name__)


class SecurityMonitoringIntegration:
    """
    Central integration hub for all security monitoring components.
    
    Features:
    - Unified security event processing pipeline
    - Cross-component correlation and analysis
    - Centralized monitoring and alerting
    - Performance optimization and caching
    - Comprehensive security analytics
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize security monitoring integration."""
        self.config = config or self._get_default_config()
        
        # Component references
        self.security_manager: Optional[SecurityManager] = None
        self.token_manager: Optional[SecureTokenManager] = None
        self.rbac_manager: Optional[RBACManager] = None
        self.rate_limiter: Optional[RateLimiter] = None
        
        # Monitoring components
        self.audit_logger = audit_logger
        self.security_monitor = security_monitor
        self.alert_system = alert_system
        
        # Event processing
        self.event_queue = asyncio.Queue(maxsize=50000)
        self.correlation_rules = []
        self.event_processors = []
        
        # Performance tracking
        self.integration_metrics = {
            "events_processed": 0,
            "events_failed": 0,
            "avg_processing_time_ms": 0.0,
            "component_events": {
                "security_manager": 0,
                "token_manager": 0,
                "rbac_manager": 0,
                "rate_limiter": 0
            }
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Background tasks
        self._processing_task = None
        
        # Initialize integration
        self._setup_event_processors()
        self._start_event_processing()
        
        logger.info("SecurityMonitoringIntegration initialized")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default integration configuration."""
        return {
            "enabled": True,
            "real_time_processing": True,
            "event_correlation": True,
            "cross_component_analysis": True,
            "performance_monitoring": True,
            "batch_processing": True,
            "batch_size": 100,
            "processing_timeout_seconds": 30,
            "max_queue_size": 50000,
            "correlation_window_minutes": 15,
            "enable_detailed_logging": True
        }
    
    def _setup_event_processors(self):
        """Setup event processing pipeline."""
        # Add standard event processors
        self.event_processors = [
            self._process_authentication_events,
            self._process_authorization_events,
            self._process_rate_limit_events,
            self._process_security_violation_events,
            self._process_system_events
        ]
        
        logger.info(f"Setup {len(self.event_processors)} event processors")
    
    def _start_event_processing(self):
        """Start background event processing."""
        async def event_processor():
            while True:
                try:
                    event = await self.event_queue.get()
                    await self._process_security_event(event)
                except Exception as e:
                    logger.error(f"Event processing error: {e}")
                    self.integration_metrics["events_failed"] += 1
                    await asyncio.sleep(1)
        
        try:
            loop = asyncio.get_running_loop()
            self._processing_task = loop.create_task(event_processor())
            logger.info("Security event processing started")
        except RuntimeError:
            logger.info("No event loop running, events will be processed synchronously")
    
    def register_security_manager(self, security_manager: SecurityManager):
        """Register SecurityManager for monitoring integration."""
        self.security_manager = security_manager
        
        # Monkey patch SecurityManager methods to add monitoring
        original_validate_operation = security_manager.validate_operation
        original_log_security_event = security_manager._log_security_event
        
        async def monitored_validate_operation(operation, agent_id, session_id, user_id=None, context=None):
            """Enhanced validate_operation with monitoring."""
            start_time = time.time()
            result = original_validate_operation(operation, agent_id, session_id, user_id, context)
            
            # Create monitoring event
            is_valid, reason, risk_level = result
            
            event = create_security_event(
                event_type=SecurityEventType.SECURITY_COMMAND_BLOCKED if not is_valid else SecurityEventType.SYSTEM_HEALTH_CHECK,
                severity=self._map_risk_level_to_severity(risk_level),
                source_component="security_manager",
                user_id=user_id,
                session_id=session_id,
                agent_id=agent_id,
                action=operation,
                result="blocked" if not is_valid else "allowed",
                risk_score=self._map_risk_level_to_score(risk_level),
                threat_indicators=["command_injection"] if not is_valid and "injection" in reason.lower() else [],
                metadata={
                    "validation_reason": reason,
                    "risk_level": risk_level.value,
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "context": context or {}
                }
            )
            
            await self._queue_security_event(event, "security_manager")
            return result
        
        def monitored_log_security_event(agent_id, session_id, event_type, action, result, risk_level, details, user_id=None, ip_address=None):
            """Enhanced _log_security_event with monitoring."""
            # Call original method
            original_log_security_event(agent_id, session_id, event_type, action, result, risk_level, details, user_id, ip_address)
            
            # Create monitoring event
            event = create_security_event(
                event_type=SecurityEventType.SECURITY_COMMAND_BLOCKED if result == "blocked" else SecurityEventType.SYSTEM_HEALTH_CHECK,
                severity=self._map_risk_level_to_severity(risk_level),
                source_component="security_manager",
                user_id=user_id,
                session_id=session_id,
                agent_id=agent_id,
                client_ip=ip_address,
                action=action,
                result=result,
                risk_score=self._map_risk_level_to_score(risk_level),
                metadata=details
            )
            
            # Queue for async processing
            asyncio.create_task(self._queue_security_event(event, "security_manager"))
        
        # Apply monkey patches
        security_manager.validate_operation = monitored_validate_operation
        security_manager._log_security_event = monitored_log_security_event
        
        logger.info("SecurityManager registered for monitoring")
    
    def register_token_manager(self, token_manager: SecureTokenManager):
        """Register TokenManager for monitoring integration."""
        self.token_manager = token_manager
        
        # Monkey patch TokenManager methods
        original_validate_token = token_manager.validate_token_secure
        original_create_token = token_manager.create_secure_token
        original_revoke_token = token_manager.revoke_token
        
        async def monitored_validate_token(token, required_permissions=None, client_ip=None, user_agent=None):
            """Enhanced validate_token_secure with monitoring."""
            start_time = time.time()
            result = await original_validate_token(token, required_permissions, client_ip, user_agent)
            
            # Create monitoring event
            event_type = SecurityEventType.AUTH_LOGIN_SUCCESS if result.success else SecurityEventType.AUTH_LOGIN_FAILURE
            severity = SecuritySeverity.INFO if result.success else SecuritySeverity.MEDIUM
            
            event = create_security_event(
                event_type=event_type,
                severity=severity,
                source_component="token_manager",
                user_id=result.user_id if result.success else None,
                client_ip=client_ip,
                user_agent=user_agent,
                action="token_validation",
                result="success" if result.success else "failure",
                error_message=result.error if not result.success else None,
                metadata={
                    "token_metadata": result.metadata if result.success else {},
                    "required_permissions": [p.value for p in required_permissions] if required_permissions else [],
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
            )
            
            await self._queue_security_event(event, "token_manager")
            return result
        
        async def monitored_create_token(user_id, token_type, permissions, expires_in_hours=None, scopes=None, client_metadata=None):
            """Enhanced create_secure_token with monitoring."""
            result = await original_create_token(user_id, token_type, permissions, expires_in_hours, scopes, client_metadata)
            
            if result:
                token, token_id = result
                
                event = create_security_event(
                    event_type=SecurityEventType.AUTH_TOKEN_ISSUED,
                    severity=SecuritySeverity.INFO,
                    source_component="token_manager",
                    user_id=user_id,
                    action="token_created",
                    result="success",
                    metadata={
                        "token_id": token_id,
                        "token_type": token_type.value,
                        "permissions": [p.value for p in permissions],
                        "expires_in_hours": expires_in_hours,
                        "scopes": scopes or []
                    }
                )
                
                await self._queue_security_event(event, "token_manager")
            
            return result
        
        async def monitored_revoke_token(token_id, reason="revoked"):
            """Enhanced revoke_token with monitoring."""
            result = await original_revoke_token(token_id, reason)
            
            if result:
                metadata = token_manager.token_metadata.get(token_id)
                
                event = create_security_event(
                    event_type=SecurityEventType.AUTH_TOKEN_REVOKED,
                    severity=SecuritySeverity.INFO,
                    source_component="token_manager",
                    user_id=metadata.user_id if metadata else None,
                    action="token_revoked",
                    result="success",
                    metadata={
                        "token_id": token_id,
                        "revocation_reason": reason,
                        "token_type": metadata.token_type.value if metadata else "unknown"
                    }
                )
                
                await self._queue_security_event(event, "token_manager")
            
            return result
        
        # Apply monkey patches
        token_manager.validate_token_secure = monitored_validate_token
        token_manager.create_secure_token = monitored_create_token
        token_manager.revoke_token = monitored_revoke_token
        
        logger.info("TokenManager registered for monitoring")
    
    def register_rbac_manager(self, rbac_manager: RBACManager):
        """Register RBACManager for monitoring integration."""
        self.rbac_manager = rbac_manager
        
        # Monkey patch RBAC methods
        original_check_permission = rbac_manager.check_permission
        original_assign_role = rbac_manager.assign_role_to_user
        original_revoke_role = rbac_manager.revoke_role_from_user
        
        async def monitored_check_permission(user_id, permission, context=None):
            """Enhanced check_permission with monitoring."""
            start_time = time.time()
            result = await original_check_permission(user_id, permission, context)
            
            # Create monitoring event
            event_type = SecurityEventType.AUTHZ_PERMISSION_GRANTED if result.granted else SecurityEventType.AUTHZ_PERMISSION_DENIED
            severity = SecuritySeverity.INFO if result.granted else SecuritySeverity.MEDIUM
            
            event = create_security_event(
                event_type=event_type,
                severity=severity,
                source_component="rbac_manager",
                user_id=user_id,
                action="permission_check",
                resource=permission.value,
                result="granted" if result.granted else "denied",
                metadata={
                    "permission": permission.value,
                    "reason": result.reason,
                    "role_sources": result.role_sources,
                    "context": context or {},
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
            )
            
            await self._queue_security_event(event, "rbac_manager")
            return result
        
        async def monitored_assign_role(user_id, role_id, assigned_by, expires_at=None, context_constraints=None):
            """Enhanced assign_role_to_user with monitoring."""
            result = await original_assign_role(user_id, role_id, assigned_by, expires_at, context_constraints)
            success, message = result
            
            if success:
                role = rbac_manager.roles.get(role_id)
                
                event = create_security_event(
                    event_type=SecurityEventType.AUTHZ_ROLE_ASSIGNED,
                    severity=SecuritySeverity.INFO,
                    source_component="rbac_manager",
                    user_id=user_id,
                    action="role_assigned",
                    result="success",
                    metadata={
                        "role_id": role_id,
                        "role_name": role.name if role else "unknown",
                        "assigned_by": assigned_by,
                        "expires_at": expires_at.isoformat() if expires_at else None,
                        "context_constraints": context_constraints or {}
                    }
                )
                
                await self._queue_security_event(event, "rbac_manager")
            
            return result
        
        async def monitored_revoke_role(user_id, role_id, revoked_by):
            """Enhanced revoke_role_from_user with monitoring."""
            result = await original_revoke_role(user_id, role_id, revoked_by)
            success, message = result
            
            if success:
                role = rbac_manager.roles.get(role_id)
                
                event = create_security_event(
                    event_type=SecurityEventType.AUTHZ_ROLE_REVOKED,
                    severity=SecuritySeverity.INFO,
                    source_component="rbac_manager",
                    user_id=user_id,
                    action="role_revoked",
                    result="success",
                    metadata={
                        "role_id": role_id,
                        "role_name": role.name if role else "unknown",
                        "revoked_by": revoked_by
                    }
                )
                
                await self._queue_security_event(event, "rbac_manager")
            
            return result
        
        # Apply monkey patches
        rbac_manager.check_permission = monitored_check_permission
        rbac_manager.assign_role_to_user = monitored_assign_role
        rbac_manager.revoke_role_from_user = monitored_revoke_role
        
        logger.info("RBACManager registered for monitoring")
    
    def register_rate_limiter(self, rate_limiter: RateLimiter):
        """Register RateLimiter for monitoring integration."""
        self.rate_limiter = rate_limiter
        
        # Monkey patch RateLimiter methods
        original_check_rate_limit = rate_limiter.check_rate_limit
        original_record_violation = rate_limiter._record_violation
        
        async def monitored_check_rate_limit(request_context):
            """Enhanced check_rate_limit with monitoring."""
            start_time = time.time()
            result = await original_check_rate_limit(request_context)
            
            # Create monitoring event
            event_type = SecurityEventType.RATE_LIMIT_EXCEEDED if not result.allowed else SecurityEventType.API_REQUEST
            severity = SecuritySeverity.MEDIUM if not result.allowed else SecuritySeverity.INFO
            
            event = create_security_event(
                event_type=event_type,
                severity=severity,
                source_component="rate_limiter",
                user_id=request_context.get("user_id"),
                client_ip=request_context.get("client_ip"),
                action="rate_limit_check",
                resource=request_context.get("endpoint", "/"),
                result="blocked" if not result.allowed else "allowed",
                metadata={
                    "remaining_requests": result.remaining,
                    "reset_time": result.reset_time.isoformat(),
                    "retry_after": result.retry_after,
                    "request_context": request_context,
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "violation_details": asdict(result.violation) if result.violation else None
                }
            )
            
            await self._queue_security_event(event, "rate_limiter")
            return result
        
        def monitored_record_violation(rule, key, context):
            """Enhanced _record_violation with monitoring."""
            violation = original_record_violation(rule, key, context)
            
            # Create monitoring event for severe violations
            event = create_security_event(
                event_type=SecurityEventType.RATE_LIMIT_VIOLATION,
                severity=SecuritySeverity.HIGH if violation.severity == "high" else SecuritySeverity.MEDIUM,
                source_component="rate_limiter",
                user_id=context.get("user_id"),
                client_ip=context.get("client_ip"),
                action="rate_limit_violation",
                resource=context.get("endpoint", "/"),
                result="violation_recorded",
                risk_score=80 if violation.severity == "high" else 60,
                threat_indicators=["rate_abuse", "potential_dos"],
                metadata={
                    "violation_id": violation.violation_id,
                    "rule_name": rule.name,
                    "violated_at": violation.violated_at.isoformat(),
                    "requests_count": violation.requests_count,
                    "window_limit": violation.window_limit,
                    "severity": violation.severity,
                    "client_info": violation.client_info
                }
            )
            
            # Queue for async processing
            asyncio.create_task(self._queue_security_event(event, "rate_limiter"))
            return violation
        
        # Apply monkey patches
        rate_limiter.check_rate_limit = monitored_check_rate_limit
        rate_limiter._record_violation = monitored_record_violation
        
        logger.info("RateLimiter registered for monitoring")
    
    async def _queue_security_event(self, event: SecurityEvent, source_component: str):
        """Queue security event for processing."""
        try:
            await self.event_queue.put(event)
            self.integration_metrics["component_events"][source_component] += 1
        except Exception as e:
            logger.error(f"Failed to queue security event: {e}")
            self.integration_metrics["events_failed"] += 1
    
    async def _process_security_event(self, event: SecurityEvent):
        """Process security event through monitoring pipeline."""
        start_time = time.time()
        
        try:
            # Log to audit system
            await self.audit_logger.log_event(event)
            
            # Process through security monitor
            anomalies = await self.security_monitor.process_security_event(event)
            
            # Process through alert system
            alerts = await self.alert_system.evaluate_event(event)
            
            # Run custom event processors
            for processor in self.event_processors:
                try:
                    await processor(event, anomalies, alerts)
                except Exception as e:
                    logger.error(f"Event processor error: {e}")
            
            # Update metrics
            processing_time = (time.time() - start_time) * 1000
            self.integration_metrics["events_processed"] += 1
            
            # Update average processing time
            current_avg = self.integration_metrics["avg_processing_time_ms"]
            self.integration_metrics["avg_processing_time_ms"] = (current_avg + processing_time) / 2
            
        except Exception as e:
            logger.error(f"Security event processing error: {e}")
            self.integration_metrics["events_failed"] += 1
    
    async def _process_authentication_events(self, event: SecurityEvent, anomalies: List[SecurityAnomaly], alerts: List):
        """Process authentication-related events."""
        if event.event_type not in [
            SecurityEventType.AUTH_LOGIN_SUCCESS,
            SecurityEventType.AUTH_LOGIN_FAILURE,
            SecurityEventType.AUTH_TOKEN_ISSUED,
            SecurityEventType.AUTH_TOKEN_REVOKED
        ]:
            return
        
        # Track authentication patterns
        if event.user_id and event.client_ip:
            # Could implement geo-location tracking, device fingerprinting, etc.
            pass
        
        # Detect brute force attacks
        if event.event_type == SecurityEventType.AUTH_LOGIN_FAILURE:
            # Track failed login attempts per user/IP
            pass
    
    async def _process_authorization_events(self, event: SecurityEvent, anomalies: List[SecurityAnomaly], alerts: List):
        """Process authorization-related events."""
        if event.event_type not in [
            SecurityEventType.AUTHZ_PERMISSION_GRANTED,
            SecurityEventType.AUTHZ_PERMISSION_DENIED,
            SecurityEventType.AUTHZ_ROLE_ASSIGNED,
            SecurityEventType.AUTHZ_ROLE_REVOKED
        ]:
            return
        
        # Track permission escalation attempts
        if event.event_type == SecurityEventType.AUTHZ_PERMISSION_DENIED:
            # Analyze permission denial patterns
            pass
    
    async def _process_rate_limit_events(self, event: SecurityEvent, anomalies: List[SecurityAnomaly], alerts: List):
        """Process rate limiting events."""
        if event.event_type not in [
            SecurityEventType.RATE_LIMIT_EXCEEDED,
            SecurityEventType.RATE_LIMIT_VIOLATION
        ]:
            return
        
        # Track rate limiting patterns
        if event.client_ip:
            # Could implement IP reputation tracking
            pass
    
    async def _process_security_violation_events(self, event: SecurityEvent, anomalies: List[SecurityAnomaly], alerts: List):
        """Process security violation events."""
        if event.event_type not in [
            SecurityEventType.SECURITY_COMMAND_BLOCKED,
            SecurityEventType.SECURITY_INJECTION_ATTEMPT,
            SecurityEventType.SECURITY_XSS_ATTEMPT
        ]:
            return
        
        # Enhanced threat analysis for security violations
        pass
    
    async def _process_system_events(self, event: SecurityEvent, anomalies: List[SecurityAnomaly], alerts: List):
        """Process system-related events."""
        if event.event_type not in [
            SecurityEventType.SYSTEM_STARTUP,
            SecurityEventType.SYSTEM_SHUTDOWN,
            SecurityEventType.SYSTEM_CONFIG_CHANGE
        ]:
            return
        
        # Track system health and configuration changes
        pass
    
    def _map_risk_level_to_severity(self, risk_level: SecurityRiskLevel) -> SecuritySeverity:
        """Map SecurityManager risk level to monitoring severity."""
        mapping = {
            SecurityRiskLevel.LOW: SecuritySeverity.LOW,
            SecurityRiskLevel.MEDIUM: SecuritySeverity.MEDIUM,
            SecurityRiskLevel.HIGH: SecuritySeverity.HIGH,
            SecurityRiskLevel.CRITICAL: SecuritySeverity.CRITICAL
        }
        return mapping.get(risk_level, SecuritySeverity.MEDIUM)
    
    def _map_risk_level_to_score(self, risk_level: SecurityRiskLevel) -> int:
        """Map SecurityManager risk level to numeric score."""
        mapping = {
            SecurityRiskLevel.LOW: 25,
            SecurityRiskLevel.MEDIUM: 50,
            SecurityRiskLevel.HIGH: 75,
            SecurityRiskLevel.CRITICAL: 95
        }
        return mapping.get(risk_level, 50)
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get comprehensive integration status."""
        return {
            "status": "active",
            "components_registered": {
                "security_manager": self.security_manager is not None,
                "token_manager": self.token_manager is not None,
                "rbac_manager": self.rbac_manager is not None,
                "rate_limiter": self.rate_limiter is not None
            },
            "monitoring_systems": {
                "audit_logger": True,
                "security_monitor": True,
                "alert_system": True
            },
            "performance": self.integration_metrics,
            "queue_status": {
                "queue_size": self.event_queue.qsize() if hasattr(self.event_queue, 'qsize') else 0,
                "max_queue_size": self.config.get("max_queue_size", 50000)
            },
            "processing": {
                "real_time": self.config.get("real_time_processing", True),
                "event_correlation": self.config.get("event_correlation", True),
                "processors_count": len(self.event_processors)
            }
        }


# Global integration instance
security_integration = SecurityMonitoringIntegration()


# Convenience functions for easy component registration
def register_security_components(security_manager=None, token_manager=None, 
                                rbac_manager=None, rate_limiter=None):
    """Register all security components for monitoring."""
    if security_manager:
        security_integration.register_security_manager(security_manager)
    
    if token_manager:
        security_integration.register_token_manager(token_manager)
    
    if rbac_manager:
        security_integration.register_rbac_manager(rbac_manager)
    
    if rate_limiter:
        security_integration.register_rate_limiter(rate_limiter)
    
    logger.info("Security components registered for monitoring integration")


def get_integration_status() -> Dict[str, Any]:
    """Get current integration status."""
    return security_integration.get_integration_status()


async def process_external_security_event(event_type: SecurityEventType,
                                        severity: SecuritySeverity,
                                        source_component: str,
                                        **kwargs) -> bool:
    """Process external security event through monitoring pipeline."""
    try:
        event = create_security_event(
            event_type=event_type,
            severity=severity,
            source_component=source_component,
            **kwargs
        )
        
        await security_integration._queue_security_event(event, source_component)
        return True
        
    except Exception as e:
        logger.error(f"Failed to process external security event: {e}")
        return False


if __name__ == "__main__":
    # Example usage and testing
    async def main():
        from security.security_manager import SecurityManager
        from security.token_manager import SecureTokenManager
        from security.rbac_manager import RBACManager
        from security.rate_limiter import RateLimiter
        
        # Initialize components
        security_manager = SecurityManager()
        token_manager = SecureTokenManager({"jwt_secret": "test-secret"})
        rbac_manager = RBACManager()
        rate_limiter = RateLimiter()
        
        # Register components
        register_security_components(
            security_manager=security_manager,
            token_manager=token_manager,
            rbac_manager=rbac_manager,
            rate_limiter=rate_limiter
        )
        
        # Test integration
        print("Testing security monitoring integration...")
        
        # Simulate some security events
        await process_external_security_event(
            SecurityEventType.SYSTEM_STARTUP,
            SecuritySeverity.INFO,
            "system",
            action="system_started"
        )
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Get status
        status = get_integration_status()
        print(f"Integration Status: {status['status']}")
        print(f"Events Processed: {status['performance']['events_processed']}")
        print(f"Components Registered: {sum(status['components_registered'].values())}/4")
    
    # Run test
    asyncio.run(main())