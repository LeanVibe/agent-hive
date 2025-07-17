"""
Security Integration Module for LeanVibe Agent Hive

Unifies all security components into a single cohesive system:
- Authentication (JWT, API Key, OAuth2)
- Authorization (RBAC)
- Command Validation
- Input Sanitization
- Audit Logging
- Security Monitoring
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict

from config.unified_security_config import get_security_config, UnifiedSecurityConfig
from security.security_manager import SecurityManager, SecurityEvent, RiskLevel
from external_api.auth_middleware import AuthenticationMiddleware, AuthResult, Permission
from external_api.models import ApiRequest, ApiResponse


logger = logging.getLogger(__name__)


@dataclass
class SecurityValidationRequest:
    """Request for security validation."""
    token: Optional[str] = None
    api_key: Optional[str] = None
    command: Optional[str] = None
    input_data: Optional[str] = None
    endpoint: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    permissions_required: Optional[List[str]] = None


@dataclass
class SecurityValidationResponse:
    """Response from security validation."""
    valid: bool
    user_id: Optional[str] = None
    permissions: Optional[List[str]] = None
    risk_level: Optional[str] = None
    error_message: Optional[str] = None
    audit_event_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class UnifiedSecurityEvent:
    """Unified security event for cross-component correlation."""
    event_id: str
    timestamp: datetime
    event_type: str
    component: str
    user_id: Optional[str]
    session_id: Optional[str]
    risk_level: str
    details: Dict[str, Any]
    correlated_events: List[str] = None


class SecurityIntegration:
    """
    Unified Security Integration System
    
    Coordinates all security components and provides unified API endpoints
    for authentication, authorization, validation, and monitoring.
    """
    
    def __init__(self, config: Optional[UnifiedSecurityConfig] = None):
        """
        Initialize security integration.
        
        Args:
            config: Unified security configuration
        """
        self.config = config or get_security_config()
        
        # Initialize security components
        self.security_manager = SecurityManager(self.config.get_security_manager_config())
        self.auth_middleware = AuthenticationMiddleware(self.config.get_auth_config())
        
        # Event correlation
        self.event_correlator = EventCorrelator()
        
        # Security metrics
        self.metrics = SecurityMetrics()
        
        logger.info("Security integration initialized successfully")
    
    async def validate_unified_security(self, request: SecurityValidationRequest) -> SecurityValidationResponse:
        """
        Unified security validation endpoint.
        
        Combines authentication, authorization, command validation, 
        and input sanitization into a single validation call.
        
        Args:
            request: Security validation request
            
        Returns:
            Unified security validation response
        """
        start_time = datetime.now()
        
        try:
            # 1. Authentication validation
            auth_result = None
            if request.token or request.api_key:
                auth_result = await self._validate_authentication(request)
                if not auth_result.valid:
                    return auth_result
            
            # 2. Authorization validation (RBAC)
            if request.permissions_required:
                rbac_result = await self._validate_authorization(
                    auth_result.user_id if auth_result else None,
                    request.permissions_required,
                    request.endpoint
                )
                if not rbac_result.valid:
                    return rbac_result
            
            # 3. Command validation
            if request.command:
                cmd_result = await self._validate_command(request.command, request.user_id)
                if not cmd_result.valid:
                    return cmd_result
            
            # 4. Input sanitization
            if request.input_data:
                input_result = await self._validate_input(request.input_data, request.user_id)
                if not input_result.valid:
                    return input_result
            
            # 5. Create unified security event
            audit_event_id = await self._create_unified_audit_event(
                request, auth_result, "validation_success"
            )
            
            # 6. Update metrics
            self.metrics.record_validation_success()
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"Unified security validation completed in {processing_time:.2f}ms")
            
            return SecurityValidationResponse(
                valid=True,
                user_id=auth_result.user_id if auth_result else None,
                permissions=auth_result.permissions if auth_result else None,
                risk_level=RiskLevel.LOW.value,
                audit_event_id=audit_event_id,
                metadata={
                    "processing_time_ms": processing_time,
                    "components_validated": self._get_validated_components(request)
                }
            )
            
        except Exception as e:
            logger.error(f"Unified security validation failed: {e}")
            
            # Create failure audit event
            audit_event_id = await self._create_unified_audit_event(
                request, None, "validation_error", str(e)
            )
            
            self.metrics.record_validation_failure()
            
            return SecurityValidationResponse(
                valid=False,
                error_message=f"Security validation failed: {str(e)}",
                risk_level=RiskLevel.HIGH.value,
                audit_event_id=audit_event_id
            )
    
    async def _validate_authentication(self, request: SecurityValidationRequest) -> SecurityValidationResponse:
        """Validate authentication using auth middleware."""
        try:
            # Create mock ApiRequest for auth middleware
            api_request = ApiRequest(
                method="POST",
                path="/api/security/validate",
                headers={
                    "Authorization": f"Bearer {request.token}" if request.token else "",
                    "X-API-Key": request.api_key or ""
                },
                query_params={},
                body=None,
                timestamp=datetime.now(),
                request_id=f"sec-{datetime.now().timestamp()}",
                client_ip="127.0.0.1"
            )
            
            auth_result = await self.auth_middleware.authenticate_request(api_request)
            
            if auth_result.success:
                return SecurityValidationResponse(
                    valid=True,
                    user_id=auth_result.user_id,
                    permissions=[perm.value for perm in auth_result.permissions],
                    risk_level=RiskLevel.LOW.value
                )
            else:
                return SecurityValidationResponse(
                    valid=False,
                    error_message=auth_result.error or "Authentication failed",
                    risk_level=RiskLevel.MEDIUM.value
                )
                
        except Exception as e:
            logger.error(f"Authentication validation failed: {e}")
            return SecurityValidationResponse(
                valid=False,
                error_message=f"Authentication validation error: {str(e)}",
                risk_level=RiskLevel.HIGH.value
            )
    
    async def _validate_authorization(self, user_id: Optional[str], 
                                   permissions_required: List[str], 
                                   endpoint: Optional[str]) -> SecurityValidationResponse:
        """Validate authorization using RBAC."""
        try:
            # Check if user has required permissions
            user_permissions = await self._get_user_permissions(user_id)
            
            for required_perm in permissions_required:
                if required_perm not in user_permissions:
                    return SecurityValidationResponse(
                        valid=False,
                        error_message=f"Missing required permission: {required_perm}",
                        risk_level=RiskLevel.MEDIUM.value
                    )
            
            # Check endpoint-specific permissions
            if endpoint:
                endpoint_perms = self.config.rbac.path_permissions.get(endpoint, [])
                for perm in endpoint_perms:
                    if perm.value not in user_permissions:
                        return SecurityValidationResponse(
                            valid=False,
                            error_message=f"Missing endpoint permission: {perm.value}",
                            risk_level=RiskLevel.MEDIUM.value
                        )
            
            return SecurityValidationResponse(
                valid=True,
                permissions=user_permissions,
                risk_level=RiskLevel.LOW.value
            )
            
        except Exception as e:
            logger.error(f"Authorization validation failed: {e}")
            return SecurityValidationResponse(
                valid=False,
                error_message=f"Authorization validation error: {str(e)}",
                risk_level=RiskLevel.HIGH.value
            )
    
    async def _validate_command(self, command: str, user_id: Optional[str]) -> SecurityValidationResponse:
        """Validate command using security manager."""
        try:
            validation_result = await self.security_manager.validate_command(
                command, user_id or "anonymous"
            )
            
            if validation_result["valid"]:
                return SecurityValidationResponse(
                    valid=True,
                    risk_level=validation_result["risk_level"],
                    metadata={"command_analysis": validation_result}
                )
            else:
                return SecurityValidationResponse(
                    valid=False,
                    error_message=validation_result["message"],
                    risk_level=validation_result["risk_level"]
                )
                
        except Exception as e:
            logger.error(f"Command validation failed: {e}")
            return SecurityValidationResponse(
                valid=False,
                error_message=f"Command validation error: {str(e)}",
                risk_level=RiskLevel.HIGH.value
            )
    
    async def _validate_input(self, input_data: str, user_id: Optional[str]) -> SecurityValidationResponse:
        """Validate input using security manager."""
        try:
            sanitized_input = self.security_manager.sanitize_input(input_data)
            
            # Check if input was modified (indicates potential security issue)
            if sanitized_input != input_data:
                return SecurityValidationResponse(
                    valid=False,
                    error_message="Input contains potentially dangerous content",
                    risk_level=RiskLevel.MEDIUM.value,
                    metadata={"sanitized_input": sanitized_input}
                )
            
            return SecurityValidationResponse(
                valid=True,
                risk_level=RiskLevel.LOW.value,
                metadata={"input_validation": "passed"}
            )
            
        except Exception as e:
            logger.error(f"Input validation failed: {e}")
            return SecurityValidationResponse(
                valid=False,
                error_message=f"Input validation error: {str(e)}",
                risk_level=RiskLevel.HIGH.value
            )
    
    async def _get_user_permissions(self, user_id: Optional[str]) -> List[str]:
        """Get user permissions from auth middleware."""
        if not user_id:
            return []
        
        # Get user role and permissions
        # In a real implementation, this would query a user database
        default_role = self.config.rbac.default_role
        user_permissions = self.config.rbac.roles.get(default_role, [])
        
        return [perm.value for perm in user_permissions]
    
    async def _create_unified_audit_event(self, request: SecurityValidationRequest, 
                                        auth_result: Optional[SecurityValidationResponse],
                                        event_type: str, error: Optional[str] = None) -> str:
        """Create unified audit event."""
        event_id = f"sec-{datetime.now().timestamp()}"
        
        security_event = SecurityEvent(
            event_id=event_id,
            timestamp=datetime.now(),
            agent_id="security-integration",
            session_id=request.session_id or "anonymous",
            event_type=event_type,
            action="unified_security_validation",
            result="success" if not error else "failure",
            risk_level=RiskLevel.MEDIUM if error else RiskLevel.LOW,
            details={
                "request": asdict(request),
                "auth_result": asdict(auth_result) if auth_result else None,
                "error": error
            },
            user_id=request.user_id,
            ip_address="127.0.0.1"
        )
        
        await self.security_manager.log_security_event(security_event)
        return event_id
    
    def _get_validated_components(self, request: SecurityValidationRequest) -> List[str]:
        """Get list of components that were validated."""
        components = []
        
        if request.token or request.api_key:
            components.append("authentication")
        
        if request.permissions_required:
            components.append("authorization")
        
        if request.command:
            components.append("command_validation")
        
        if request.input_data:
            components.append("input_sanitization")
        
        return components
    
    async def get_security_status(self) -> Dict[str, Any]:
        """Get unified security system status."""
        return {
            "status": "operational",
            "components": {
                "security_manager": "active",
                "auth_middleware": "active",
                "event_correlator": "active",
                "metrics": "active"
            },
            "configuration": {
                "profile": self.config.profile.value,
                "auth_methods": [method.value for method in self.config.auth.enabled_methods],
                "monitoring_enabled": self.config.monitoring.enabled,
                "audit_enabled": self.config.audit.enabled
            },
            "metrics": await self.metrics.get_summary(),
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_audit_events(self, limit: int = 100, 
                             risk_level: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent audit events."""
        events = await self.security_manager.get_recent_events(limit, risk_level)
        return [event.to_dict() for event in events]


class EventCorrelator:
    """Correlates security events across components."""
    
    def __init__(self):
        self.event_store: List[UnifiedSecurityEvent] = []
    
    async def correlate_events(self, event: UnifiedSecurityEvent) -> List[str]:
        """Correlate event with existing events."""
        # Simple correlation based on user_id and time window
        correlated = []
        
        for existing_event in self.event_store[-100:]:  # Last 100 events
            if (existing_event.user_id == event.user_id and 
                abs((event.timestamp - existing_event.timestamp).total_seconds()) < 300):
                correlated.append(existing_event.event_id)
        
        self.event_store.append(event)
        return correlated


class SecurityMetrics:
    """Tracks security metrics and statistics."""
    
    def __init__(self):
        self.validation_successes = 0
        self.validation_failures = 0
        self.auth_attempts = 0
        self.auth_failures = 0
        self.command_blocks = 0
        self.input_sanitizations = 0
        self.start_time = datetime.now()
    
    def record_validation_success(self):
        """Record successful validation."""
        self.validation_successes += 1
    
    def record_validation_failure(self):
        """Record failed validation."""
        self.validation_failures += 1
    
    def record_auth_attempt(self):
        """Record authentication attempt."""
        self.auth_attempts += 1
    
    def record_auth_failure(self):
        """Record authentication failure."""
        self.auth_failures += 1
    
    def record_command_block(self):
        """Record blocked command."""
        self.command_blocks += 1
    
    def record_input_sanitization(self):
        """Record input sanitization."""
        self.input_sanitizations += 1
    
    async def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "uptime_seconds": uptime,
            "validation_successes": self.validation_successes,
            "validation_failures": self.validation_failures,
            "validation_success_rate": (
                self.validation_successes / max(1, self.validation_successes + self.validation_failures)
            ),
            "auth_attempts": self.auth_attempts,
            "auth_failures": self.auth_failures,
            "auth_success_rate": (
                (self.auth_attempts - self.auth_failures) / max(1, self.auth_attempts)
            ),
            "command_blocks": self.command_blocks,
            "input_sanitizations": self.input_sanitizations,
            "requests_per_second": (
                (self.validation_successes + self.validation_failures) / max(1, uptime)
            )
        }