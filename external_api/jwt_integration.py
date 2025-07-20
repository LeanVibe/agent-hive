#!/usr/bin/env python3
"""
JWT Authentication Integration for API Gateway

Provides seamless JWT authentication integration between the security layer
and API Gateway, with advanced token validation, refresh handling, and
comprehensive security monitoring.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import uuid

import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from config.auth_models import Permission, AuthResult
from security.auth_service import AuthenticationService, UserRole, SessionStatus
from security.token_manager import SecureTokenManager, TokenType, TokenStatus
from external_api.auth_middleware import AuthenticationMiddleware, AuthMethod
from external_api.models import ApiRequest, ApiResponse


logger = logging.getLogger(__name__)


class JwtValidationResult(Enum):
    """JWT validation result types."""
    VALID = "valid"
    EXPIRED = "expired"
    INVALID = "invalid"
    REVOKED = "revoked"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    RATE_LIMITED = "rate_limited"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


@dataclass
class JwtValidationMetadata:
    """Extended JWT validation metadata."""
    validation_result: JwtValidationResult
    user_id: Optional[str] = None
    username: Optional[str] = None
    roles: List[str] = None
    permissions: List[Permission] = None
    token_age_hours: Optional[float] = None
    usage_count: Optional[int] = None
    rotation_recommended: bool = False
    security_flags: List[str] = None
    client_ip: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = []
        if self.permissions is None:
            self.permissions = []
        if self.security_flags is None:
            self.security_flags = []


class JwtIntegrationService:
    """
    JWT Integration Service for API Gateway Authentication
    
    Provides comprehensive JWT authentication integration with:
    - Seamless token validation and refresh
    - Rate limiting and security monitoring
    - Integration with existing auth services
    - Advanced security features and threat detection
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize JWT integration service."""
        self.config = config
        
        # Initialize core services
        self.auth_service = AuthenticationService(config)
        self.token_manager = SecureTokenManager(config)
        self.auth_middleware = AuthenticationMiddleware(config)
        
        # Rate limiting configuration
        self.rate_limit_requests = config.get("rate_limit_requests_per_hour", 1000)
        self.rate_limit_window = config.get("rate_limit_window_seconds", 3600)
        self.suspicious_threshold = config.get("suspicious_requests_per_minute", 100)
        
        # Security settings
        self.require_https = config.get("require_https", True)
        self.enable_ip_whitelist = config.get("enable_ip_whitelist", False)
        self.allowed_ips = set(config.get("allowed_ips", []))
        self.block_tor_exit_nodes = config.get("block_tor_exit_nodes", False)
        
        # Token refresh settings
        self.auto_refresh_threshold_hours = config.get("auto_refresh_threshold_hours", 1)
        self.max_refresh_attempts = config.get("max_refresh_attempts", 3)
        
        # Monitoring and tracking
        self.request_tracking: Dict[str, List[datetime]] = {}
        self.security_events: List[Dict[str, Any]] = []
        self.rate_limit_cache: Dict[str, Dict[str, Any]] = {}
        
        # Protected endpoints configuration
        self.protected_endpoints = config.get("protected_endpoints", [])
        self.public_endpoints = config.get("public_endpoints", ["/health", "/metrics"])
        
        logger.info("JWT Integration Service initialized with enhanced security features")
    
    async def authenticate_request(self, request: ApiRequest,
                                 required_permissions: Optional[List[Permission]] = None) -> Tuple[bool, JwtValidationMetadata, Optional[ApiResponse]]:
        """
        Authenticate API request with comprehensive security checks.
        
        Returns:
            Tuple of (success, metadata, error_response)
        """
        start_time = time.time()
        
        try:
            # Check if endpoint requires authentication
            if self._is_public_endpoint(request.path):
                return True, JwtValidationMetadata(
                    validation_result=JwtValidationResult.VALID,
                    security_flags=["public_endpoint"]
                ), None
            
            # Pre-authentication security checks
            security_check_result = await self._perform_security_checks(request)
            if not security_check_result[0]:
                return False, security_check_result[1], security_check_result[2]
            
            # Extract JWT token from request
            token = self._extract_jwt_token(request)
            if not token:
                return False, JwtValidationMetadata(
                    validation_result=JwtValidationResult.INVALID,
                    security_flags=["missing_token"]
                ), self._create_error_response(401, "Authentication token required", request.request_id)
            
            # Validate JWT token
            validation_result = await self._validate_jwt_token(
                token=token,
                request=request,
                required_permissions=required_permissions
            )
            
            # Check if token needs refresh
            if validation_result.rotation_recommended:
                await self._recommend_token_refresh(validation_result, request)
            
            # Log authentication event
            await self._log_authentication_event(request, validation_result, time.time() - start_time)
            
            # Return result
            success = validation_result.validation_result == JwtValidationResult.VALID
            error_response = None if success else self._create_auth_error_response(validation_result, request.request_id)
            
            return success, validation_result, error_response
            
        except Exception as e:
            logger.error(f"Authentication error for request {request.request_id}: {e}")
            return False, JwtValidationMetadata(
                validation_result=JwtValidationResult.INVALID,
                security_flags=["system_error"]
            ), self._create_error_response(500, "Authentication system error", request.request_id)
    
    async def refresh_token(self, refresh_token: str, client_ip: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Refresh JWT token using refresh token.
        
        Returns:
            Tuple of (success, new_access_token, new_refresh_token)
        """
        try:
            # Use auth service for token refresh
            success, message, session = await self.auth_service.refresh_session(
                refresh_token=refresh_token,
                client_ip=client_ip
            )
            
            if success and session:
                # Log successful refresh
                await self._log_security_event({
                    "event_type": "token_refreshed",
                    "user_id": session.user_id,
                    "client_ip": client_ip,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                return True, session.access_token, session.refresh_token
            else:
                # Log failed refresh
                await self._log_security_event({
                    "event_type": "token_refresh_failed",
                    "client_ip": client_ip,
                    "reason": message,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                return False, None, None
                
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return False, None, None
    
    async def revoke_token(self, token: str, reason: str = "user_logout") -> bool:
        """Revoke JWT token."""
        try:
            # Extract token ID
            payload = jwt.decode(token, options={"verify_signature": False})
            token_id = payload.get("token_id")
            
            if token_id:
                return await self.token_manager.revoke_token(token_id, reason)
            
            return False
            
        except Exception as e:
            logger.error(f"Token revocation error: {e}")
            return False
    
    async def get_authentication_stats(self) -> Dict[str, Any]:
        """Get comprehensive authentication statistics."""
        auth_stats = await self.auth_service.get_authentication_stats()
        token_analytics = await self.token_manager.get_token_analytics()
        
        # Calculate request statistics
        total_requests = len(self.security_events)
        successful_auth = len([e for e in self.security_events if e.get("event_type") == "authentication_success"])
        failed_auth = len([e for e in self.security_events if e.get("event_type") == "authentication_failed"])
        
        # Rate limiting statistics
        rate_limited_requests = len([e for e in self.security_events if e.get("event_type") == "rate_limited"])
        
        return {
            "jwt_integration": {
                "total_requests": total_requests,
                "successful_authentications": successful_auth,
                "failed_authentications": failed_auth,
                "rate_limited_requests": rate_limited_requests,
                "active_rate_limits": len(self.rate_limit_cache)
            },
            "auth_service": auth_stats,
            "token_analytics": token_analytics,
            "security_configuration": {
                "require_https": self.require_https,
                "ip_whitelist_enabled": self.enable_ip_whitelist,
                "rate_limit_per_hour": self.rate_limit_requests,
                "auto_refresh_threshold_hours": self.auto_refresh_threshold_hours
            }
        }
    
    # Private helper methods
    
    def _extract_jwt_token(self, request: ApiRequest) -> Optional[str]:
        """Extract JWT token from request headers."""
        # Check Authorization header (Bearer token)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix
        
        # Check X-Access-Token header
        access_token = request.headers.get("X-Access-Token")
        if access_token:
            return access_token
        
        # Check query parameter (less secure, log as warning)
        token_param = request.query_params.get("token")
        if token_param:
            logger.warning(f"Token provided in query parameter for request {request.request_id} - security risk")
            return token_param
        
        return None
    
    async def _validate_jwt_token(self, token: str, request: ApiRequest,
                                 required_permissions: Optional[List[Permission]] = None) -> JwtValidationMetadata:
        """Validate JWT token with comprehensive checks."""
        try:
            # Use token manager for validation
            auth_result = await self.token_manager.validate_token_secure(
                token=token,
                required_permissions=required_permissions,
                client_ip=request.client_ip,
                user_agent=request.headers.get("User-Agent")
            )
            
            if not auth_result.success:
                # Determine specific error type
                if "expired" in auth_result.error.lower():
                    result_type = JwtValidationResult.EXPIRED
                elif "revoked" in auth_result.error.lower():
                    result_type = JwtValidationResult.REVOKED
                elif "permission" in auth_result.error.lower():
                    result_type = JwtValidationResult.INSUFFICIENT_PERMISSIONS
                else:
                    result_type = JwtValidationResult.INVALID
                
                return JwtValidationMetadata(
                    validation_result=result_type,
                    security_flags=[auth_result.error]
                )
            
            # Token is valid - extract metadata
            metadata = auth_result.metadata or {}
            
            return JwtValidationMetadata(
                validation_result=JwtValidationResult.VALID,
                user_id=auth_result.user_id,
                username=metadata.get("username"),
                roles=metadata.get("roles", []),
                permissions=auth_result.permissions,
                token_age_hours=self._calculate_token_age(metadata),
                usage_count=metadata.get("usage_count"),
                rotation_recommended=metadata.get("rotation_recommended", False),
                client_ip=request.client_ip
            )
            
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            return JwtValidationMetadata(
                validation_result=JwtValidationResult.INVALID,
                security_flags=[f"validation_error: {str(e)}"]
            )
    
    async def _perform_security_checks(self, request: ApiRequest) -> Tuple[bool, JwtValidationMetadata, Optional[ApiResponse]]:
        """Perform comprehensive security checks."""
        security_flags = []
        
        # HTTPS requirement check
        if self.require_https:
            # In a real implementation, check if request was made over HTTPS
            # For now, assume it's handled by the gateway/proxy
            pass
        
        # IP whitelist check
        if self.enable_ip_whitelist and request.client_ip not in self.allowed_ips:
            return False, JwtValidationMetadata(
                validation_result=JwtValidationResult.INVALID,
                security_flags=["ip_not_whitelisted"]
            ), self._create_error_response(403, "Access denied from this IP address", request.request_id)
        
        # Rate limiting check
        rate_limit_result = await self._check_rate_limits(request)
        if not rate_limit_result[0]:
            return False, JwtValidationMetadata(
                validation_result=JwtValidationResult.RATE_LIMITED,
                security_flags=["rate_limited"],
                rate_limit_remaining=rate_limit_result[1]
            ), self._create_error_response(429, "Rate limit exceeded", request.request_id)
        
        # Suspicious activity detection
        if await self._detect_suspicious_activity(request):
            security_flags.append("suspicious_activity")
            
            # Log but don't block (configurable)
            await self._log_security_event({
                "event_type": "suspicious_activity_detected",
                "client_ip": request.client_ip,
                "user_agent": request.headers.get("User-Agent"),
                "request_path": request.path,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return True, JwtValidationMetadata(
            validation_result=JwtValidationResult.VALID,
            security_flags=security_flags
        ), None
    
    async def _check_rate_limits(self, request: ApiRequest) -> Tuple[bool, int]:
        """Check rate limits for client IP."""
        client_key = f"rate_limit:{request.client_ip}"
        current_time = datetime.utcnow()
        window_start = current_time - timedelta(seconds=self.rate_limit_window)
        
        # Initialize tracking if not exists
        if request.client_ip not in self.request_tracking:
            self.request_tracking[request.client_ip] = []
        
        # Clean old requests outside window
        self.request_tracking[request.client_ip] = [
            req_time for req_time in self.request_tracking[request.client_ip]
            if req_time > window_start
        ]
        
        # Check if under limit
        current_count = len(self.request_tracking[request.client_ip])
        remaining = max(0, self.rate_limit_requests - current_count)
        
        if current_count >= self.rate_limit_requests:
            # Log rate limit exceeded
            await self._log_security_event({
                "event_type": "rate_limit_exceeded",
                "client_ip": request.client_ip,
                "request_count": current_count,
                "limit": self.rate_limit_requests,
                "timestamp": current_time.isoformat()
            })
            return False, 0
        
        # Add current request
        self.request_tracking[request.client_ip].append(current_time)
        return True, remaining - 1
    
    async def _detect_suspicious_activity(self, request: ApiRequest) -> bool:
        """Detect suspicious activity patterns."""
        # Track requests per minute for burst detection
        minute_key = datetime.utcnow().replace(second=0, microsecond=0)
        minute_requests = self.request_tracking.get(request.client_ip, [])
        
        # Count requests in current minute
        current_minute_count = len([
            req_time for req_time in minute_requests
            if req_time.replace(second=0, microsecond=0) == minute_key
        ])
        
        # Check for burst activity
        if current_minute_count > self.suspicious_threshold:
            return True
        
        # Check for unusual user agent patterns
        user_agent = request.headers.get("User-Agent", "").lower()
        suspicious_patterns = ["bot", "crawler", "scanner", "curl", "wget"]
        if any(pattern in user_agent for pattern in suspicious_patterns):
            return True
        
        # Check for suspicious paths
        suspicious_paths = ["/admin", "/.env", "/config", "/backup"]
        if any(path in request.path for path in suspicious_paths):
            return True
        
        return False
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (doesn't require authentication)."""
        return any(public_path in path for public_path in self.public_endpoints)
    
    def _calculate_token_age(self, metadata: Dict[str, Any]) -> Optional[float]:
        """Calculate token age in hours."""
        try:
            created_at = metadata.get("created_at")
            if created_at:
                created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                age_delta = datetime.utcnow() - created_time.replace(tzinfo=None)
                return age_delta.total_seconds() / 3600
        except Exception:
            pass
        return None
    
    async def _recommend_token_refresh(self, validation_metadata: JwtValidationMetadata, request: ApiRequest) -> None:
        """Recommend token refresh to client."""
        await self._log_security_event({
            "event_type": "token_refresh_recommended",
            "user_id": validation_metadata.user_id,
            "token_age_hours": validation_metadata.token_age_hours,
            "client_ip": request.client_ip,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def _create_error_response(self, status_code: int, message: str, request_id: str) -> ApiResponse:
        """Create standardized error response."""
        return ApiResponse(
            status_code=status_code,
            headers={"Content-Type": "application/json"},
            body={
                "error": message,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            timestamp=datetime.utcnow(),
            processing_time=0.0,
            request_id=request_id
        )
    
    def _create_auth_error_response(self, validation_metadata: JwtValidationMetadata, request_id: str) -> ApiResponse:
        """Create authentication-specific error response."""
        error_messages = {
            JwtValidationResult.EXPIRED: "Token has expired",
            JwtValidationResult.INVALID: "Invalid authentication token",
            JwtValidationResult.REVOKED: "Token has been revoked",
            JwtValidationResult.INSUFFICIENT_PERMISSIONS: "Insufficient permissions",
            JwtValidationResult.RATE_LIMITED: "Rate limit exceeded",
            JwtValidationResult.SUSPICIOUS_ACTIVITY: "Request blocked due to suspicious activity"
        }
        
        status_codes = {
            JwtValidationResult.EXPIRED: 401,
            JwtValidationResult.INVALID: 401,
            JwtValidationResult.REVOKED: 401,
            JwtValidationResult.INSUFFICIENT_PERMISSIONS: 403,
            JwtValidationResult.RATE_LIMITED: 429,
            JwtValidationResult.SUSPICIOUS_ACTIVITY: 403
        }
        
        message = error_messages.get(validation_metadata.validation_result, "Authentication failed")
        status_code = status_codes.get(validation_metadata.validation_result, 401)
        
        response_body = {
            "error": message,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add additional information for specific error types
        if validation_metadata.validation_result == JwtValidationResult.RATE_LIMITED:
            response_body["rate_limit_remaining"] = validation_metadata.rate_limit_remaining
            response_body["retry_after"] = self.rate_limit_window
        
        if validation_metadata.rotation_recommended:
            response_body["token_refresh_recommended"] = True
        
        return ApiResponse(
            status_code=status_code,
            headers={"Content-Type": "application/json"},
            body=response_body,
            timestamp=datetime.utcnow(),
            processing_time=0.0,
            request_id=request_id
        )
    
    async def _log_authentication_event(self, request: ApiRequest, 
                                       validation_metadata: JwtValidationMetadata,
                                       processing_time: float) -> None:
        """Log authentication event for monitoring."""
        event_type = "authentication_success" if validation_metadata.validation_result == JwtValidationResult.VALID else "authentication_failed"
        
        event = {
            "event_type": event_type,
            "request_id": request.request_id,
            "client_ip": request.client_ip,
            "user_agent": request.headers.get("User-Agent"),
            "path": request.path,
            "method": request.method,
            "validation_result": validation_metadata.validation_result.value,
            "processing_time_ms": round(processing_time * 1000, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add user information if available
        if validation_metadata.user_id:
            event["user_id"] = validation_metadata.user_id
        if validation_metadata.username:
            event["username"] = validation_metadata.username
        if validation_metadata.roles:
            event["roles"] = validation_metadata.roles
        
        # Add security flags
        if validation_metadata.security_flags:
            event["security_flags"] = validation_metadata.security_flags
        
        await self._log_security_event(event)
    
    async def _log_security_event(self, event: Dict[str, Any]) -> None:
        """Log security event for monitoring and analysis."""
        event["event_id"] = str(uuid.uuid4())
        self.security_events.append(event)
        
        # Keep only last 10000 events to prevent memory issues
        if len(self.security_events) > 10000:
            self.security_events = self.security_events[-5000:]
        
        # Log to standard logger as well
        logger.info(f"Security event: {event['event_type']} - {event.get('request_id', 'N/A')}")